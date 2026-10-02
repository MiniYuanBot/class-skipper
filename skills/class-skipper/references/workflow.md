# Local operations and artifact contracts

The helper is self-contained. Use `<python>` for the selected Python 3.11+
interpreter, `<skill>` for the installed folder, and `<root>` for the user's output
workspace. Windows and macOS use the same arguments; quote paths with spaces.
All files written by Codex must use UTF-8. Text input is UTF-8 (BOM accepted).

## Canonical directories

Use this structure for every new skill run. IDs are portable names; human-readable
Chinese titles are note properties and headings, not inferred filenames.

```text
<root>/
  input/                         User source files only
    course.yaml                  Optional manifest; paths relative to this file
    os/l02/slides.pdf
    os/l02/transcript.docx
  workspace/                     Private intermediate work; never import into Obsidian
    os/l02/<run-id>/
      run.json                   Version, source identity, root, IDs, title, options
      materials.json             Complete sources, located units, parser warnings
      status.json                Four-step progress and publication result
      plan.json                  Full lecture plan
      requests/                  One exact request JSON per reasoning task
      chapters/section-1.json     Completed chapter response (not published Markdown)
      visuals/readings.json      Verified/skipped visual records
      visuals/pages/             Rendered original PDF pages
      visuals/crops/             Candidate and verified crops
      draft/notes.md             Assembled draft for the single editor
      revision/review.json       The single editorial response
      final/document.json        Corrected structured lecture for publication
      cache/                     Completed responses and refresh history
    publication/                 Protected structured-output receipts and registry
  output/                        Final Obsidian-compatible library only
    index.md                     Course navigation
    os/index.md                  Lecture navigation
    os/l02/index.md              Learning thread, chapter navigation, synthesis
    os/l02/chapters/section-1.md  One Markdown note per major planned section
    os/l02/chapters/section-2.md
    os/l02/assets/diagram.png    Only images referenced by published chapters
```

Do not scatter temporary pages, logs, JSON, drafts or cache files into input/output.
Use the prepared run's subfolders for agent-owned work. A failed or incomplete run
stays in workspace and does not replace the existing completed output. Receipts,
export candidates and conflict versions also stay in workspace. Earlier runs keep
their existing files; do not move or delete old caches or handwritten notes.

New run, material, status, request and reasoning-response JSON artifacts have
`schema_version: 1`; helper receipts and cache envelopes retain their own field
contracts. JSON is UTF-8, with
two-space indentation and a final newline. Keep lists in source/plan order and
use source unit IDs verbatim. Read unknown schema versions explicitly rather than
silently interpreting them as the current format.

`status.json` uses `stages` for reading (includes planning), writing, visuals and
revision, with values `pending`, `running`, `complete`, `skipped` or `failed`;
`chapters` maps each section ID to its status and response path. Record `unread_locations`,
`cache_hits` and `publication` only as actually observed. These fields track the
existing workflow; they do not add independent review stages.

Local parser dependencies, installed only as needed:

| Input/action | Package |
| --- | --- |
| TXT, Markdown, caching/publication | Python standard library |
| PDF extraction and rendering | `pypdfium2` |
| DOCX extraction | `python-docx` |
| PPTX extraction | `python-pptx` |
| Image crops | `Pillow` |
| YAML course manifest | `PyYAML` (read in Codex; expand into prepare calls) |

For binary inputs, install the necessary packages with `<python> -m pip install`.
Do not install this repository's API client or copy credential configuration.

## Prepare and source reading

```text
<python> <skill>/scripts/local.py prepare --root <root> --course os --lecture l02 --title "操作系统" --slides "<slides.pdf>" --transcript "<transcript.docx>"
```

Repeat `--slides`/`--transcript` to include all files; transcripts are optional.
The response identifies a run folder containing `materials.json`, `run.json`,
`status.json` and the intermediate subfolders above.
`materials.json` contains sources (`id`, `path`, `name`, `role`, `sha256`), units
(`id`, `source`, `location`, optional `page`, `text`, `role`) and parser warnings.
Read every unit. Source locations are PDF page, slide, DOCX body range, or text
segment. Do not equate empty extracted text with an empty academic page.

Write all intermediate artifacts inside the run folder, never inside the installed
skill. On resume, verify source hashes and task/cache identity before reusing files.
Update `status.json` using the contract above. A present partial file is not a
completed response.

## Responses and caching

Plan response (`plan.json`):

```json
{"schema_version":1,"title":"...","learning_thread":"...","topics":["..."],"sections":[{"id":"section-1","title":"...","goal":"...","key_points":["..."],"source_ids":["s1p1","s2b1"],"figure_ids":[]}],"omitted":"..."}
```

Chapter response (`chapters/section-1.json`):

```json
{"schema_version":1,"markdown":"### 概念\n\n...","summary":"...","source_ids":["s1p1"],"uncertainties":[]}
```

Editor response (`revision/review.json`):

```json
{"schema_version":1,"introduction":"...","synthesis":"...","replacements":[{"section_id":"section-1","markdown":"...","source_ids":["s1p1"]}],"additions":[],"changes":["concrete corrections"],"uncertainties":[]}
```

An addition is only for a missing core topic and includes `title`, `markdown` and
`source_ids`. Empty replacements/additions are valid. Apply replacements; do not
merely list a fixable issue in `changes`. Verify returned IDs belong to supplied
units/sections and response bodies are complete before caching. Invalid/truncated
responses remain uncached; report failure or resume later without endless retries.

Before each reasoning task, write `requests/<task-id>.json` with `schema_version`,
`stage`, `instructions` (the
actual full task prompt text, not a filename), and `options` (an object). Include
or hash the current SKILL.md and this reference, not just a short role name.
Options contain language, title, target length, visual/revision choices and Codex
model identity (if exposed; otherwise record `current-session`). Keep the request
consistent between lookup and store. Include actual upstream
files: full plan + raw assigned units for writing; complete draft + plan + visual
readings for revision; image file + coordinates + raw context for visual reading.

```text
<python> <skill>/scripts/local.py cache lookup --run <run> --request <request.json> --upstream <plan.json>
<python> <skill>/scripts/local.py cache store --run <run> --request <request.json> --upstream <plan.json> --response <chapter.json>
```

Repeat `--upstream` for every dependent artifact, including binary images. Keep
their argument order stable between lookup, store and resume; order affects the key.
Lookup identifies a hit or miss. On hit, read and reuse the complete response.
Responses are explicit local artifacts produced by Codex, not provider prompt
caches. Source, instruction, option or upstream changes invalidate reuse. Refresh
bypasses lookup; use `cache store --refresh` to archive the previous complete
response and activate the new one. Without this flag a differing response under
the same key is preserved rather than replaced.

## Writing and assembly

The workspace draft uses one H1 lecture title, a short learning thread, H2 major
chapters and H3 concept headings, with optional H4 derivations. Writers return
bodies with H3/H4 only. Publication splits this into one note per major chapter;
each published chapter gets one H1 title, H2 concepts and optional H3 details.
The publisher promotes body headings outside code blocks. Its parent lecture
index contains the learning thread, linked chapter list and final synthesis.
Define concepts, explain purpose/mechanism and give a concrete source-backed example.
Introduce terms as Chinese (English), compare real dimensions in compact tables,
use numbered process steps and explain mathematical symbols and meanings.
Use `$...$` and standalone `$$` blocks. Keep meaningful code/pseudocode correct.
Each chapter ends with 1–3 useful Q&A, usually 1–2; avoid repeating the explanation
in answers. Do not mechanically fill a fixed checklist or expand into a transcript.

Normalize Markdown string line endings to `\n` before assembly on either platform;
preserve spacing inside code and tables. The coordinator attaches draft source
footnotes using actual `name · location`
values from `materials.json`; retain exact unit IDs in artifacts. Add a short
`本讲小结` and only specific unresolved `待核验与阅读提示` when necessary. Incomplete
chapters use a visible `本节生成暂未完成` notice and remain local. When applying the
editor's replacements, retain existing citations and avoid appending duplicate
footnote definitions that the editor already preserved.

## Selective images

```text
<python> <skill>/scripts/local.py render --run <run> --source s1 --page 2 --output <run>/visuals/pages/s1-p2.png
<python> <skill>/scripts/local.py render --run <run> --source s1 --page 2 --crop x,y,w,h --output <run>/visuals/crops/diagram.png
```

Consult `render --help` for the coordinate convention. Inspect the whole rendered
page before selecting coordinates, then inspect the actual saved crop. Record a
visual reading in `visuals/readings.json` as
`{"schema_version":1,"status":"complete","readings":[...]}`. Each reading has
`source_id`, `page`, `crop`, `path`, `caption`, `visible_content`, `section_id` and
`status` (`verified` or `skipped`). When visuals are skipped, set top-level status
to `skipped` and use an empty list. Include only verified, relevant
images in the draft. Do not fabricate figures or model-generated replacements.

## Publish and optional export

```text
<python> <skill>/scripts/local.py publish --run <run> --document <run>/final/document.json --asset <run>/visuals/crops/diagram.png
<python> <skill>/scripts/local.py export --root <root> --course os --vault "<vault-root>" --course-name "操作系统"
```

After applying the editor, write `final/document.json`:

```json
{"schema_version":1,"title":"讲次标题","introduction":"导读","synthesis":"本讲小结","sections":[{"id":"section-1","title":"板块标题","markdown":"### 核心概念\n\n正文","source_ids":["s1p1"]}],"uncertainties":[]}
```

Section order is the final reading order. IDs are unique and stable. Return raw
chapter bodies without coordinator-added footnotes; the publisher attaches exact
source locations. Include editorial additions as complete final sections.
Repeat `--asset` for referenced images. Reference them as `assets/diagram.png` in
section bodies; publication rewrites them to `../assets/diagram.png` for chapter
files. The structured publisher creates the output tree above, with relative links
and parent-index backlinks. Hash receipts preserve manual changes in notes, assets
and indexes; conflicting output stays in a candidate folder. Compare it without
overwriting the user's file. Export copies existing complete notes and referenced
images to the requested Obsidian course folder without regenerating content.
Inspect the JSON result and process exit code; conflicts are preserved, not success.
No Obsidian plugin or `.obsidian` settings change is needed. Open `output/` as a
vault and start at `index.md`. Structured export to an existing vault creates
`<vault>/<course-name>/index.md` plus `<course-id>/index.md` and its lecture/chapters
tree, forming a complete single-course library with valid relative backlinks.
The legacy `--note` option supports earlier single-file publications only; new
skill runs must use `--document`.

## Published Markdown contract

All notes and indexes begin with YAML properties. Use `schema_version: 1`, `type`,
`title`; course-level files also have `course`, lecture-level files have `lecture`,
and chapter files have `section`. Types are `library-index`, `course-index`,
`lecture-index` and `course-note`. Properties use quoted human-readable titles and
stable IDs. Do not insert private absolute paths, prompts, cache identifiers or
execution logs into the published note.

Each chapter contains its title, a parent-index link, the conceptual explanation
with formulas/examples/comparisons, verified diagrams beside matching prose,
1–3 Q&A and a source-location footer. The lecture index contains its title,
parent-index link, learning thread, ordered chapter links, synthesis and only
material unresolved questions. Root/course indexes contain ordered links to the
next level. Standard Markdown links, LaTeX and footnotes work in Obsidian without
plugins; avoid custom code blocks for internal status data.
