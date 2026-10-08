# Local operations and artifact contracts

The helper is self-contained. `<python>` is the selected Python 3.11+ interpreter,
`<skill>` is the folder containing SKILL.md, and `<root>` is one course folder
beneath the notebook/Obsidian vault root. Windows and macOS use the same arguments;
quote every path, because course and vault paths often contain spaces or Chinese.
All files written by the agent use UTF-8. Text input is UTF-8 (BOM accepted).

Writing rules and the chapter template are in [note-style.md](note-style.md);
figure, Mermaid and external-resource rules are in [visuals.md](visuals.md).

## Python environment

```text
<python> <skill>/scripts/local.py doctor
```

`doctor` prints the interpreter, version and missing parser packages, plus the
exact `pip install` command for that interpreter. Pick `<python>` as follows:

| Host shell | Try in order |
| --- | --- |
| macOS / Linux | `python3`, then `python` |
| Windows PowerShell or cmd | `py -3`, then `python` |
| Windows Git Bash (Claude Code) | `py -3`, then `python` (avoid the Microsoft Store stub) |

If packages are missing, create a virtual environment in `<root>/workspace/.venv`
(`<python> -m venv "<root>/workspace/.venv"`) and use its interpreter for every
later command: `workspace/.venv/bin/python` on macOS, `workspace\.venv\Scripts\python.exe`
on Windows. Install only what `doctor` lists. No model client or credentials are
needed.

| Input/action | Package |
| --- | --- |
| TXT, Markdown, caching, check, publication | Python standard library |
| PDF extraction, rendering and contact sheets | `pypdfium2`, `Pillow` |
| DOCX extraction | `python-docx` |
| PPTX extraction | `python-pptx` |
| YAML course manifest | read by the agent and expanded into `prepare` calls |

## Canonical directories

The notebook root holds `.obsidian/` and sibling course folders. `<root>` and the
helper's `--root` mean one course folder, not the notebook root. Lecture
directories use uppercase `LXX`, padded to at least two digits.

```text
<notebook-root>/                 User-selected Obsidian vault root
  .obsidian/                    Existing vault configuration; never modify
  computer-organization-and-architecture/  <root>: one course
    input/                      User source files only
      course.yaml               Optional manifest; paths relative to this file
      L02/slides.pdf
      L02/transcript.docx
    workspace/                  Private intermediates
      course.json               Course-root identity and layout marker
      L02/<run-id>/
        run.json                Version, source identity, root, IDs, title, options
        materials.json          Complete sources, located units, parser warnings
        status.json             Four-step progress and publication result
        plan.json               Full lecture plan, including figure candidates
        requests/               One exact request JSON per reasoning task
        chapters/section-1.json Completed chapter response
        visuals/sheets/         Contact sheets used for slide screening
        visuals/pages/          Rendered original PDF pages
        visuals/crops/          Candidate and verified crops
        visuals/readings.json   Verified/skipped visual records
        draft/notes.md          Assembled draft for the single editor
        revision/review.json    The single editorial response
        final/document.json     Corrected structured lecture for publication
        cache/                  Completed responses and refresh history
      publication/              Protected output receipts and course registry
      exports/                  Export receipts and conflict candidates
    output/                     Final notes for this course only
      index.md                  Ordered lecture navigation
      L02/
        index.md                Introduction, chapter links with summaries, synthesis
        chapters/01-process-model.md  One note per section: NN + English slug
        chapters/02-threads-and-concurrency.md
        assets/l02-thread-states.png  Only when a chapter references it
  operating-systems/            Another independent course root
```

Resolve the course folder from the request, manifest or source paths. Do not put
input/output/workspace directly under a vault root or add a course-ID layer within
output/workspace. `prepare` accepts `2`, `02`, `l2` or `L02` and stores `L02`; a
non-numbered lecture needs its actual number before preparation. Each course root
is bound to one course ID. Do not rename input folders automatically.

New run metadata records `layout: "course-root-v1"`. Runs without that marker keep
the earlier workspace/course/lecture structure for resume, publication and export
(including `section-id.md` chapter filenames). Do not move or delete existing runs,
caches or outputs. A failed or incomplete run stays in workspace and does not
replace completed output. Never scatter temporary files into input/ or output/.

JSON artifacts written by the agent use `schema_version: 1`, UTF-8, two-space
indentation and a final newline. Keep lists in source/plan order and use source
unit IDs verbatim.

`status.json` uses `stages` for reading (includes planning), writing, visuals and
revision, with values `pending`, `running`, `complete`, `skipped` or `failed`;
`chapters` maps each section ID to its status and response path. Record
`unread_locations`, `cache_hits` and `publication` only as actually observed.

## Prepare and source reading

```text
<python> <skill>/scripts/local.py prepare --root "<root>" --course coa --lecture L02 --title "L02 性能与指令集" --course-name "计算机组成与体系结构" --slides "<root>/input/L02.pdf" --transcript "<root>/input/L02.docx"
```

Repeat `--slides`/`--transcript` for every file; transcripts are optional.
`--options` takes a JSON object or `@path/to/options.json` (use the file form on
Windows to avoid shell quoting problems). `--course-name` sets the course index
title. The response names the run folder.

`materials.json` contains sources (`id`, `path`, `name`, `role`, `sha256`), units
(`id`, `source`, `location`, optional `page`, `text`, `role`) and parser warnings.
Unit IDs look like `s1p12` (PDF page / slide) and `s2b3` (DOCX/TXT body range).
Read every unit. Empty extracted text is not an empty academic page: screen PDFs
with `sheet` (see visuals.md) during this step.

On resume, verify source hashes and task/cache identity before reusing files. A
present partial file is not a completed response.

## Responses and caching

Plan response (`plan.json`):

```json
{"schema_version":1,"title":"L03 运算与流水线","learning_thread":"...","topics":["..."],
 "sections":[{"id":"section-1","title":"01 整数运算电路","slug":"integer-arithmetic","goal":"...","key_points":["..."],
   "source_ids":["s1p3","s2b1"],"figure_ids":["s1p7"],"owns":["行波进位加法器","溢出检测"]}],
 "omitted":"..."}
```

`slug` is the English file-name stem for the chapter: lowercase ASCII words
joined by hyphens, at most ten words, translating the Chinese title (for example
`01 进程模型` → `process-model`). `owns` lists the concepts whose main explanation
lives in that section, so other writers link instead of repeating them.

Chapter response (`chapters/section-1.json`):

```json
{"schema_version":1,"markdown":"> [!abstract] 本节要点\n> - ...\n\n### 概念\n\n...",
 "summary":"一句话摘要","source_ids":["s1p3"],"visual_suggestions":[],"uncertainties":[]}
```

Editor response (`revision/review.json`):

```json
{"schema_version":1,"introduction":"...","synthesis":"...",
 "replacements":[{"section_id":"section-1","markdown":"...","summary":"...","source_ids":["s1p3"]}],
 "additions":[],"changes":["concrete corrections"],"uncertainties":[]}
```

An addition is only for a missing core topic and includes `title`, `markdown`,
`summary` and `source_ids`. Apply replacements; do not merely list a fixable issue
in `changes`. Verify returned IDs belong to supplied units/sections and bodies are
complete before caching. Invalid or truncated responses stay uncached.

Before each reasoning task, write `requests/<task-id>.json` with `schema_version`,
`stage`, `instructions` (the actual full task prompt text, including the shared
writing brief for writers and the editor), and `options` (language, title, target
length, visual/revision choices and the model identity if exposed, otherwise
`current-session`). Include or hash the current SKILL.md and reference files.
Include the actual upstream files: full plan + assigned raw units for writing;
complete draft + plan + visual readings for revision; image + coordinates + raw
context for visual reading.

```text
<python> <skill>/scripts/local.py cache lookup --run "<run>" --request "<request.json>" --upstream "<plan.json>"
<python> <skill>/scripts/local.py cache store --run "<run>" --request "<request.json>" --upstream "<plan.json>" --response "<chapter.json>"
```

Repeat `--upstream` for every dependent artifact, including images, in a stable
order. On a hit, reuse the stored response. Source, instruction, option or
upstream changes invalidate reuse. A refresh bypasses lookup; `cache store
--refresh` archives the previous response. Without it a differing response under
the same key is preserved rather than replaced.

## Assembly and the single revision

The workspace draft is one H1 lecture title, the introduction, H2 chapters in plan
order and the writers' H3/H4 bodies. Normalize line endings to `\n`. Incomplete
chapters carry a visible `本节生成暂未完成` notice and are never published.

After the editor's response is applied, write `final/document.json`:

```json
{"schema_version":1,"title":"L03 运算与流水线","introduction":"导读","synthesis":"本讲小结",
 "sections":[{"id":"section-1","title":"01 整数运算电路","slug":"integer-arithmetic","summary":"一句话摘要",
   "markdown":"> [!abstract] 本节要点\n> - ...\n\n### 核心概念\n\n正文","source_ids":["s1p3"]}],
 "uncertainties":[]}
```

Section order is the final reading order. IDs are unique and stable. Then run the
format check once and fix every reported item directly in `final/document.json`:

```text
<python> <skill>/scripts/local.py check --run "<run>" --document "<run>/final/document.json"
```

`check` reports mechanical problems only (title formats, missing summaries or slugs,
heading levels, bold-label boundaries, unbalanced `$$` or code fences, unknown
footnote IDs, missing self-tests). It is not a score or acceptance gate; fix the
items in the same revision and do not loop.

## Publish and optional export

```text
<python> <skill>/scripts/local.py publish --run "<run>" --document "<run>/final/document.json" --asset "<run>/visuals/crops/l03-single-cycle-datapath.png"
<python> <skill>/scripts/local.py export --root "<root>" --course coa --vault "<vault-root>" --course-name "computer-organization-and-architecture"
```

Repeat `--asset` for each referenced local image; reference it in section bodies as
`assets/<filename>` (the publisher rewrites it to `../assets/<filename>`). Remote
`https://` images and links are left unchanged. Return chapter bodies without
footnote definitions or source lines: the publisher defines every `[^unit-id]`
marker actually used and appends a collapsed source list built from `source_ids`.
An unknown marker fails publication.

Hash receipts preserve manual changes in notes, assets and indexes; conflicting
output is written to a candidate folder in workspace and the command exits 5.
Inspect the JSON result and exit code; conflicts are preserved, not success.
Chapters retired from a lecture are removed only if unchanged since publication.

Publishing inside the vault already completes the layout; open the notebook root
(the folder containing `.obsidian/`) and start at `<course-folder>/output/index.md`.
Optional export copies published notes and referenced images to
`<vault>/<course-name>/output/`, creates empty `input/` and `workspace/` siblings
if absent, preserves manual edits, and never copies sources, caches or
`.obsidian` configuration. The legacy `--note` option supports earlier
single-file publications only; new runs use `--document`.

## Published Markdown contract

All notes and indexes begin with YAML properties: `schema_version: 1`, `type`,
`title`, `aliases` (the display title, so `[[01 进程模型]]` resolves in Obsidian);
lecture-level files add `course` and `lecture`, chapter files add `section`;
lecture indexes and chapters also carry `excerpt` (the chapter summary) and
`tags` (the course name) for the blog the notes are published to. Types
are `course-index`, `lecture-index` and `course-note`. No private absolute paths,
prompts, cache identifiers or logs appear in published notes.

File and folder names are English ASCII; note content stays in the note language.
A chapter file is the title number plus the section `slug`
(`01 进程模型` + `process-model` → `01-process-model.md`); without a slug the
section ID is used, and a collision appends the section ID. A non-ASCII slug fails
publication. The Chinese title stays the H1, the `title` property and an alias.

Each chapter contains: H1 title; top navigation; the `[!abstract]` key points;
H2 concept sections with formulas, examples, comparisons and verified visuals;
self-test callouts; a collapsed `> [!info]- 来源` list with merged page ranges per
file; footnote definitions for markers used; and bottom navigation.

Navigation is `[本讲目录](../index.md) · [课程目录](../../index.md)` followed by
`[上一节：NN Topic](<file>)` and `[下一节：NN Topic](<file>)` in final section
order, at both top and bottom. The first section has no previous link, the last
no next link; links never wrap or cross lectures.

The lecture index contains its title, `[课程目录](../index.md)`, the introduction,
`## 章节导航` with one line per chapter (`- [01 进程模型](chapters/01-process-model.md)：summary`),
`## 本讲小结`, `## 不确定事项` only when material issues remain, and the collapsed
source list. The course `output/index.md` lists lectures in publication order, e.g.
`- [L02 性能与指令集](L02/index.md)`. Standard Markdown links, LaTeX, footnotes,
callouts and Mermaid render in Obsidian without plugins.
