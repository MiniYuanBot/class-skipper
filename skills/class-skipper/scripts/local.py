"""Offline helpers for Codex-authored course notes; Python 3.11+, Windows/macOS."""

import argparse
import json
import re
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

from materials import read_materials, render_page
from storage import atomic, digest, managed, read_json, slug, write_json

PARSER_VERSION = 1
IMAGE = re.compile(r"!\[([^\]]*)\]\(([^()]+)\)")


def portable_id(parent, value):
    """Reject case collisions on macOS too, even when its volume is case-sensitive."""
    if parent.exists():
        for child in parent.iterdir():
            if child.name.casefold() == value.casefold() and child.name != value:
                raise ValueError(f"ID {value} collides with existing {child.name} on Windows.")


@contextmanager
def lock(directory):
    """Atomic directory creation works on Windows and macOS without fcntl."""
    directory.parent.mkdir(parents=True, exist_ok=True)
    try:
        directory.mkdir()
    except FileExistsError as exc:
        raise ValueError(
            f"Another writer holds {directory}; retry after it finishes. "
            "After a crash, verify no writer remains before removing this lock."
        ) from exc
    try:
        yield
    finally:
        directory.rmdir()


def prepare(args):
    course, lecture = slug(args.course), slug(args.lecture)
    if lecture.lower() == "index":
        raise ValueError("Lecture ID index is reserved.")
    root = managed(Path(args.root).expanduser())
    managed(root, "input").mkdir(parents=True, exist_ok=True)
    for parent in (root / "workspace", root / "output"):
        portable_id(parent, course)
        portable_id(parent / course, lecture)
    materials = read_materials(args.slides or [], args.transcript or [])
    if not materials["sources"]:
        raise ValueError("Provide at least one slide or transcript source.")
    options = json.loads(args.options)
    if not isinstance(options, dict):
        raise ValueError("Options must be a JSON object.")
    identity = {
        "schema_version": 1,
        "parser_version": PARSER_VERSION,
        "course": course,
        "lecture": lecture,
        "title": args.title,
        "options": options,
        "sources": materials["sources"],
    }
    run = managed(root, "workspace", course, lecture, digest(identity)[:24])
    run.mkdir(parents=True, exist_ok=True)
    for folder in (
        "requests",
        "chapters",
        "visuals/pages",
        "visuals/crops",
        "draft",
        "revision",
        "final",
        "cache",
    ):
        managed(run, folder).mkdir(parents=True, exist_ok=True)
    with lock(run / ".prepare-lock"):
        managed(run, "run.json")
        managed(run, "materials.json")
        metadata = identity | {"root": str(root), "source_digest": digest(identity)}
        if not (run / "run.json").exists():
            write_json(run / "materials.json", {"schema_version": 1} | materials)
            write_json(run / "run.json", metadata)
        elif read_json(run / "run.json") != metadata:
            raise ValueError("Existing run identity differs; preserve it and use another root.")
        status = managed(run, "status.json")
        if not status.exists():
            write_json(
                status,
                {
                    "schema_version": 1,
                    "stages": {
                        stage: "pending" for stage in ("reading", "writing", "visuals", "revision")
                    },
                    "chapters": {},
                    "publication": None,
                },
            )
    return {
        "status": "prepared",
        "run": str(run),
        "materials": str(run / "materials.json"),
        "sources": len(materials["sources"]),
        "units": len(materials["units"]),
        "warnings": materials["warnings"],
    }, 0


def get_run(path):
    run = managed(Path(path).expanduser())
    metadata = read_json(managed(run, "run.json"))
    managed(run, "materials.json")
    expected = managed(
        metadata["root"],
        "workspace",
        slug(metadata["course"]),
        slug(metadata["lecture"]),
        metadata["source_digest"][:24],
    )
    if expected != run:
        raise ValueError("Run path does not match its identity.")
    return run, metadata


def cache(args):
    run, metadata = get_run(args.run)
    request = read_json(args.request)
    if not isinstance(request, dict) or not all(
        k in request for k in ("stage", "instructions", "options")
    ):
        raise ValueError("Cache request needs stage, instructions and options fields.")
    if not request["stage"] or not request["instructions"]:
        raise ValueError("Stage and full instructions must be nonempty.")
    upstream = [digest(Path(p).read_bytes()) for p in args.upstream or []]
    key = digest(
        {
            "source_digest": metadata["source_digest"],
            "request": request,
            "materials_digest": digest((run / "materials.json").read_bytes()),
            "upstream": upstream,
        }
    )
    path = managed(run, "cache", key + ".json")
    if args.operation == "lookup":
        if not path.exists():
            return {"status": "miss", "key": key}, 0
        stored = read_json(path)
        return {
            "status": "hit",
            "key": key,
            "response": stored["response"],
            "cache": str(path),
        }, 0
    if not args.response:
        raise ValueError("Cache store needs --response containing completed response JSON.")
    response = read_json(args.response)
    if response in (None, "", [], {}):
        raise ValueError("Do not cache empty or incomplete responses.")
    with lock(run / ".cache-lock"):
        proposed = {
            "key": key,
            "request": request,
            "upstream": upstream,
            "response": response,
        }
        if path.exists() and read_json(path) != proposed:
            if not args.refresh:
                raise ValueError(
                    "Cache key already has another response; use --refresh to archive it first."
                )
            old = read_json(path)
            write_json(
                managed(run, "cache", "history", key + "-" + digest(old)[:24] + ".json"),
                old,
            )
        write_json(path, proposed)
    return {"status": "stored", "key": key, "cache": str(path)}, 0


def render(args):
    run, _ = get_run(args.run)
    materials = read_json(run / "materials.json")
    source = next((s for s in materials["sources"] if s["id"] == args.source), None)
    if source is None:
        raise ValueError("Unknown source ID.")
    if digest(Path(source["path"]).read_bytes()) != source["sha256"]:
        raise ValueError("Source changed since preparation; prepare a new run.")
    output = Path(args.output).expanduser().absolute()
    values = None
    if args.crop:
        values = [int(v) for v in args.crop.split(",")]
        if len(values) != 4:
            raise ValueError("Crop is x,y,width,height in rendered image pixels.")
    with tempfile.TemporaryDirectory(prefix="class-skipper-render-") as temporary:
        rendered = Path(temporary) / "page.png"
        render_page(source, args.page, rendered)
        raw = rendered.read_bytes()
        if values:
            from PIL import Image

            x, y, width, height = values
            with Image.open(rendered) as image:
                if (
                    min(x, y) < 0
                    or min(width, height) <= 0
                    or x + width > image.width
                    or y + height > image.height
                ):
                    raise ValueError("Crop lies outside the rendered page.")
                cropped = image.crop((x, y, x + width, y + height))
                raw = _png_bytes(cropped)
        atomic(output, raw)
    return {
        "status": "rendered",
        "image": str(output),
        "source": args.source,
        "page": args.page,
        "crop": args.crop,
    }, 0


def _png_bytes(image):
    from io import BytesIO

    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def referenced_assets(body, supplied):
    assets = {}
    by_name = {}
    for filename in supplied:
        path = Path(filename).resolve(strict=True)
        folder_name(path.name)
        if path.name.casefold() in {name.casefold() for name in by_name}:
            raise ValueError("Asset filenames must be unique.")
        by_name[path.name] = path
    for _, reference in IMAGE.findall(body):
        if not reference.startswith("assets/"):
            raise ValueError("Published images must use assets/FILENAME paths.")
        filename = reference[len("assets/") :]
        if not filename or Path(filename).name != filename or "\\" in filename:
            raise ValueError("Published asset path must contain a single filename.")
        if filename not in by_name:
            raise ValueError(f"Referenced asset was not supplied: {filename}")
        assets["assets/" + filename] = by_name[filename].read_bytes()
    return assets


def sync_files(target, files, receipt, candidates, *, remove=()):
    """Preflight every file before writing; unrecognized edits produce candidates."""
    managed(receipt.parent, receipt.name)
    previous = read_json(receipt).get("files", {}) if receipt.exists() else {}
    conflicts = []
    for relative in set(files) | set(remove):
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
        candidate = managed(candidates, digest({k: digest(v) for k, v in files.items()})[:24])
        for relative, raw in files.items():
            atomic(managed(candidate, relative), raw)
        return {
            "status": "manual_changes_preserved",
            "conflicts": sorted(conflicts),
            "candidate": str(candidate),
        }, 5
    for relative, raw in files.items():
        atomic(managed(target, relative), raw)
    for relative in remove:
        path = managed(target, relative)
        if path.exists():
            path.unlink()
        previous.pop(relative, None)
    previous.update({k: digest(v) for k, v in files.items()})
    write_json(receipt, {"files": previous})
    return {"status": "published", "target": str(target)}, 0


def publish_legacy(args):
    run, metadata = get_run(args.run)
    course, lecture = metadata["course"], metadata["lecture"]
    target = managed(metadata["root"], "output", course)
    base = managed(metadata["root"], "workspace", course, "publication")
    body = Path(args.note).read_text(encoding="utf-8-sig")
    if not body.strip():
        raise ValueError("Final note is empty.")
    if "本节生成暂未完成" in body:
        raise ValueError("Incomplete draft cannot be published; resume chapter writing first.")
    assets = referenced_assets(body, args.asset or [])
    files = {lecture + "/notes.md": body.encode("utf-8")}
    files.update({lecture + "/" + k: v for k, v in assets.items()})
    with lock(base / ".publish-lock"):
        titles_path = managed(base, "titles.json")
        titles = read_json(titles_path) if titles_path.exists() else {}
        if any(key.casefold() == lecture.casefold() and key != lecture for key in titles):
            raise ValueError("Lecture ID has a Windows case collision.")
        titles[lecture] = metadata["title"]
        index = f"# {course}\n\n" + "".join(
            f"- [{title.replace('[', '').replace(']', '').replace(chr(10), ' ')}]({key}/notes.md)\n"
            for key, title in sorted(titles.items())
        )
        files["index.md"] = index.encode("utf-8")
        receipt = managed(base, "published.json")
        previous = read_json(receipt).get("files", {}) if receipt.exists() else {}
        remove = {k for k in previous if k.startswith(lecture + "/assets/")} - set(files)
        result, code = sync_files(target, files, receipt, base / "candidates", remove=remove)
        if not code:
            write_json(titles_path, titles)
            result["notes"] = str(target / lecture / "notes.md")
            result["index"] = str(target / "index.md")
    return result, code


def text(value):
    if not isinstance(value, str):
        raise ValueError("Document text fields must be strings.")
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def label(value):
    return text(value).replace("[", "").replace("]", "").replace("\n", " ")


def chapter_headings(body):
    """Promote draft headings for a standalone chapter, preserving code and math."""
    result, fence, math = [], None, False
    for line in body.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker and not math:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
        elif fence is None and line.strip() in {"$$", "\\[", "\\]"}:
            math = not math
        elif fence is None and not math:
            line = re.sub(r"^(#{3,4})(?=\s)", lambda match: match[1][1:], line)
        result.append(line)
    return "\n".join(result)


def markdown_page(kind, metadata, title, body, section=None):
    fields = {
        "schema_version": 1,
        "type": kind,
        "title": text(title),
    }
    fields.update({key: metadata[key] for key in ("course", "lecture") if key in metadata})
    if section:
        fields["section"] = section
    header = (
        "---\n"
        + "".join(f"{k}: {json.dumps(v, ensure_ascii=False)}\n" for k, v in fields.items())
        + "---\n\n"
    )
    return (header + f"# {label(title)}\n\n" + text(body) + "\n").encode("utf-8")


def publish(args):
    if not args.document:
        return publish_legacy(args)
    run, metadata = get_run(args.run)
    document = read_json(args.document)
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError("Publication document requires schema_version: 1.")
    title = text(document["title"])
    introduction, synthesis = text(document["introduction"]), text(document["synthesis"])
    sections = document["sections"]
    uncertainties = document["uncertainties"]
    if (
        not title
        or not isinstance(sections, list)
        or not sections
        or not isinstance(uncertainties, list)
    ):
        raise ValueError("Document needs a title, nonempty sections and an uncertainties list.")
    materials = read_json(run / "materials.json")
    units = {unit["id"]: unit for unit in materials["units"]}
    sources = {source["id"]: source for source in materials["sources"]}
    chapter_bodies, ids = {}, set()
    for section in sections:
        if not isinstance(section, dict) or not isinstance(section.get("id"), str):
            raise ValueError("Each section needs a string id and chapter fields.")
        section_id = slug(section["id"])
        if section_id.casefold() in ids:
            raise ValueError("Section IDs must be unique, including Windows case folding.")
        ids.add(section_id.casefold())
        body, chapter_title = text(section["markdown"]), text(section["title"])
        references = section["source_ids"]
        if not body or not chapter_title or "本节生成暂未完成" in body:
            raise ValueError("Each chapter requires complete title and Markdown.")
        if (
            not isinstance(references, list)
            or not references
            or any(not isinstance(ref, str) or ref not in units for ref in references)
        ):
            raise ValueError("Each chapter needs valid material unit source_ids.")
        references = list(dict.fromkeys(references))
        citations = "\n\n来源：" + " ".join(f"[^{ref}]" for ref in references) + "\n\n"
        for ref in references:
            unit = units[ref]
            citations += (
                f"[^{ref}]: {label(sources[unit['source']]['name'])} — {label(unit['location'])}\n"
            )
        chapter_bodies[section_id] = (chapter_title, chapter_headings(body) + citations)
    all_body = "\n".join([introduction, synthesis, *[body for _, body in chapter_bodies.values()]])
    if "本节生成暂未完成" in all_body:
        raise ValueError("Publication document contains an incomplete draft marker.")
    assets = referenced_assets(all_body, args.asset or [])
    course, lecture = metadata["course"], metadata["lecture"]
    root = Path(metadata["root"])
    target, base = managed(root, "output"), managed(root, "workspace", "publication")
    prefix = f"{course}/{lecture}/"
    files = {prefix + name: raw for name, raw in assets.items()}
    links = "\n".join(
        f"- [{label(chapter_title)}](chapters/{section_id}.md)"
        for section_id, (chapter_title, _) in chapter_bodies.items()
    )
    lecture_body = (
        f"[课程目录](../index.md) · [全部课程](../../index.md)\n\n{introduction}"
        f"\n\n## 章节导航\n\n{links}\n\n## 本讲小结\n\n{synthesis}"
    )
    if uncertainties:
        lecture_body += "\n\n## 不确定事项\n\n" + "\n".join(
            "- " + text(item) for item in uncertainties
        )
    locations = list(dict.fromkeys(ref for section in sections for ref in section["source_ids"]))
    lecture_body += "\n\n## 来源\n\n" + "\n".join(
        f"- {label(sources[units[ref]['source']]['name'])} — {label(units[ref]['location'])}"
        for ref in locations
    )
    files[prefix + "index.md"] = markdown_page("lecture-index", metadata, title, lecture_body)
    for section_id, (chapter_title, body) in chapter_bodies.items():
        body = IMAGE.sub(lambda match: f"![{match[1]}](../{match[2]})", body)
        navigation = (
            "[本讲目录](../index.md) · [课程目录](../../index.md) · [全部课程](../../../index.md)"
        )
        files[prefix + f"chapters/{section_id}.md"] = markdown_page(
            "course-note", metadata, chapter_title, navigation + "\n\n" + body, section_id
        )
    with lock(base / ".publish-lock"):
        registry_path = managed(base, "courses.json")
        registry = read_json(registry_path) if registry_path.exists() else {}
        for existing in registry:
            if existing.casefold() == course.casefold() and existing != course:
                raise ValueError("Course ID has a Windows case collision.")
        entry = registry.setdefault(
            course, {"name": metadata["options"].get("course_name", course), "lectures": {}}
        )
        for existing in entry["lectures"]:
            if existing.casefold() == lecture.casefold() and existing != lecture:
                raise ValueError("Lecture ID has a Windows case collision.")
        entry["lectures"][lecture] = {"title": title, "layout": "sections"}
        course_body = "[全部课程](../index.md)\n\n" + "\n".join(
            f"- [{label(item['title'])}]({key}/index.md)" for key, item in entry["lectures"].items()
        )
        files[course + "/index.md"] = markdown_page(
            "course-index", {"course": course}, entry["name"], course_body
        )
        root_body = "\n".join(
            f"- [{label(item['name'])}]({key}/index.md)" for key, item in registry.items()
        )
        files["index.md"] = markdown_page("library-index", {}, "课程目录", root_body)
        receipt = managed(base, "published.json")
        previous = read_json(receipt).get("files", {}) if receipt.exists() else {}
        remove = {name for name in previous if name.startswith(prefix)} - set(files)
        result, code = sync_files(target, files, receipt, base / "candidates", remove=remove)
        if not code:
            write_json(registry_path, registry)
            result.update(
                {
                    "index": str(target / "index.md"),
                    "course_index": str(target / course / "index.md"),
                    "lecture_index": str(target / prefix / "index.md"),
                    "chapters": len(sections),
                }
            )
        return result, code


def folder_name(value):
    if (
        not value
        or value.startswith(".")
        or value.endswith((".", " "))
        or any(c in value for c in '/\\:*?"<>|\n\r\t')
        or len(value.encode("utf-8")) > 200
    ):
        raise ValueError("Course name must be one portable visible folder name.")
    if value.split(".")[0].upper() in {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *{f"COM{i}" for i in range(1, 10)},
        *{f"LPT{i}" for i in range(1, 10)},
    }:
        raise ValueError("Course name is a reserved Windows filename.")
    return value


def export(args):
    root, course = managed(Path(args.root).expanduser()), slug(args.course)
    source = managed(root, "output", course)
    target = managed(Path(args.vault).expanduser(), folder_name(args.course_name))
    if target == root or target in root.parents or root in target.parents:
        raise ValueError("Vault course folder must be separate from the working root.")
    registry_path = managed(root, "workspace", "publication", "courses.json")
    registry = read_json(registry_path) if registry_path.exists() else {}
    files = structured_export(root, course, source, registry[course]) if course in registry else {}
    index = managed(source, "index.md").read_text(encoding="utf-8-sig")
    notes = sorted(source.glob("*/notes.md")) if not files else []
    if not notes and not files:
        raise ValueError("No published notes to export.")
    for note in notes:
        lecture = slug(note.parent.name)
        managed(source, lecture, "notes.md")
        body = note.read_text(encoding="utf-8-sig")
        if not body.strip() or "本节生成暂未完成" in body:
            raise ValueError(f"{lecture} is incomplete; resume writing before export.")
        supplied = []
        for _, reference in IMAGE.findall(body):
            if not reference.startswith("assets/"):
                raise ValueError("Export expects relative published image references.")
            supplied.append(managed(source, lecture, reference))
        assets = referenced_assets(body, list(dict.fromkeys(supplied)))
        for relative, raw in assets.items():
            filename = relative[len("assets/") :]
            files[f"assets/{lecture}/{filename}"] = raw
            body = body.replace(f"]({relative})", f"](assets/{lecture}/{filename})")
        files[lecture + ".md"] = body.encode("utf-8")
        index = index.replace(f"]({lecture}/notes.md)", f"]({lecture}.md)")
    if notes:
        files["index.md"] = index.encode("utf-8")
    base = managed(root, "workspace", course, "exports", digest(str(target))[:24])
    with lock(base / ".export-lock"):
        receipt = managed(base, "published.json")
        previous = read_json(receipt).get("files", {}) if receipt.exists() else {}
        result, code = sync_files(
            target,
            files,
            receipt,
            base / "candidates",
            remove=set(previous) - set(files),
        )
    if not code:
        result["status"] = "exported"
        result["index"] = str(target / "index.md")
        if course in registry:
            result["course_index"] = str(target / course / "index.md")
    return result, code


def structured_export(root, course, source, entry):
    receipt = read_json(managed(root, "workspace", "publication", "published.json"))
    files = {}
    for relative in receipt["files"]:
        if not relative.startswith(course + "/") or not relative.endswith(".md"):
            continue
        local = relative[len(course) + 1 :]
        note = managed(source, local)
        body = note.read_text(encoding="utf-8-sig")
        if not body.strip() or "本节生成暂未完成" in body:
            raise ValueError(f"{relative} is incomplete.")
        files[relative] = body.encode("utf-8")
        for _, reference in IMAGE.findall(body):
            unresolved = note.parent / reference
            if not unresolved.resolve().is_relative_to(source.resolve()):
                raise ValueError("Exported image must stay inside its course folder.")
            asset = managed(source, unresolved.relative_to(source))
            asset_relative = asset.resolve().relative_to(source.resolve()).as_posix()
            files[course + "/" + asset_relative] = asset.read_bytes()
    files["index.md"] = markdown_page(
        "library-index", {}, "课程目录", f"- [{label(entry['name'])}]({course}/index.md)"
    )
    return files


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    p = commands.add_parser("prepare")
    for name in ("root", "course", "lecture", "title"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--slides", action="append")
    p.add_argument("--transcript", action="append")
    p.add_argument("--options", default="{}", help="JSON object of parser/workflow options")
    p.set_defaults(handler=prepare)
    p = commands.add_parser("cache")
    p.add_argument("operation", choices=("lookup", "store"))
    p.add_argument("--run", required=True)
    p.add_argument("--request", required=True)
    p.add_argument("--response")
    p.add_argument(
        "--refresh",
        action="store_true",
        help="Archive prior response before replacement",
    )
    p.add_argument("--upstream", action="append")
    p.set_defaults(handler=cache)
    p = commands.add_parser("render")
    p.add_argument("--run", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--page", type=int, required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--crop", help="x,y,width,height in pixels at rendering scale 1.5")
    p.set_defaults(handler=render)
    p = commands.add_parser("publish")
    p.add_argument("--run", required=True)
    document = p.add_mutually_exclusive_group(required=True)
    document.add_argument("--note", help="Legacy single Markdown note")
    document.add_argument("--document", help="Structured final document JSON")
    p.add_argument("--asset", action="append")
    p.set_defaults(handler=publish)
    p = commands.add_parser("export")
    for name in ("root", "course", "vault", "course-name"):
        p.add_argument("--" + name, required=True)
    p.set_defaults(handler=export)
    return cli


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        result, code = args.handler(args)
    except (ValueError, OSError, ImportError, KeyError) as exc:
        result, code = {"status": "error", "message": str(exc)}, 2
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
