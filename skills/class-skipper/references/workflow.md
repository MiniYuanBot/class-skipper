# Local operations and artifact contracts

The helper is self-contained. Use `<python>` for the selected Python 3.11+
interpreter, `<skill>` for the installed folder, and `<root>` for one course folder
beneath the notebook/Obsidian vault root. Windows and macOS use the same arguments; quote paths with spaces.
All files written by Codex must use UTF-8. Text input is UTF-8 (BOM accepted).

## Canonical directories

Use this structure for every new skill run. The notebook root holds `.obsidian/`
and sibling course folders. `<root>` and helper `--root` mean one course folder,
not the notebook root. Course IDs remain metadata, not repeated subdirectories.
Human-readable titles remain note properties/headings; lecture directories use
uppercase `LXX`, padded to at least two digits. The standard subfolder is `chapters/`.

```text
<notebook-root>/                 User-selected Obsidian vault root
  .obsidian/                    Existing vault configuration; never modify
  computer-organization-and-architecture/  <root>: one course
    input/                      User source files only
      course.yaml               Optional manifest; paths relative to this file
      L02/slides.pdf
      L02/transcript.docx
    workspace/                  Private intermediates
      course.json               Course-root identity and directory-layout marker
      L02/<run-id>/
        run.json                Version, source identity, root, IDs, title, options
        materials.json          Complete sources, located units, parser warnings
        status.json             Four-step progress and publication result
        plan.json               Full lecture plan
        requests/               One exact request JSON per reasoning task
        chapters/section-1.json  Completed chapter response
        visuals/readings.json   Verified/skipped visual records
        visuals/pages/          Rendered original PDF pages
        visuals/crops/          Candidate and verified crops
        draft/notes.md          Assembled draft for the single editor
        revision/review.json     The single editorial response
        final/document.json     Corrected structured lecture for publication
        cache/                  Completed responses and refresh history
      publication/              Protected output receipts and course registry
      exports/                  Export receipts and conflict candidates
    output/                     Final notes for this course only
      index.md                  Ordered lecture navigation
      L02/
        index.md                Learning thread, chapter navigation, synthesis
        chapters/section-1.md    One Markdown note per major planned section
        chapters/section-2.md
        assets/diagram.png      Only when a chapter references this image
      L03/
        index.md
        chapters/...
  operating-systems/            Another independent course root
    input/
    output/
    workspace/
```

Resolve the course folder from the request, manifest or source paths. Do not put
input/output/workspace directly under a vault root or add a course-ID layer within
output/workspace. `prepare` accepts `2`, `02`, `l2` or `L02` and stores `L02`; a
non-numbered lecture needs its actual lecture number before preparation. Each
course root is bound to one course ID. Do not rename input folders automatically.
New run metadata records `layout: "course-root-v1"`. Existing run metadata without
that marker retains the earlier workspace/course/lecture structure for resume,
publication and export. Do not move or delete existing runs or outputs to adopt
the new layout; generate new notes in the selected course folder.

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
These dependencies only parse local files; no model client or credential setup is needed.

## Prepare and source reading

```text
<python> <skill>/scripts/local.py prepare --root <root> --course os --lecture L02 --title "L02 进程与线程" --slides "<slides.pdf>" --transcript "<transcript.docx>"
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

### Concise, consistent titles

Use `LXX Topic` for every lecture display title: uppercase `L`, the actual lecture
number padded to at least two digits, one space, and a concise topic phrase, e.g.
`L02 进程与线程`. Use the same title in the plan, draft H1, final document, lecture
index H1/YAML title and course index link. Derive the number from source names or
the manifest; do not confuse a course title with a lecture topic or invent a number.
If the number cannot be established, ask for it before publication. Preserve stable
course/lecture IDs and paths; a display-title change is not an ID rename.

Use `NN Topic` for major section titles, e.g. `01 进程模型`, `02 线程与并发`.
Number them in final reading order, including editorial additions, and use the
same title in the plan, draft, final sections, chapter H1/YAML title and navigation
labels. Preserve section IDs when renumbering display titles. Aim for 4–12 Chinese
characters in the topic phrase when natural; clarity takes priority over a rigid
length limit. Use parallel noun phrases, avoid subtitles or lists of every covered
concept. H3/H4 concept headings in writer bodies remain short, parallel phrases
without repeated lecture/section prefixes.

### Knowledge-first narration

The final notes must make knowledge itself the subject of the narration. Write
self-contained statements a student can study directly: definitions, mechanisms,
relationships, conditions, reasoning and examples. Do not merely summarize the
sequence or presentation of a class, slide deck or transcript.

Rewrite routine classroom meta-narration such as `讲师用……说明……`, `老师指出……`,
`课件以……为例……`, `PPT 展示了……`, `本页介绍……`, `随后讲师讲解……` and
`课程首先……然后……`. Apply this principle to equivalent wording, not just these
exact phrases. Keep the underlying knowledge, source-backed example and conditions;
do not simply delete the attribution and leave a vague sentence.

Avoid: `讲师用流水线的例子说明吞吐率与延迟的区别。`
Prefer: `延迟描述完成单个任务所需的时间；吞吐率描述单位时间内能够完成的任务数量。
流水线主要提升吞吐率，而不一定降低单个任务的延迟。`

Retain attribution only when the instructor's personal emphasis, exam guidance,
experience-based judgment, or a special source organization itself has learning
value. Label it explicitly, e.g. `**课堂强调**：区分 latency 与 throughput。`
Such claims must be supported by the supplied material; never invent exam hints or
turn a personal judgment into a universal fact. Ordinary provenance belongs in
source footnotes and the source footer, which must remain intact.

Include these rules in the full English instructions given to chapter writers and
the editor, covering introductions, synthesis, captions and Q&A as well as chapter
prose. During the existing single revision, correct meta-narration in place while
preserving academic content and useful source attribution.

### Knowledge density and emphasis

Lead with the concept, result or rule and its necessary conditions, then explain
the mechanism or show its application. Use direct verbs and familiar terms. A
simple definition can be one sentence; a difficult mechanism may need several
steps, a worked example or a derivation. Density means useful learning per sentence,
not a word-count target or removing prerequisites and intermediate reasoning.

Experimental limitations belong in the prose only when they change how to use the
conclusion; express them in one short qualification attached to that conclusion.
Avoid organizing paragraphs around provenance, evidence sufficiency or imagined
misreadings (`材料没有说明……`, `不能推广为……`, `不能认为……`). Write the supported
rule with its scope instead. Real misconceptions may still deserve a direct
contrast when it teaches a distinction; do not append speculative rebuttals to
every statement. Never turn a local observation into a universal law.

For example, instead of the SSD paragraph about missing drive types and several
claims that cannot be inferred, write:
`SSD 长期断电保存时也可能出现数据错误。一项实验中，约 100 块 SSD 离线三个月后，
21 块出现错误；该比例仅代表这次实验。` Keep this observation separate from retention
noise/ECC mechanisms unless the sources actually connect them. Do not equate an
observed error with unrecoverable data loss, or invent a maintenance interval.

Keep terminology corrections in their corrected form. Put a brief erratum in a
footnote only when readers need to reconcile an important source discrepancy.
Unresolved ambiguities affecting a formula, code behavior or learning conclusion
may go in the lecture's uncertainty list, naming the affected claim and location.
Routine parser limitations, absent recordings and corrected transcription noise
belong in workspace review records or the completion report; do not repeat them
throughout the note or list them as unresolved knowledge issues.

Give each concept one main explanation in the outline. Later chapters may reuse
it in a new application or link to it; avoid repeating its full definition,
warnings and examples. Within a section, merge sentences that merely paraphrase
one another. Cut generic wrap-ups such as `需要一起权衡` unless they name a concrete
trade-off. Use consistent technical terms instead of vague substitutes such as
`组织方式`, `参与者` or `作用环节` when the actual component is known.
If an assigned source unit also contains another topic, read it but explain only
what serves this chapter; preserve that topic in its own planned chapter instead
of forcing a connection. Instructor emphasis can preserve the point to study
without repeating an unsupported universal numerical promise as a headline.
Split paragraphs that mix several instruction semantics or algorithm phases into
parallel rules or ordered steps. Keep the assumptions beside the rule they govern.

Add background only to bridge a prerequisite or explain the current mechanism.
Mark it once as `**补充解释**：…`; do not insert a chain of labeled digressions,
advanced exceptions or speculative calculations. A toy example must state its
assumptions and help solve the current problem. Introduce an English term at its
first useful occurrence rather than repeatedly expanding it. Use tables for
real parallel comparisons, not to spread a short list into vague cells.

Q&A should exercise prediction, calculation, diagnosis or a consequential
distinction. Keep answers short, with the decisive reasoning. Do not fill the
quota with questions whose answers just repeat the preceding definition. The
question should usually give a concrete situation to work through rather than
ask `能否直接推出……` again. A genuine misconception question remains useful when
its answer teaches a necessary distinction. The introduction maps the learning
problem; the synthesis connects key relationships
or decisions instead of repeating the introduction or every chapter summary.

### Shared English writing brief

Include this brief verbatim in each chapter writer and editor request, alongside
the source paths, outline and response contract. These rules also apply to
introductions, synthesis, captions and Q&A. Hash the updated skill/reference in
request identity; do not reuse old writing/revision responses under unchanged
role-only prompts after a guidance update.

> Write Chinese study notes with knowledge, not the class or evidence review, as
> the subject. Lead with the definition, result or rule and its necessary scope,
> then explain how it works or apply it. Use plain, precise language; give simple
> points briefly and spend detail on mechanisms, worked examples and derivations.
> Preserve prerequisites, symbols, units, code semantics and intermediate reasoning.
> State experiment limits in one short qualification only when they affect the
> conclusion; keep routine provenance, transcription corrections and speculative
> rebuttals out of the prose. Preserve citations and justified instructor emphasis.
> Do not invent facts, generalize a local result, or silently settle real conflicts.
> Give concepts one main explanation; remove repeated paraphrases and generic
> wrap-ups. Split mixed rules into parallel items and algorithms into ordered steps.
> Keep each chapter focused even if a source unit contains unrelated topics.
> Add only background needed for the current topic, label it once, and
> use consistent terms. Prefer concrete tasks in Q&A over repeated questions about
> whether a broad inference is valid; give concise answers. Write bold labels as
> `**补充解释**：正文` or `**补充解释：** 正文`, never
> `**补充解释：**正文`; apply this boundary rule to all punctuation-ending bold
> labels. Keep Markdown/code/math intact. The editor applies these corrections
> directly during the existing single revision without adding a review stage.

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
Each chapter ends with 1–3 useful Q&A, usually 1–2; make them test application or
reasoning and avoid repeating the explanation in answers. Do not mechanically
fill a fixed checklist or expand into a transcript.

Normalize Markdown string line endings to `\n` before assembly on either platform;
preserve spacing inside code and tables. For bold labels, keep the colon outside
the emphasis (`**补充解释**：正文`), or put a space after the closing delimiter
(`**补充解释：** 正文`). The form `**补充解释：**正文` can fail to close emphasis
under Markdown delimiter rules. Apply this to `课堂强调`, `勘误`, `阅读提示` and
other labels as well. In the single revision, inspect emphasis boundaries, heading
levels, list/table spacing, math delimiters and fenced code without altering literal
code examples. The coordinator attaches draft source
footnotes using actual `name-location` (filename, ASCII hyphen, source location;
no surrounding spaces, for example `L01.pdf-PDF p.4`)
values from `materials.json`; retain exact unit IDs in artifacts. Add a short
`本讲小结` and only specific unresolved `不确定事项` when necessary. Incomplete
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
<python> <skill>/scripts/local.py export --root <root> --course os --vault "<vault-root>" --course-name "operating-systems"
```

After applying the editor, write `final/document.json`:

```json
{"schema_version":1,"title":"讲次标题","introduction":"导读","synthesis":"本讲小结","sections":[{"id":"section-1","title":"板块标题","markdown":"### 核心概念\n\n正文","source_ids":["s1p1"]}],"uncertainties":[]}
```

Section order is the final reading order. IDs are unique and stable. Return raw
chapter bodies without coordinator-added footnote definitions; the publisher
attaches exact source locations. Keep nearby `[^unit-id]` reference markers on
important numerical results, formulas and source corrections, using real unit IDs
included in that section's `source_ids`. The chapter source footer remains; nearby
markers improve traceability without inserting provenance prose. Include editorial
additions as complete final sections.
Repeat `--asset` for referenced images. Reference them as `assets/diagram.png` in
section bodies; publication rewrites them to `../assets/diagram.png` for chapter
files. The structured publisher creates the output tree above, with relative links,
parent-index backlinks and previous/next section links. The publisher derives
neighbors from the final `sections` list, including editorial additions; section
IDs or filesystem sort order must not determine reading order. Writers return
content only: the publisher owns navigation so links cannot be stale or duplicated.
Hash receipts preserve manual changes in notes, assets
and indexes; conflicting output stays in a candidate folder. Compare it without
overwriting the user's file. Export copies existing complete notes and referenced
images to the requested Obsidian course folder without regenerating content.
Inspect the JSON result and process exit code; conflicts are preserved, not success.
Open the notebook root (the folder containing `.obsidian/`) as the vault and
start at `<course-folder>/output/index.md`. Publishing inside that vault already
completes the requested layout; no export is needed. Optional export from a separate
course workspace creates `<vault>/<course-name>/output/index.md` and
`output/LXX/{index.md,chapters/,...}`, with empty `input/` and `workspace/` siblings
if absent. It copies only published notes/referenced images, preserves existing
inputs/intermediates and manual edits, and never copies source material, caches or
`.obsidian` configuration. Relative links retain the same depth after export.
No notebook-wide index is required or generated. Earlier runs keep their legacy
export behavior. Do not use legacy export for new course-root runs.
The legacy `--note` option supports earlier single-file publications only; new
skill runs must use `--document`.

## Published Markdown contract

All notes and indexes begin with YAML properties. Use `schema_version: 1`, `type`,
`title`; course-level files also have `course`, lecture-level files have `lecture`,
and chapter files have `section`. New layout types are `course-index`,
`lecture-index` and `course-note`. Properties use quoted human-readable titles and
stable IDs. Do not insert private absolute paths, prompts, cache identifiers or
execution logs into the published note.

Each chapter contains its title, top and bottom navigation, the conceptual explanation
with formulas/examples/comparisons, verified diagrams beside matching prose,
1–3 Q&A and a source-location footer. The lecture index contains its title,
parent-index link, learning thread, ordered chapter links, synthesis and only
material unresolved questions. The course's `output/index.md` contains ordered
lecture links directly, e.g. `[L02 进程与线程](L02/index.md)`. Standard Markdown links, LaTeX and footnotes work in Obsidian without
plugins; avoid custom code blocks for internal status data.

Chapter navigation retains lecture/course directory links and adds
`[上一节：NN Topic](previous-id.md)` and `[下一节：NN Topic](next-id.md)` at both
the top (below H1) and the bottom (after the source footer). Use sibling-relative
Markdown links and final display titles. Omit the previous link on the first
section and the next link on the last; a single-section lecture has only directory
links. Do not wrap around or cross into another lecture. The same links must remain
valid after export to Obsidian. In the new layout, chapter directory links are
`[本讲目录](../index.md)` and `[课程目录](../../index.md)`; lecture indexes link to
`[课程目录](../index.md)`. Do not generate an `全部课程` link to a nonexistent parent
index. Notebook-wide navigation is outside this course publisher's scope.
