"""Offline helpers for Codex-authored course notes; Python 3.11+, Windows/macOS."""

import argparse
import json
import re
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

from materials import page_count, page_images, read_materials, render_page
from storage import RESERVED, atomic, digest, managed, read_json, slug, write_json

PARSER_VERSION = 1
COURSE_LAYOUT = "course-root-v1"
IMAGE = re.compile(r"!\[([^\]]*)\]\(([^()]+)\)")
REMOTE = re.compile(r"^https?://", re.IGNORECASE)
FOOTNOTE = re.compile(r"\[\^([^\]\s]+)\](?!:)")
DEFINITION = re.compile(r"^\[\^([^\]\s]+)\]:", re.MULTILINE)
ENGLISH_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+){0,9}")


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


def lecture_id(value):
    match = re.fullmatch(r"[Ll]?(\d+)", value)
    if not match:
        raise ValueError("Lecture must be a number or LXX, for example L02.")
    return slug(f"L{int(match[1]):02d}")


def prepare(args):
    course, lecture = slug(args.course), lecture_id(args.lecture)
    root = managed(Path(args.root).expanduser())
    if (root / ".obsidian").exists():
        raise ValueError("--root must be a course folder below the Obsidian vault root.")
    registry_path = managed(root, "workspace", "publication", "courses.json")
    if registry_path.exists() and any(
        entry.get("layout") != COURSE_LAYOUT for entry in read_json(registry_path).values()
    ):
        raise ValueError("Existing library layout preserved; choose a separate course root.")
    if managed(root, "workspace", course, "publication", "published.json").exists():
        raise ValueError("Existing legacy output preserved; choose a separate course root.")
    course_record = managed(root, "workspace", "course.json")
    if course_record.exists() and read_json(course_record)["course"] != course:
        raise ValueError("This course root is already assigned to another course.")
    for name in ("input", "workspace", "output"):
        managed(root, name).mkdir(parents=True, exist_ok=True)
    for parent in (root / "workspace", root / "output"):
        portable_id(parent, lecture)
    materials = read_materials(args.slides or [], args.transcript or [])
    if not materials["sources"]:
        raise ValueError("Provide at least one slide or transcript source.")
    raw = args.options
    if raw.startswith("@"):
        raw = Path(raw[1:]).expanduser().read_text(encoding="utf-8-sig")
    options = json.loads(raw)
    if not isinstance(options, dict):
        raise ValueError("Options must be a JSON object.")
    if args.course_name:
        options["course_name"] = args.course_name
    identity = {
        "schema_version": 1,
        "parser_version": PARSER_VERSION,
        "layout": COURSE_LAYOUT,
        "course": course,
        "lecture": lecture,
        "title": args.title,
        "options": options,
        "sources": materials["sources"],
    }
    with lock(root / "workspace" / ".course-lock"):
        if course_record.exists() and read_json(course_record)["course"] != course:
            raise ValueError("This course root is already assigned to another course.")
        write_json(course_record, {"layout": COURSE_LAYOUT, "course": course})
    run = managed(root, "workspace", lecture, digest(identity)[:24])
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
    layout = metadata.get("layout")
    if layout not in (None, COURSE_LAYOUT):
        raise ValueError("Unknown run directory layout.")
    parts = ["workspace"]
    if layout is None:
        parts.append(slug(metadata["course"]))
    parts.extend([slug(metadata["lecture"]), metadata["source_digest"][:24]])
    expected = managed(metadata["root"], *parts)
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


def pdf_source(run, source_id):
    materials = read_json(run / "materials.json")
    source = next((s for s in materials["sources"] if s["id"] == source_id), None)
    if source is None:
        raise ValueError("Unknown source ID.")
    if digest(Path(source["path"]).read_bytes()) != source["sha256"]:
        raise ValueError("Source changed since preparation; prepare a new run.")
    return source


def crop_box(value, width, height):
    """Pixels (x,y,w,h) at the render scale, or page fractions when any value has a dot."""
    parts = value.split(",")
    if len(parts) != 4:
        raise ValueError("Crop is x,y,width,height in pixels or page fractions.")
    if any("." in part for part in parts):
        fx, fy, fw, fh = (float(part) for part in parts)
        if min(fx, fy) < 0 or min(fw, fh) <= 0 or fx + fw > 1.0001 or fy + fh > 1.0001:
            raise ValueError("Fractional crop must lie within 0..1 of the page.")
        x, y = round(fx * width), round(fy * height)
        return x, y, min(round(fw * width), width - x), min(round(fh * height), height - y)
    x, y, w, h = (int(part) for part in parts)
    if min(x, y) < 0 or min(w, h) <= 0 or x + w > width or y + h > height:
        raise ValueError("Crop lies outside the rendered page.")
    return x, y, w, h


def render(args):
    run, _ = get_run(args.run)
    source = pdf_source(run, args.source)
    output = Path(args.output).expanduser().absolute()
    with tempfile.TemporaryDirectory(prefix="class-skipper-render-") as temporary:
        rendered = Path(temporary) / "page.png"
        render_page(source, args.page, rendered, args.scale)
        raw = rendered.read_bytes()
        if args.crop:
            from PIL import Image

            with Image.open(rendered) as image:
                x, y, width, height = crop_box(args.crop, image.width, image.height)
                raw = _png_bytes(image.crop((x, y, x + width, y + height)))
        atomic(output, raw)
    return {
        "status": "rendered",
        "image": str(output),
        "source": args.source,
        "page": args.page,
        "crop": args.crop,
        "scale": args.scale,
    }, 0


def page_numbers(value, count):
    if not value:
        return list(range(1, count + 1))
    numbers = []
    for part in value.split(","):
        first, _, last = part.strip().partition("-")
        start, stop = int(first), int(last or first)
        if not 1 <= start <= stop <= count:
            raise ValueError(f"Pages must lie within 1-{count}.")
        numbers.extend(range(start, stop + 1))
    return list(dict.fromkeys(numbers))


def sheet(args):
    """Labeled thumbnail grids so a host can screen many slides per image view."""
    from PIL import Image, ImageDraw, ImageFont

    run, _ = get_run(args.run)
    source = pdf_source(run, args.source)
    numbers = page_numbers(args.pages, page_count(source))
    if args.per_sheet < 1 or args.columns < 1 or args.width < 64:
        raise ValueError("Use at least one page per sheet, one column and width 64.")
    output = Path(args.output_dir).expanduser().absolute()
    try:
        font = ImageFont.load_default(size=max(14, args.width // 16))
    except TypeError:
        font = ImageFont.load_default()
    sheets, gap = [], 8
    for offset in range(0, len(numbers), args.per_sheet):
        chunk = numbers[offset : offset + args.per_sheet]
        thumbs = []
        for number, image in page_images(source, chunk, scale=1.0):
            ratio = args.width / image.width
            thumbs.append((number, image.resize((args.width, max(1, round(image.height * ratio))))))
        cell = max(image.height for _, image in thumbs)
        columns = min(args.columns, len(thumbs))
        rows = -(-len(thumbs) // columns)
        grid = Image.new(
            "RGB",
            (columns * (args.width + gap) + gap, rows * (cell + gap) + gap),
            (200, 200, 200),
        )
        draw = ImageDraw.Draw(grid)
        for position, (number, image) in enumerate(thumbs):
            x = gap + (position % columns) * (args.width + gap)
            y = gap + (position // columns) * (cell + gap)
            grid.paste(image, (x, y))
            text = f"p.{number}"
            box = draw.textbbox((x, y), text, font=font)
            draw.rectangle((box[0], box[1], box[2] + 8, box[3] + 6), fill=(180, 0, 0))
            draw.text((x + 4, y + 2), text, fill=(255, 255, 255), font=font)
        path = output / f"{args.source}-p{chunk[0]:03d}-{chunk[-1]:03d}.png"
        atomic(path, _png_bytes(grid))
        sheets.append({"path": str(path), "pages": chunk})
    return {"status": "rendered", "source": args.source, "sheets": sheets}, 0


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
        if REMOTE.match(reference):
            continue
        if not reference.startswith("assets/"):
            raise ValueError("Published images must use assets/FILENAME or https:// paths.")
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
    if metadata.get("layout") == COURSE_LAYOUT:
        raise ValueError("New course-root runs require --document, not legacy --note.")
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


def chapter_filename(title, slug_value, section_id, used):
    """English ASCII filename: title `01 进程模型` + slug `process-model` -> 01-process-model.md."""
    if slug_value is not None and not (
        isinstance(slug_value, str) and ENGLISH_SLUG.fullmatch(slug_value)
    ):
        raise ValueError("Section slug must be lowercase English words joined by hyphens.")
    number = re.match(r"[0-9]+", label(title))
    name = slug_value or section_id
    if number and not name.startswith(number[0] + "-"):
        name = f"{number[0]}-{name}"
    if name.casefold() in used:
        name = f"{name}-{section_id}"
    used.add(name.casefold())
    return name + ".md"


def source_lines(references, units, sources):
    """One line per file with merged ranges, e.g. L03.pdf：PDF p.23–51, 127."""
    spans = {}
    for ref in references:
        unit = units[ref]
        match = re.fullmatch(r"(.*?)(\d+)(?:-(\d+))?", unit["location"])
        prefix, start, end = (
            (match[1], int(match[2]), int(match[3] or match[2]))
            if match
            else (unit["location"], None, None)
        )
        spans.setdefault((unit["source"], prefix), []).append((start, end))
    lines = {}
    for (source_id, prefix), items in spans.items():
        merged = []
        for start, end in sorted(item for item in items if item[0] is not None):
            if merged and start <= merged[-1][1] + 1:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        text_spans = ", ".join(f"{a}–{b}" if a != b else str(a) for a, b in merged)
        lines.setdefault(source_id, []).append(f"{prefix}{text_spans}".strip())
    return [
        f"{label(sources[source_id]['name'])}：{'；'.join(parts)}"
        for source_id, parts in lines.items()
    ]


def footnotes(body, units, sources):
    """Define only markers the prose uses; publication stays free of unused citations."""
    defined = set(DEFINITION.findall(body))
    definitions = []
    for ref in dict.fromkeys(FOOTNOTE.findall(body)):
        if ref in defined:
            continue
        if ref not in units:
            raise ValueError(f"Footnote marker [^{ref}] is not a material unit ID.")
        unit = units[ref]
        definitions.append(
            f"[^{ref}]: {label(sources[unit['source']]['name'])}-{label(unit['location'])}"
        )
    return "\n".join(definitions)


def sources_callout(lines):
    return "> [!info]- 来源\n" + "\n".join(f"> - {line}" for line in lines)


def markdown_page(kind, metadata, title, body, section=None):
    fields = {
        "schema_version": 1,
        "type": kind,
        "title": text(title),
        "aliases": [label(title)],
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


PACKAGES = {"pypdfium2": "pypdfium2", "docx": "python-docx", "pptx": "python-pptx", "PIL": "Pillow"}
BOLD_LABEL = re.compile(r"\*\*[^*\n]+[：:]\*\*(?=[^\s*])")
SECTION_TITLE = re.compile(r"\d{2} \S.*")
LECTURE_TITLE = re.compile(r"L\d{2,} \S.*")


def doctor(args):
    import importlib.util

    missing = [pip for module, pip in PACKAGES.items() if not importlib.util.find_spec(module)]
    supported = sys.version_info >= (3, 11)
    return {
        "status": "ready" if supported and not missing else "setup_needed",
        "python": sys.executable,
        "version": sys.version.split()[0],
        "platform": sys.platform,
        "supported": supported,
        "missing": missing,
        "install": f'"{sys.executable}" -m pip install ' + " ".join(missing) if missing else None,
    }, 0


def markdown_issues(body, units):
    """Mechanical Markdown problems; prose quality stays with the single editor."""
    issues, fence, math = [], None, 0
    for number, line in enumerate(body.splitlines(), 1):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is not None:
            continue
        if line.strip() == "$$":
            math += 1
        elif re.match(r"^#{1,2}\s", line):
            issues.append((number, "Chapter bodies use ### and #### headings only."))
        if BOLD_LABEL.search(line):
            issues.append((number, "Write **标签**：正文 or **标签：** 正文."))
        for ref in FOOTNOTE.findall(line):
            if ref not in units:
                issues.append((number, f"Unknown footnote unit [^{ref}]."))
    if fence is not None:
        issues.append((0, "Unclosed fenced code block."))
    if math % 2:
        issues.append((0, "Unbalanced $$ display-math delimiters."))
    if "[!question]" not in body:
        issues.append((0, "Missing [!question] self-test callout."))
    return issues


def check(args):
    run, _ = get_run(args.run)
    document = read_json(args.document)
    units = {unit["id"] for unit in read_json(run / "materials.json")["units"]}
    issues = []
    if not LECTURE_TITLE.fullmatch(text(document.get("title", ""))):
        issues.append({"section": None, "line": 0, "message": "Lecture title must be LXX Topic."})
    for section in document.get("sections", []):
        found = []
        if not SECTION_TITLE.fullmatch(text(section.get("title", ""))):
            found.append((0, "Section title must be NN Topic."))
        if not text(section.get("summary", "")):
            found.append((0, "Add a one-line summary for the lecture index."))
        if not ENGLISH_SLUG.fullmatch(str(section.get("slug") or "")):
            found.append((0, "Add an English kebab-case slug for the file name."))
        found += markdown_issues(text(section.get("markdown", "")), units)
        issues += [
            {"section": section.get("id"), "line": line, "message": message}
            for line, message in found
        ]
    return {"status": "issues" if issues else "ok", "issues": issues}, 0


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
    course_layout = metadata.get("layout") == COURSE_LAYOUT
    chapters, ids, filenames = [], set(), set()
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
        summary = section.get("summary", "")
        if not isinstance(summary, str):
            raise ValueError("Section summary must be a string.")
        filename = (
            chapter_filename(chapter_title, section.get("slug"), section_id, filenames)
            if course_layout
            else section_id + ".md"
        )
        definitions = footnotes(body, units, sources)
        body = (
            chapter_headings(body)
            + "\n\n"
            + sources_callout(source_lines(references, units, sources))
        )
        if definitions:
            body += "\n\n" + definitions
        chapters.append((section_id, chapter_title, filename, body, label(summary)))
    all_body = "\n".join([introduction, synthesis, *[chapter[3] for chapter in chapters]])
    if "本节生成暂未完成" in all_body:
        raise ValueError("Publication document contains an incomplete draft marker.")
    assets = referenced_assets(all_body, args.asset or [])
    course, lecture = metadata["course"], metadata["lecture"]
    root = Path(metadata["root"])
    target, base = managed(root, "output"), managed(root, "workspace", "publication")
    prefix = f"{lecture}/" if course_layout else f"{course}/{lecture}/"
    files = {prefix + name: raw for name, raw in assets.items()}
    links = "\n".join(
        f"- [{label(chapter_title)}](chapters/{filename})" + (f"：{summary}" if summary else "")
        for _, chapter_title, filename, _, summary in chapters
    )
    parent_links = "[课程目录](../index.md)"
    if not course_layout:
        parent_links += " · [全部课程](../../index.md)"
    lecture_body = (
        f"{parent_links}\n\n{introduction}\n\n## 章节导航\n\n{links}\n\n## 本讲小结\n\n{synthesis}"
    )
    if uncertainties:
        lecture_body += "\n\n## 不确定事项\n\n" + "\n".join(
            "- " + text(item) for item in uncertainties
        )
    locations = list(dict.fromkeys(ref for section in sections for ref in section["source_ids"]))
    lecture_body += "\n\n" + sources_callout(source_lines(locations, units, sources))
    files[prefix + "index.md"] = markdown_page("lecture-index", metadata, title, lecture_body)
    for position, (section_id, chapter_title, filename, body, _) in enumerate(chapters):
        body = IMAGE.sub(
            lambda match: match[0] if REMOTE.match(match[2]) else f"![{match[1]}](../{match[2]})",
            body,
        )
        navigation = "[本讲目录](../index.md) · [课程目录](../../index.md)"
        if not course_layout:
            navigation += " · [全部课程](../../../index.md)"
        neighbors = []
        if position > 0:
            previous = chapters[position - 1]
            neighbors.append(f"[上一节：{label(previous[1])}]({previous[2]})")
        if position + 1 < len(chapters):
            following = chapters[position + 1]
            neighbors.append(f"[下一节：{label(following[1])}]({following[2]})")
        if neighbors:
            navigation += " · " + " · ".join(neighbors)
        files[prefix + f"chapters/{filename}"] = markdown_page(
            "course-note",
            metadata,
            chapter_title,
            navigation + "\n\n" + body + "\n\n" + navigation,
            section_id,
        )
    with lock(base / ".publish-lock"):
        registry_path = managed(base, "courses.json")
        registry = read_json(registry_path) if registry_path.exists() else {}
        for existing in registry:
            if existing.casefold() == course.casefold() and existing != course:
                raise ValueError("Course ID has a Windows case collision.")
        if course_layout and (set(registry) - {course}):
            raise ValueError("A course-root output cannot contain multiple courses.")
        entry = registry.setdefault(
            course, {"name": metadata["options"].get("course_name", course), "lectures": {}}
        )
        if course_layout:
            if entry["lectures"] and entry.get("layout") != COURSE_LAYOUT:
                raise ValueError(
                    "Existing library layout preserved; choose a separate course root."
                )
            entry["layout"] = COURSE_LAYOUT
        for existing in entry["lectures"]:
            if existing.casefold() == lecture.casefold() and existing != lecture:
                raise ValueError("Lecture ID has a Windows case collision.")
        entry["lectures"][lecture] = {"title": title, "layout": "sections"}
        course_body = "\n".join(
            f"- [{label(item['title'])}]({key}/index.md)" for key, item in entry["lectures"].items()
        )
        if course_layout:
            files["index.md"] = markdown_page(
                "course-index", {"course": course}, entry["name"], course_body
            )
        else:
            files[course + "/index.md"] = markdown_page(
                "course-index",
                {"course": course},
                entry["name"],
                "[全部课程](../index.md)\n\n" + course_body,
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
                    "course_index": str(
                        target / "index.md" if course_layout else target / course / "index.md"
                    ),
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
    if value.split(".")[0].upper() in RESERVED:
        raise ValueError("Course name is a reserved Windows filename.")
    return value


def export(args):
    root = managed(Path(args.root).expanduser())
    course_record = managed(root, "workspace", "course.json")
    if not course_record.exists():
        return export_legacy(args)
    record = read_json(course_record)
    if record.get("layout") != COURSE_LAYOUT or record["course"] != slug(args.course):
        raise ValueError("Export course does not match this course root.")
    source = managed(root, "output")
    target = managed(Path(args.vault).expanduser(), folder_name(args.course_name))
    if target == root or target in root.parents or root in target.parents:
        raise ValueError("Vault course folder must be separate from the working root.")
    receipt_path = managed(root, "workspace", "publication", "published.json")
    if not receipt_path.exists():
        raise ValueError("No published notes to export.")
    files = {}
    for relative in read_json(receipt_path)["files"]:
        if not relative.endswith(".md"):
            continue
        note = managed(source, relative)
        body = note.read_text(encoding="utf-8-sig")
        if not body.strip() or "本节生成暂未完成" in body:
            raise ValueError(f"{relative} is incomplete.")
        files["output/" + relative] = body.encode("utf-8")
        for _, reference in IMAGE.findall(body):
            if REMOTE.match(reference):
                continue
            unresolved = (note.parent / reference).resolve()
            if not unresolved.is_relative_to(source.resolve()):
                raise ValueError("Exported image must stay inside the course output.")
            asset_relative = unresolved.relative_to(source.resolve()).as_posix()
            asset = managed(source, asset_relative)
            files["output/" + asset_relative] = asset.read_bytes()
    if "output/index.md" not in files:
        raise ValueError("Published course index is missing.")
    base = managed(root, "workspace", "exports", digest(str(target))[:24])
    with lock(base / ".export-lock"):
        receipt = managed(base, "published.json")
        previous = read_json(receipt).get("files", {}) if receipt.exists() else {}
        result, code = sync_files(
            target, files, receipt, base / "candidates", remove=set(previous) - set(files)
        )
    if not code:
        for name in ("input", "workspace"):
            managed(target, name).mkdir(parents=True, exist_ok=True)
        result.update(
            {
                "status": "exported",
                "index": str(target / "output/index.md"),
                "course_index": str(target / "output/index.md"),
            }
        )
    return result, code


def export_legacy(args):
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
            if REMOTE.match(reference):
                continue
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
            if REMOTE.match(reference):
                continue
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
    p.add_argument(
        "--options", default="{}", help="JSON object of workflow options, or @path to a JSON file"
    )
    p.add_argument("--course-name", help="Human-readable course title for the course index")
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
    p.add_argument(
        "--crop",
        help="x,y,width,height: pixels at --scale, or page fractions such as 0.1,0.2,0.6,0.5",
    )
    p.add_argument("--scale", type=float, default=1.5, help="Render scale (default 1.5)")
    p.set_defaults(handler=render)
    p = commands.add_parser("sheet", help="Render labeled thumbnail grids for slide screening")
    p.add_argument("--run", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--pages", help="For example 1-20,25; default all pages")
    p.add_argument("--per-sheet", type=int, default=20)
    p.add_argument("--columns", type=int, default=5)
    p.add_argument("--width", type=int, default=360, help="Thumbnail width in pixels")
    p.set_defaults(handler=sheet)
    p = commands.add_parser("doctor", help="Report interpreter and missing parser packages")
    p.set_defaults(handler=doctor)
    p = commands.add_parser("check", help="Report mechanical format issues in final/document.json")
    p.add_argument("--run", required=True)
    p.add_argument("--document", required=True)
    p.set_defaults(handler=check)
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
