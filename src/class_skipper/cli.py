"""Single lecture and manifest batch commands."""

import argparse
import json
import sys
from pathlib import Path

from .config import credentials, load, load_env
from .engine import generate
from .llm import ModelError
from .obsidian import export_course
from .storage import atomic, digest, managed, read_json, slug, write_json


def parser():
    result = argparse.ArgumentParser(
        description="class-skipper: read, plan, write sections, revise."
    )
    result.add_argument("--config", type=Path)
    result.add_argument("--env-file", type=Path, default=Path(".env"))
    result.add_argument("--output", type=Path)
    result.add_argument("--workspace", type=Path)
    commands = result.add_subparsers(dest="command", required=True)
    single = commands.add_parser("generate", help="Generate a lecture directly from source files")
    single.add_argument("course")
    single.add_argument("lecture")
    single.add_argument("--slides", action="append", type=Path, required=True)
    single.add_argument("--transcript", action="append", type=Path, default=[])
    single.add_argument("--title")
    batch = commands.add_parser("batch", help="Generate an ordered course library")
    batch.add_argument("course")
    batch.add_argument("--manifest", type=Path, required=True)
    export = commands.add_parser(
        "export", help="Publish existing notes to Obsidian without API calls"
    )
    export.add_argument("course")
    for command in (single, batch, export):
        command.add_argument("--vault", type=Path, help="Obsidian vault root")
        command.add_argument("--course-name", help="Course folder name; defaults to index title")
    for command in (single, batch):
        command.add_argument(
            "--resume",
            action="store_true",
            default=True,
            help="Reuse exact matching complete responses (default)",
        )
        command.add_argument(
            "--refresh", action="store_true", help="Regenerate all model responses"
        )
        visual = command.add_mutually_exclusive_group()
        visual.add_argument(
            "--vision",
            action="store_true",
            default=None,
            help="Send selected page images to configured vision provider",
        )
        visual.add_argument(
            "--no-vision",
            action="store_false",
            dest="vision",
            help="Generate text notes without remote image processing",
        )
        command.add_argument(
            "--no-review", action="store_true", help="Skip final editorial revision"
        )
    commands.add_parser("doctor", help="Check dependencies and configuration without API calls")
    return result


def index_course(config, course, title, results):
    root = managed(config["output"], slug(course))
    lines = ["# " + str(title).replace("\n", " "), ""]
    for result in results:
        lecture = result["lecture"]
        note = managed(root, slug(lecture), "notes.md")
        if note.exists():
            first = note.read_text().splitlines()[0].lstrip("# ")
            label = first.replace("[", "").replace("]", "")
            suffix = "（本次未完成，保留现有版本）" if result.get("exit_code") else ""
            lines.append(f"- [{label}]({lecture}/notes.md){suffix}")
        else:
            lines.append(f"- {lecture}：尚未生成，请续跑。")
    raw = "\n".join(lines) + "\n"
    target = root / "index.md"
    receipt = managed(config["workspace"], "published", course, "index.json")
    expected = read_json(receipt).get("sha256") if receipt.exists() else None
    if target.exists() and digest(target.read_bytes()) != expected:
        target = managed(config["workspace"], "candidates", course, "index.md")
    atomic(target, raw)
    if target.name == "index.md":
        write_json(receipt, {"sha256": digest(raw.encode())})
    return str(target)


def run_batch(config, course, manifest_path, *, runner=generate, **options):
    import yaml

    spec = yaml.safe_load(manifest_path.read_text())
    if (
        not isinstance(spec, dict)
        or not isinstance(spec.get("lectures"), list)
        or not spec["lectures"]
    ):
        raise ValueError("Manifest requires a nonempty lectures list.")
    for item in spec["lectures"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("Each lecture needs a string id.")
        for field in ("slides", "transcripts"):
            values = item.get(field, [])
            if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
                raise ValueError(f"{field} must be a list of file paths.")
    ids = [slug(item["id"]) for item in spec["lectures"]]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate lecture IDs.")
    results = []
    directory = manifest_path.resolve().parent
    for item in spec["lectures"]:
        lecture = item["id"]
        try:
            if not isinstance(item.get("slides"), list) or not item["slides"]:
                raise ValueError("Each lecture needs slides.")
            result, code = runner(
                config,
                course,
                lecture,
                [directory / p for p in item["slides"]],
                [directory / p for p in item.get("transcripts", [])],
                title=item.get("title"),
                **options,
            )
            results.append({"lecture": lecture, "exit_code": code, **result})
        except (ValueError, OSError, ModelError) as exc:
            results.append(
                {
                    "lecture": lecture,
                    "exit_code": 3,
                    "status": "failed",
                    "error": str(exc)
                    if not isinstance(exc, OSError)
                    else "Source or output file could not be accessed.",
                }
            )
    index = index_course(config, course, spec.get("title") or course, results)
    write_json(
        managed(config["workspace"], "reports", course, "batch.json"),
        {"lectures": results, "index": index},
    )
    return {"lectures": results, "index": index}, 3 if any(r["exit_code"] for r in results) else 0


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        load_env(args.env_file)
        # The supplied local config enables already-authorized course testing.
        config_path = args.config
        if config_path is None and Path("configs/local.yaml").exists():
            config_path = Path("configs/local.yaml")
        config = load(config_path)
        if args.output:
            config["output"] = str(args.output)
        if args.workspace:
            config["workspace"] = str(args.workspace)
        if args.command == "doctor":
            import importlib.util

            missing = [
                m
                for m in ("httpx", "yaml", "pypdfium2", "docx", "pptx", "PIL")
                if importlib.util.find_spec(m) is None
            ]
            credentials()
            print(
                json.dumps(
                    {
                        "missing_dependencies": missing,
                        "remote_enabled": config["allow_remote_llm"],
                        "api_called": False,
                    },
                    indent=2,
                )
            )
            return 2 if missing else 0
        if args.command == "export":
            result, code = export_course(
                config, args.course, vault=args.vault, name=args.course_name
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return code
        options = dict(
            resume=not args.refresh,
            vision=args.vision,
            review=False if args.no_review else None,
            progress=lambda message: print(message, file=sys.stderr, flush=True),
        )
        if args.command == "generate":
            result, code = generate(
                config,
                args.course,
                args.lecture,
                args.slides,
                args.transcript,
                title=args.title,
                **options,
            )
            if result.get("notes"):
                # Include other existing lecture notes when updating a single lecture.
                root = managed(config["output"], args.course)
                rows = [
                    {"lecture": p.parent.name, "exit_code": 0}
                    for p in sorted(root.glob("*/notes.md"))
                    if not p.parent.name.startswith(".")
                ]
                index_path = root / "index.md"
                course_title = (
                    index_path.read_text().splitlines()[0].lstrip("# ")
                    if index_path.exists()
                    else args.course
                )
                result["index"] = index_course(config, args.course, course_title, rows)
        else:
            result, code = run_batch(config, args.course, args.manifest, **options)
        if code == 0 and (args.vault or config.get("obsidian_vault")):
            exported, export_code = export_course(
                config, args.course, vault=args.vault, name=args.course_name
            )
            result["obsidian"] = exported
            code = export_code or code
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    except (ValueError, ModelError) as exc:
        print("error: " + str(exc), file=sys.stderr)
        return 2
    except OSError:
        print(
            "error: unable to read sources or write output; check paths and permissions.",
            file=sys.stderr,
        )
        return 2
