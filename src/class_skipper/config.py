"""Explicit local credentials and a deliberately small configuration."""

import os
from pathlib import Path
from urllib.parse import urlsplit

import yaml

DEFAULTS = {
    "output": "output",
    "workspace": "workspace",
    "obsidian_vault": "",
    "language": "zh-CN",
    "workers": 3,
    "section_chars": 1200,
    "timeout_seconds": 300,
    "retries": 1,
    "max_output_tokens": 16000,
    "max_source_chars": 500000,
    "max_figures": 3,
    "vision": False,
    "review": True,
    "allow_remote_llm": False,
}


def load_env(path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.removeprefix("export ").partition("=")
        if not separator or not key.strip().replace("_", "a").isalnum():
            raise ValueError("Invalid environment file; expected KEY=value.")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key.strip(), value)


def load(path=None):
    values = yaml.safe_load(Path(path).read_text()) if path else {}
    values = values or {}
    if not isinstance(values, dict) or set(values) - DEFAULTS.keys():
        raise ValueError("Unknown configuration setting; see configs/default.yaml.")
    config = DEFAULTS | values
    for key in (
        "workers",
        "section_chars",
        "timeout_seconds",
        "max_output_tokens",
        "max_source_chars",
        "max_figures",
    ):
        if type(config[key]) is not int or config[key] < 1:
            raise ValueError(f"{key} must be a positive integer.")
    if config["workers"] > 8 or config["retries"] not in (0, 1, 2):
        raise ValueError("Use 1-8 workers and 0-2 retries.")
    for key in ("vision", "review", "allow_remote_llm"):
        if type(config[key]) is not bool:
            raise ValueError(f"{key} must be a boolean.")
    if config["language"] not in ("zh-CN", "en"):
        raise ValueError("language must be zh-CN or en.")
    return config


def credentials(vision=False, review=False):
    if vision:
        key = os.getenv("MOONSHOT_API_KEY", "")
        model = os.getenv("CLASS_SKIPPER_VISION_MODEL") or os.getenv("CLASS_SKIPPER_KIMI_MODEL", "")
        base = os.getenv("CLASS_SKIPPER_KIMI_BASE_URL", "https://api.moonshot.cn/v1")
        hosts = {"api.moonshot.cn", "api.moonshot.ai"}
    else:
        key = os.getenv("DEEPSEEK_API_KEY", "")
        model = (
            (os.getenv("CLASS_SKIPPER_REVIEW_MODEL") if review else None)
            or os.getenv("CLASS_SKIPPER_TEXT_MODEL")
            or os.getenv("CLASS_SKIPPER_DEEPSEEK_MODEL", "")
        )
        base = os.getenv("CLASS_SKIPPER_DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        hosts = {"api.deepseek.com"}
    url = urlsplit(base)
    if (
        url.scheme != "https"
        or url.hostname not in hosts
        or url.username
        or url.password
        or url.query
        or url.fragment
        or url.port not in (None, 443)
        or url.path.rstrip("/") not in ("", "/v1")
    ):
        raise ValueError("Unsupported provider endpoint.")
    if not key or not model:
        raise ValueError("Missing API key or model name in the local environment.")
    return key, model, base.rstrip("/")
