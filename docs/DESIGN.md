# Design: a Codex-native lecture workflow

The repository packages one self-contained skill in `skills/class-skipper`.
The current Codex session coordinates full-material reading and planning, chapter
writing, optional selective visual reading, and one editorial revision. Native
subagents handle independent chapters, visual candidates and the single editorial
pass when available. Without delegation tools the same workflow runs sequentially.

## Local helpers

`scripts/materials.py` reads complete PDF, PPTX, DOCX, TXT and Markdown sources,
including tables, speaker notes and final source segments. It preserves source
hashes, roles, unit IDs and page/body locations. `scripts/storage.py` provides
portable identifiers, managed paths, atomic writes and JSON helpers.
`scripts/local.py` prepares runs, caches completed Codex responses, renders and
crops PDF pages, publishes final notes, and exports a library into Obsidian.
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

Codex inspects selected PDF pages and actual crops before placing useful mechanism
figures beside their explanations. Only referenced figures enter the output.
Receipts compare expected file hashes before publication/export; edited files are
preserved and complete replacements remain in workspace candidates. Structured
export retains the complete navigation hierarchy. Earlier single-file notes can
still be published/exported locally through the helper's compatibility option.

## Portability and validation

Python 3.11+, pathlib, UTF-8, atomic writes and directory locks support Windows and
macOS without a Unix launcher or Unix-only lock module. Tests use labeled response
doubles and real small parser fixtures. Actual Codex exercises are recorded
separately in [CODEX_SKILL_REPORT.md](CODEX_SKILL_REPORT.md); macOS execution and
human acceptance have not been established.
