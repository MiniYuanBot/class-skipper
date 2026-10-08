# Design: a host-native lecture workflow

The repository packages one self-contained skill in `skills/class-skipper`.
The current agent session (Codex or Claude Code) coordinates full-material
reading and planning, chapter writing, visual selection, and one editorial revision. Native
subagents handle independent chapters, visual candidates and the single editorial
pass when available. Without delegation tools the same workflow runs sequentially.

## Local helpers

`scripts/materials.py` reads complete PDF, PPTX, DOCX, TXT and Markdown sources,
including tables, speaker notes and final source segments. It preserves source
hashes, roles, unit IDs and page/body locations. `scripts/storage.py` provides
portable identifiers, managed paths, atomic writes and JSON helpers.
`scripts/local.py` prepares runs, reports the Python environment (`doctor`),
caches completed agent responses, renders and crops PDF pages, renders labeled
contact sheets (`sheet`), lists mechanical format issues (`check`), publishes
final notes, and exports a library into Obsidian.
These helpers perform local operations; they do not provide model inference.

## Artifact boundaries

Users place source material in `input/`. Run identity, complete extracted material,
exact task requests, plans, chapter responses, visual readings, drafts, revision
responses and caches stay under `workspace/`. Matching completed responses are
reused; refresh preserves prior responses. Sources are untrusted data and cannot
authorize changes to the workflow or tool execution.

The coordinator supplies chapter workers with the full plan and their complete
raw source units. The one editor reads the full draft and all original material.
There are no claim graphs, independent alignment stages, scores or repair loops.
Essential unread material prevents a lecture from being represented as complete.

## Notes and figures

The notebook root holds `.obsidian/` and sibling course folders. Each course
folder is a helper root containing input/output/workspace. Its `output/index.md`
links directly to `LXX/index.md`, which links to independent `LXX/chapters/` notes.
New runs live under workspace/LXX/run-id with a course-root layout marker; old
runs retain their original paths and compatibility behavior. Optional export
keeps output/LXX beneath the destination course folder and does not touch vault
configuration. Notes carry Obsidian properties,
relative navigation, source-location footnotes, concept explanations, meaningful
examples and Q&A. Chapter headings are promoted outside code/math when splitting
the assembled lecture. The active file and formatting contract is in
[workflow.md](../skills/class-skipper/references/workflow.md).

Writers link by stable section ID. Publication first assigns every chapter's
final filename, then resolves references to relative Markdown links; Chinese
titles remain display text and completion aliases. Full-title references from
older drafts are accepted only when unique. Shared Markdown parsing protects
code and math, preserves nested brackets in image descriptions, and supports
reference diagnostics in the existing `check` command. Publication verifies
reference integrity before writing files.

Chapters follow the template in `references/note-style.md`. During full reading
the agent views contact sheets of every PDF page, records figure candidates in
the plan, and writers leave placeholders where those figures belong. The agent
views each actual crop before replacing a placeholder; writers may add Mermaid
diagrams for processes stated in the source, and verified external visual links
go beside the matching concept. Only referenced local figures enter the output.
Image alt text is short and plain; complete captions are separate paragraphs
that can render LaTeX and are retained in visual readings. Writers and the single
editor use source-grounded mathematical symbols and LaTeX throughout prose,
summaries, tables and captions. Helpers report mechanical notation problems;
they do not infer meanings or rewrite code and instruction fields as variables.
Receipts compare expected file hashes before publication/export; edited files are
preserved and complete replacements remain in workspace candidates. Structured
export retains the complete navigation hierarchy. Earlier single-file notes can
still be published/exported locally through the helper's compatibility option.

## Portability and validation

Python 3.11+, pathlib, UTF-8, atomic writes and directory locks support Windows and
macOS without a Unix launcher or Unix-only lock module. Chapter file names are
English ASCII slugs, so they are portable and easy to type on both systems. SKILL.md maps each
step to Codex and Claude Code tools, and the installer targets both hosts. Tests use labeled response
doubles and real small parser fixtures. Actual Codex exercises are recorded
separately in [CODEX_SKILL_REPORT.md](CODEX_SKILL_REPORT.md); offline helper tests
do not establish a real host/course run or human acceptance.
