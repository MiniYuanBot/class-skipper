"""Publish final Markdown and referenced images to a course folder in a vault."""

import re
from pathlib import Path

from .storage import atomic, digest, managed, read_json, slug, write_json


def course_folder(value):
    value = str(value).strip()
    if (
        not value
        or value in {".", ".."}
        or value.startswith(".")
        or any(c in value for c in '/\\:*?"<>|\n\r\t')
        or value.endswith(".")
        or len(value.encode()) > 200
    ):
        raise ValueError(
            "Course name must be a single visible folder name without path separators."
        )
    return value


def export_course(config, course, *, vault=None, name=None):
    """No model calls; keep receipts/candidates outside the vault and preserve user edits."""
    import fcntl

    source = managed(config["output"], slug(course))
    index = source / "index.md"
    if not index.is_file():
        raise ValueError("Generate the course index before exporting.")
    vault = vault or config.get("obsidian_vault")
    if not vault:
        raise ValueError("Set obsidian_vault or pass --vault.")
    vault = managed(Path(vault).expanduser())
    name = course_folder(name or index.read_text().splitlines()[0].lstrip("# "))
    target = managed(vault, name)
    for local in (managed(config["output"]), managed(config["workspace"])):
        if local == target or local in target.parents or target in local.parents:
            raise ValueError("Obsidian course folder must be separate from output and workspace.")
    identity = digest(str(target))[:24]
    base = managed(config["workspace"], "obsidian", identity)
    base.mkdir(parents=True, exist_ok=True)
    with (base / "export.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        files = {}
        lectures = sorted(source.glob("*/notes.md"))
        if not lectures:
            raise ValueError("No lecture notes to export.")
        for note in lectures:
            lecture = slug(note.parent.name)
            if lecture.lower() == "index":
                raise ValueError("Lecture ID index is reserved for the vault course index.")
            managed(source, lecture, "notes.md")
            body = note.read_text()
            if "本节生成暂未完成" in body:
                raise ValueError(f"{lecture} is incomplete; resume generation before exporting.")

            def image(match):
                filename = match[2]
                if Path(filename).name != filename:
                    raise ValueError("Invalid generated image path.")
                asset = managed(source, lecture, "assets", filename)
                relative = f"assets/{lecture}/{filename}"
                files[relative] = asset.read_bytes()
                return f"![{match[1]}]({relative})"

            body = re.sub(r"!\[([^\]]*)\]\(assets/([^()]+)\)", image, body)
            files[lecture + ".md"] = body.encode()
        index_text = index.read_text()
        for note in lectures:
            lecture = note.parent.name
            index_text = index_text.replace(f"]({lecture}/notes.md)", f"]({lecture}.md)")
        files["index.md"] = index_text.encode()
        receipt = base / "published.json"
        previous = read_json(receipt).get("files", {}) if receipt.exists() else {}
        conflicts = []
        for relative in previous.keys() | files.keys():
            path = managed(target, relative)
            if path.exists() and not path.is_file():
                conflicts.append(relative)
                continue
            current = digest(path.read_bytes()) if path.exists() else None
            proposed = digest(files[relative]) if relative in files else None
            if relative in previous:
                if current != previous[relative] and current != proposed:
                    conflicts.append(relative)
            elif current is not None and current != proposed:
                conflicts.append(relative)
        if conflicts:
            candidate = base / "candidates" / digest({k: digest(v) for k, v in files.items()})[:16]
            for relative, raw in files.items():
                atomic(managed(candidate, relative), raw)
            return {
                "status": "manual_changes_preserved",
                "conflicts": conflicts,
                "candidate": str(candidate),
                "vault_course": str(target),
            }, 5
        for relative, raw in files.items():
            path = managed(target, relative)
            if not path.exists() or path.read_bytes() != raw:
                atomic(path, raw)
        for relative in previous.keys() - files.keys():
            path = managed(target, relative)
            if path.exists():
                path.unlink()
        write_json(
            receipt,
            {
                "course": course,
                "target": str(target),
                "files": {k: digest(v) for k, v in files.items()},
            },
        )
        return {
            "status": "exported",
            "vault_course": str(target),
            "index": str(target / "index.md"),
            "lectures": len(lectures),
            "images": sum(k.startswith("assets/") for k in files),
        }, 0
