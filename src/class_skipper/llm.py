"""One cached JSON request per operation; bounded transport/JSON retries."""

import base64
import json
import threading
import time
from pathlib import Path

from .config import credentials
from .storage import digest, read_json, write_json


class ModelError(RuntimeError):
    pass


class Client:
    def __init__(self, config, cache, refresh=False, transport=None):
        self.config, self.cache, self.refresh = config, Path(cache), refresh
        self.transport = transport
        self.calls = []
        self.lock = threading.Lock()

    def ask(self, stage, system, data, *, vision=False, image=None, validate=None):
        if not self.config["allow_remote_llm"]:
            raise ModelError("Remote model permission is disabled; set allow_remote_llm: true.")
        key, model, base = credentials(vision, stage == "review")
        effort = ("high" if stage.startswith("vision:verify:") else "low") if vision else None
        user = json.dumps(data, ensure_ascii=False)
        identity = digest(
            {
                "system": system,
                "data": data,
                "model": model,
                "base": base,
                "image": digest(image) if image else None,
                "tokens": self.config["max_output_tokens"],
                "reasoning_effort": effort,
            }
        )
        path = self.cache / f"{identity}.json"
        if path.exists() and not self.refresh:
            cached = read_json(path)
            if cached.get("identity") == identity and isinstance(cached.get("data"), dict):
                try:
                    if validate:
                        validate(cached["data"])
                except (ValueError, KeyError, TypeError):
                    pass
                else:
                    with self.lock:
                        self.calls.append(
                            {
                                "stage": stage,
                                "cache_hit": True,
                                "model": model,
                                "usage": None,
                                "seconds": 0,
                            }
                        )
                    return cached["data"]
        import httpx

        system += "\nReturn one valid JSON object, without Markdown fences around the JSON."
        messages = [{"role": "system", "content": system}]
        content = user
        if image:
            content = [
                {"type": "text", "text": user},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "data:image/png;base64," + base64.b64encode(image).decode()
                    },
                },
            ]
        messages.append({"role": "user", "content": content})
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": self.config["max_output_tokens"],
            "response_format": {"type": "json_object"},
            "stream": False,
        }
        if vision:
            payload["reasoning_effort"] = effort
        if not vision:
            payload["thinking"] = {"type": "disabled"}
        if len(json.dumps(payload).encode()) > 12 * 1024 * 1024:
            raise ModelError("Request is too large; split this lecture into smaller input groups.")
        for attempt in range(self.config["retries"] + 1):
            raw = None
            started = time.monotonic()
            record = {"stage": stage, "model": model, "cache_hit": False, "usage": None}
            try:
                with httpx.Client(
                    timeout=httpx.Timeout(
                        self.config["timeout_seconds"], connect=15, write=60, pool=15
                    ),
                    trust_env=False,
                    follow_redirects=False,
                    transport=self.transport,
                ) as client:
                    response = client.post(
                        base + "/chat/completions",
                        headers={"Authorization": "Bearer " + key},
                        json=payload,
                    )
                if response.status_code != 200:
                    retryable = response.status_code == 429 or response.status_code >= 500
                    record["error"] = f"HTTP {response.status_code}"
                    if not retryable or attempt == self.config["retries"]:
                        raise ModelError(record["error"])
                    continue
                raw = response.json()
                record["usage"] = raw.get("usage")
                choice = raw["choices"][0]
                if choice.get("finish_reason") == "length":
                    raise ValueError("Response reached the output limit; shorten the answer.")
                answer = json.loads(choice["message"]["content"])
                if not isinstance(answer, dict):
                    raise ValueError("Expected a JSON object.")
                if validate:
                    validate(answer)
                write_json(path, {"identity": identity, "data": answer})
                return answer
            except (httpx.RequestError, ValueError, KeyError, TypeError, IndexError) as exc:
                record["error"] = type(exc).__name__
                if isinstance(exc, ValueError):
                    record["detail"] = str(exc)[:200]
                    if raw is not None:
                        write_json(
                            self.cache / "failed" / f"{identity}-{attempt}.json",
                            {"response": raw, "error": str(exc)[:200]},
                        )
                if attempt == self.config["retries"]:
                    raise ModelError(
                        f"{stage}: {type(exc).__name__}; retry with --resume."
                    ) from None
                # One structural retry with the actual answer and precise error.
                if isinstance(exc, ValueError):
                    if isinstance(raw, dict):
                        previous = raw.get("choices", [{}])[0].get("message", {})
                        if isinstance(previous.get("content"), str):
                            payload["messages"].append(dict(previous, role="assistant"))
                    payload["messages"].append(
                        {
                            "role": "user",
                            "content": "Fix this response structure: "
                            + str(exc)[:200]
                            + " Return all required JSON fields, preserving the requested scope. "
                            "Escape backslashes in strings. Do not regenerate the whole lecture.",
                        }
                    )
                time.sleep(1)
            finally:
                record["seconds"] = round(time.monotonic() - started, 2)
                with self.lock:
                    self.calls.append(record)
