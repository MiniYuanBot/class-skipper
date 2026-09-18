"""Read -> whole-lecture outline -> section writing -> one editorial revision."""

import re
import shutil
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .llm import Client, ModelError
from .materials import read_materials
from .storage import atomic, digest, managed, read_json, slug, write_json
from .vision import collect_figures

PROMPTS = Path(__file__).parent / "prompts"


def prompt(name):
    return (PROMPTS / f"{name}.md").read_text()


def validate_plan(value):
    if not isinstance(value.get("sections"), list) or not value["sections"]:
        raise ValueError("Outline needs sections.")
    for section in value["sections"]:
        if not isinstance(section, dict) or not isinstance(section.get("title"), str):
            raise ValueError("Each outline section needs a title.")
        if not isinstance(section.get("source_ids"), list):
            raise ValueError("Each outline section needs source_ids.")


def validate_section(value):
    if not isinstance(value.get("markdown"), str) or not value["markdown"].strip():
        raise ValueError("Missing chapter text.")
    if not isinstance(value.get("source_ids"), list):
        raise ValueError("Missing chapter sources.")


def validate_review(value):
    for field in ("replacements", "additions", "changes", "uncertainties"):
        if not isinstance(value.get(field), list):
            raise ValueError("Invalid editorial response.")
    for section in value["replacements"] + value["additions"]:
        validate_section(section)
    for section in value["replacements"]:
        if not isinstance(section.get("section_id"), str):
            raise ValueError("Missing section ID.")
    for section in value["additions"]:
        if not isinstance(section.get("title"), str):
            raise ValueError("Missing added section title.")
    for field in ("introduction", "synthesis"):
        if not isinstance(value.get(field), str):
            raise ValueError("Missing editorial synthesis.")


def text_list(value):
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def selected_ids(value, units):
    return list(dict.fromkeys(v for v in text_list(value) if v in units))


def clean_markdown(text):
    """Only application-owned citations/assets; preserve math and fenced code."""
    lines, fence, display_math = [], None, False
    for line in text.strip().splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            if fence is None:
                fence = match[1]
            elif match[1][0] == fence[0] and len(match[1]) >= len(fence):
                fence = None
            lines.append(line)
            continue
        if fence:
            lines.append(line)
            continue
        if line.strip() == "$$":
            display_math = not display_math
            lines.append(line)
            continue
        if display_math:
            lines.append(line)
            continue
        if line.strip().startswith("$$") and line.strip().endswith("$$") and len(line.strip()) > 4:
            lines.extend(["$$", line.strip()[2:-2].strip(), "$$"])
            continue
        if line.strip().startswith("|") and line.strip().endswith("|"):
            cells = re.split(r"(?<!\\)\|", line.strip())[1:-1]
            line = "| " + " | ".join(cell.strip() for cell in cells) + " |"
        line = re.sub(r"^#{1,2}\s+", "### ", line)
        line = re.sub(r"^#{5,}\s+", "#### ", line)
        line = re.sub(r"!\[([^]]*)\]\([^)]*\)", "", line)
        line = re.sub(r"\[([^]]*)\]\([^)]*\)", r"\1", line)
        if re.match(r"^\[\^[^]]+\]:", line):
            continue
        line = re.sub(r"\[\^[^]]+\]", "", line)
        spans = re.split(r"(`[^`]*`|\$[^$]*\$)", line)
        for i in range(0, len(spans), 2):
            spans[i] = re.sub(r"<[^>]*>", "", spans[i])
        line = "".join(spans)
        lines.append(line)
    if fence:
        lines.append(fence)
    return "\n".join(lines).strip()


def heading(text):
    return re.sub(r"[\r\n#\[\]<>]", " ", str(text)).strip()


def layout_issues(sections):
    issues = []
    for section in sections:
        text = section["markdown"]
        if not re.search(r"(?m)^### ", text):
            issues.append(section["id"] + ": missing concept headings")
        if not re.search(r"问|Q[1-3:]|Question", text):
            issues.append(section["id"] + ": missing useful Q&A")
        if not section.get("source_ids"):
            issues.append(section["id"] + ": no valid source references")
    return issues


def render(title, introduction, sections, synthesis, units, sources, figures, uncertainties):
    lines = ["# " + heading(title), "", clean_markdown(introduction), ""]
    footnotes = []
    for number, section in enumerate(sections, 1):
        body = clean_markdown(section["markdown"])
        inserted = set()

        def insert(match):
            fid = match[1]
            if fid in inserted or fid not in figures or fid not in section.get("figure_ids", []):
                return ""
            inserted.add(fid)
            figure = figures[fid]
            caption = heading(figure["caption"])
            return f"\n\n![{caption}](assets/{fid}.png)\n\n*{caption}*\n\n"

        body = re.sub(r"\[\[figure:([^]\n]+)\]\]", insert, body)
        lines += ["## " + heading(section["title"]), "", body, ""]
        locations = list(
            dict.fromkeys(
                sources[units[i]["source"]]["name"] + " · " + units[i]["location"]
                for i in section["source_ids"]
            )
        )
        if locations:
            lines += [f"来源：[^section-{number}]", ""]
            footnotes.append(f"[^section-{number}]: " + "；".join(locations))
    if synthesis:
        lines += ["## 本讲小结", "", clean_markdown(synthesis), ""]
    if uncertainties:
        lines += ["## 待核验与阅读提示", ""]
        lines += ["- " + clean_markdown(t).replace("\n", " ") for t in dict.fromkeys(uncertainties)]
        lines.append("")
    lines += footnotes
    return "\n".join(lines).rstrip() + "\n"


def publish(candidate, target, run_id, workspace, course):
    """Preserve manually edited files, including images and added personal files."""
    if target.exists():
        metadata = managed(workspace, "published", course, target.name + ".json")
        old = read_json(metadata).get("files", {}) if metadata.exists() else {}
        actual = {
            str(p.relative_to(target)): digest(p.read_bytes())
            for p in target.rglob("*")
            if p.is_file()
        }
        if any(p.is_symlink() for p in target.rglob("*")) or actual != old:
            return {
                "status": "manual_changes_preserved",
                "candidate": str(candidate / "notes.md"),
            }, 5
        backup = managed(workspace, "backups", course, target.name + "-" + run_id)
        backup.parent.mkdir(parents=True, exist_ok=True)
        target.rename(backup)
        try:
            shutil.copytree(candidate, target)
        except BaseException:
            if target.exists():
                shutil.rmtree(target)
            backup.rename(target)
            raise
    else:
        shutil.copytree(candidate, target)
    write_json(
        managed(workspace, "published", course, target.name + ".json"),
        {
            "files": {
                str(p.relative_to(target)): digest(p.read_bytes())
                for p in target.rglob("*")
                if p.is_file()
            }
        },
    )
    return {"notes": str(target / "notes.md")}, 0


def _generate(
    config,
    course,
    lecture,
    slides,
    transcripts=(),
    *,
    title=None,
    resume=True,
    vision=None,
    review=None,
    client_factory=Client,
    reader=read_materials,
    progress=lambda message: None,
):
    slug(course)
    slug(lecture)
    started = time.monotonic()
    config = dict(config)
    if vision is not None:
        config["vision"] = vision
    if review is not None:
        config["review"] = review
    root = managed(config["output"])
    workspace_root = managed(config["workspace"])
    if root == workspace_root or root in workspace_root.parents or workspace_root in root.parents:
        raise ValueError("output and workspace must be separate, non-nested directories.")
    target = managed(root, course, lecture)
    run_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:8]
    workspace = managed(config["workspace"])
    run = managed(workspace, "runs", course, lecture, run_id)
    run.mkdir(parents=True, exist_ok=True)
    client = client_factory(config, managed(workspace, "cache", "calls"), refresh=not resume)
    report = {
        "engine": "read-plan-write-revise",
        "course": course,
        "lecture": lecture,
        "run_id": run_id,
        "status": "reading",
        "human_acceptance": "pending",
    }
    warnings = []

    def save():
        report.update(calls=client.calls, elapsed_seconds=round(time.monotonic() - started, 2))
        write_json(run / "run.json", report)

    save()
    try:
        progress(f"{lecture}: reading complete source materials")
        material = reader(slides, transcripts)
        write_json(run / "sources.json", material)
        units = {u["id"]: u for u in material["units"]}
        sources = {s["id"]: s for s in material["sources"]}
        warnings.extend(material["warnings"])
        total = sum(len(u["text"]) for u in units.values())
        if total > config["max_source_chars"]:
            raise ValueError(
                "Lecture exceeds max_source_chars; increase it or split the lecture. "
                "No text was truncated."
            )
        figures, visual_context = {}, {}

        sparse = [u["id"] for u in units.values() if len(u["text"]) < 40 and u.get("page")]
        if not total:
            raise ValueError("No readable text; supply an OCR PDF or transcript before planning.")
        source_payload = [{k: v for k, v in u.items() if k != "page"} for u in units.values()]
        report["status"] = "planning"
        save()
        progress(f"{lecture}: planning from all {len(units)} source units ({total} characters)")
        plan = client.ask(
            "plan",
            prompt("plan"),
            {
                "title": title or lecture,
                "language": config["language"],
                "materials": source_payload,
                "visual_readings": visual_context,
            },
            validate=validate_plan,
        )
        for i, section in enumerate(plan["sections"], 1):
            section["id"] = f"section-{i}"
            wanted = selected_ids(section["source_ids"], units)
            if not wanted:
                wanted = list(units)
                warnings.append(
                    f"section-{i}: outline lacked valid references; writer received all material."
                )
            section["source_ids"] = wanted
            section["figure_ids"] = selected_ids(section.get("figure_ids"), units)
        write_json(run / "outline.json", plan)
        if config["vision"]:
            report["status"] = "reading_figures"
            save()
            progress(f"{lecture}: Kimi locating and verifying mechanism diagrams")
            figures, visual_context, visual_warnings = collect_figures(
                client, config, run, units, sources, plan, progress
            )
            warnings.extend(visual_warnings)
        for section in plan["sections"]:
            section["selected_figures"] = [
                fid for fid, figure in figures.items() if figure["section_id"] == section["id"]
            ]
        write_json(run / "visual.json", visual_context)
        report["status"] = "writing"
        save()
        progress(
            f"{lecture}: writing {len(plan['sections'])} sections, {config['workers']} at a time"
        )
        sections, failures = {}, []

        def write_section(section):
            answer = client.ask(
                "write:" + section["id"],
                prompt("write"),
                {
                    "language": config["language"],
                    "section_chars": config["section_chars"],
                    "lecture_map": [
                        {"title": s["title"], "goal": s.get("goal", "")} for s in plan["sections"]
                    ],
                    "requested_section": section,
                    "materials": [units[i] for i in section["source_ids"]],
                    "visual_readings": {i: visual_context[i] for i in section["selected_figures"]},
                },
                validate=validate_section,
            )
            result = dict(
                section,
                markdown=answer["markdown"],
                summary=answer.get("summary", ""),
                uncertainties=text_list(answer.get("uncertainties")),
                source_ids=selected_ids(
                    answer["source_ids"], {i: units[i] for i in section["source_ids"]}
                ),
                figure_ids=section["selected_figures"],
            )
            write_json(run / "sections" / (section["id"] + ".json"), result)
            return result

        with ThreadPoolExecutor(max_workers=config["workers"]) as pool:
            jobs = {pool.submit(write_section, s): s for s in plan["sections"]}
            for job in as_completed(jobs):
                section = jobs[job]
                try:
                    sections[section["id"]] = job.result()
                    progress(f"{lecture}: finished {section['title']}")
                except (ModelError, ValueError) as exc:
                    failures.append(section["id"])
                    sections[section["id"]] = dict(
                        section,
                        markdown="本节生成暂未完成，请续跑。",
                        uncertainties=["Section generation failed."],
                        summary="",
                    )
                    warnings.append(f"{section['title']}: {type(exc).__name__}; rerun to complete.")
                save()
        ordered = [sections[s["id"]] for s in plan["sections"]]
        introduction, synthesis = plan.get("learning_thread", ""), ""
        write_json(run / "draft.json", {"sections": ordered})
        review_result = {"changes": [], "uncertainties": [], "status": "disabled"}
        if config["review"] and not failures:
            report["status"] = "revising"
            save()
            progress(f"{lecture}: reviewing and revising the complete lecture once")
            try:
                review_result = client.ask(
                    "review",
                    prompt("review"),
                    {
                        "language": config["language"],
                        "materials": source_payload,
                        "visual_readings": visual_context,
                        "outline": plan,
                        "draft": ordered,
                        "layout_issues": layout_issues(ordered),
                    },
                    validate=validate_review,
                )
                for patch in review_result["replacements"]:
                    if patch["section_id"] not in sections:
                        warnings.append(
                            "Editor returned an unknown section; that replacement was ignored."
                        )
                        continue
                    section = sections[patch["section_id"]]
                    section.update(
                        markdown=patch["markdown"],
                        source_ids=selected_ids(patch["source_ids"], units),
                        uncertainties=[],
                    )
                for addition in review_result["additions"]:
                    addition = dict(
                        addition,
                        id=f"section-{len(ordered) + 1}",
                        figure_ids=[],
                        source_ids=selected_ids(addition["source_ids"], units),
                    )
                    ordered.append(addition)
                introduction = review_result["introduction"] or introduction
                synthesis = review_result["synthesis"]
                review_result["status"] = "completed"
            except (ModelError, ValueError) as exc:
                review_result = {"status": "unavailable", "changes": [], "uncertainties": []}
                warnings.append(
                    f"Editorial revision unavailable ({type(exc).__name__}); draft retained."
                )
        write_json(run / "review.json", review_result)
        uncertainties = text_list(review_result.get("uncertainties"))
        for section in ordered:
            if review_result["status"] != "completed":
                uncertainties.extend(text_list(section.get("uncertainties")))
            if not section["source_ids"]:
                uncertainties.append(section["title"] + "：来源定位需核验。")
        report.update(
            status="partial" if failures else "complete",
            warnings=warnings,
            review_status=review_result["status"],
            failed_sections=failures,
            layout_warnings=layout_issues(ordered),
            source_units=len(units),
            source_characters=total,
            sections=len(ordered),
            figures=len(figures),
        )
        if review_result["status"] == "unavailable":
            uncertainties.append("自动校订未完成；当前保留完整初稿，稍后可续跑。")
        if sparse:
            unread = [i for i in sparse if i not in visual_context]
            if unread:
                uncertainties.append(
                    "部分页面文本稀少且未识别图像，请对照原文：" + "、".join(unread)
                )
        candidate = run / "candidate"
        candidate.mkdir()
        used_figures = {
            fid
            for s in ordered
            for fid in s.get("figure_ids", [])
            if fid in figures and "[[figure:" + fid + "]]" in s["markdown"]
        }
        report["figures_selected"] = len(figures)
        report["figures"] = len(used_figures)
        for fid in used_figures:
            atomic(candidate / "assets" / (fid + ".png"), Path(figures[fid]["path"]).read_bytes())
        note = render(
            title or plan.get("title", lecture),
            introduction,
            ordered,
            synthesis,
            units,
            sources,
            figures,
            uncertainties,
        )
        atomic(candidate / "notes.md", note)
        save()
        target.parent.mkdir(parents=True, exist_ok=True)
        publication, code = publish(candidate, target, run_id, workspace, course)
        report.update(publication)
        save()
        return report, code or (3 if failures else 0)
    except (ValueError, ModelError, OSError):
        report["status"] = "failed"
        save()
        raise


def generate(config, course, lecture, *args, **kwargs):
    """One writer per lecture; OS releases the lock after interruption."""
    import fcntl

    slug(course)
    slug(lecture)
    lock = managed(config["workspace"], "locks", course, lecture + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError(
                "This lecture is already generating; wait for that run to finish."
            ) from None
        try:
            return _generate(config, course, lecture, *args, **kwargs)
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)
