# Codex skill implementation and evidence

The self-contained `skills/class-skipper` folder keeps full-material reading and
planning, chapter writing, optional selective visual reading, and one editorial
revision. The current Codex session and available native subagents perform all
model work. Its Python helpers do not import a model client, read provider
environment files, invoke a nested Codex CLI, or make model/OCR network calls.
The repository contains only the Codex skill and local helpers. The installer copies only the
skill files and preserves differing installed content. Users place sources in
`input/`; run data, requests, chapter responses, visual records, drafts, revision
responses and caches stay in `workspace/`. Structured publication creates an
Obsidian course notes under `<vault>/<course>/output/`, with course/lecture
`index.md` navigation (older runs retain the earlier library layout),
one Markdown note per chapter, properties, parent links, source footnotes and only
referenced images. Intermediate JSON is never copied into the published library.

## Local validation on Windows

At the original implementation checkpoint, fourteen tests passed: twelve helper tests and two installer tests. They use real small
UTF-8 TXT, PDF, DOCX and PPTX fixtures, including tables, speaker notes and ending
conditions. Checks cover PDF rendering/cropping, source changes, cache invalidation
and refresh history, portable names, standalone installation, and manual note,
index and vault-file preservation. Structured-output regressions verify every
local navigation/image link, versioned intermediate folders, heading promotion
outside code/math, normalized Windows line endings, valid source IDs, ordering,
retired unchanged chapters/assets, and manual edits to root/chapter/vault notes.
Cached test responses are explicitly labeled
model doubles; parser fixtures are real local documents.

The skill-creator frontmatter validator passed. Ruff lint/format and compilation checks
passed for the added Python files. The installed skill also parsed a TXT fixture
from outside its source folder. Binary parser tests ran with the bundled local
Python runtime; no external model API was called.

## Course-root layout regression checks

The current nineteen offline tests additionally cover uppercase LXX normalization,
course-local output/workspace paths, separate course roots under a shared vault,
unchanged `.obsidian` settings, previous/next chapter links in final reading order,
export into a course/output hierarchy, and old-run publication/export compatibility.
New preparation does not mix a course-root layout into an existing legacy library.
These are local helper/fixture checks, not a new model or full-course generation run.

## Real Codex forward exercise

Before the structured-layout update, an isolated synthetic lecture used two TXT
sources, two chapters, a delegated
chapter writer, and one delegated whole-lecture editor. It retained the ending
dynamic-relocation topic and ignored an embedded request for an external API key.
The generated note has actual source names and text-segment locations. Four
completed responses were retrieved, persisted and compared during cache replay
without regenerating them. Republishing after a manual edit returned exit code 5,
preserved the edited bytes, and retained a complete candidate.

The first generation omitted pre-task cache lookups; replay verifies response
reuse but does not establish that the first exercise followed every instruction.
The exercise also exposed mixed Windows line endings and duplicate retained
footnotes during assembly. Its harness corrected these issues; the skill reference
now explains line-ending normalization, footnote preservation, and stable upstream
argument order. Evidence and the note remain under the ignored
`workspace/skill-forward/result/` folder.

This is a small Codex fixture run. No macOS execution, original full-course run, or human
acceptance was performed. Cross-platform support is implemented with pathlib,
UTF-8, atomic files and directory locks rather than a Unix launcher or `fcntl`.
