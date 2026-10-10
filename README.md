# class-skipper

[中文说明](README_ZH.md)

A portable agent skill that turns lecture slides (PDF/PPTX) and optional
transcripts (DOCX/TXT/MD), in Chinese or English, into Chinese Obsidian study
notes. It works in **Codex** and **Claude Code**, on **Windows** and **macOS**.

The skill runs four steps in the current agent session, delegating independent
work to native subagents when available:

1. **Read and plan**: read every extracted unit, view labeled slide contact sheets
   to catch diagrams and scanned pages, and plan 4–8 chapters with figure
   candidates and concept ownership. When a transcript exists it defines the
   lecture's scope: slides carried over from the previous deck are included,
   untaught slides move to the lecture that teaches them, and slides the
   instructor leaves as extension are still written, labeled 拓展.
   With the optional `thought_questions` switch, instructor thought questions are
   written beside their concepts with a hint and a folded solution, exam hints
   are marked only when the transcript states them, and `output/questions.md`
   collects them for the whole course.
2. **Write chapters**: writers follow a fixed template: key-point summary,
   motivation → definition → mechanism → example → pitfalls, Mermaid diagrams for
   source-described processes, labeled supplement callouts, and hidden-answer
   self-tests.
3. **Add visuals**: crop and verify slide figures, and (with web access) add
   verified links to external visualizations or interactive demos.
4. **Revise once**: one editor fixes coverage, accuracy, repetition and format;
   a mechanical `check` lists Markdown problems to fix in the same pass.

Local Python helpers only parse documents, render pages, cache responses and
publish files. No API key, `.env`, model SDK or external OCR is used; the host's
normal sign-in and usage limits apply.

## Install

Python 3.11+ is required. From this repository:

```powershell
# Windows (PowerShell)
py -3 tools/install_skill.py
```

```bash
# macOS
python3 tools/install_skill.py
```

By default the installer links `skills/class-skipper` into both hosts, so edits
in this repository apply without reinstalling (macOS/Linux: symlink; Windows: junction):

| Host | Default location |
| --- | --- |
| Codex | `$CODEX_HOME/skills/class-skipper`, else `~/.agents/skills/class-skipper` |
| Claude Code | `$CLAUDE_CONFIG_DIR/skills/class-skipper`, else `~/.claude/skills/class-skipper` |

Use `--host codex` or `--host claude` for one host, or `--destination` for an
exact folder (for example a project's `.claude/skills/class-skipper`). A differing
existing folder or link to another location is preserved; `--update` renames it to
`class-skipper.backup*` and links the new version. Copying the folder by hand also works.

## Use

Start the agent in your notebook (Obsidian vault) root or a course folder, then:

```text
# Codex
Use $class-skipper to make notes for every lecture in computer-organization-and-architecture/input.

# Claude Code
/class-skipper make notes for every lecture in computer-organization-and-architecture/input
```

Claude Code also loads the skill automatically when you ask for lecture notes.
The skill checks Python with `scripts/local.py doctor` and installs only missing
parser packages (`pypdfium2`, `Pillow`, `python-docx`, `python-pptx`) into
`<course>/workspace/.venv`.

## Course manifest

Put a course's sources in `<course-folder>/input/`, for example `L02/slides.pdf`
and `L02/transcript.docx`. An optional `input/course.yaml` makes lecture pairing,
order and run options explicit; copy
[`course.example.yaml`](skills/class-skipper/references/course.example.yaml) and
edit it. Paths are relative to the manifest. Without a manifest the skill pairs
files by name and asks when that is ambiguous.

```yaml
schema_version: '1'
title: 操作系统
options:
  thought_questions: true                  # default false
  thought_question_terms: [思考题, Think]   # optional
lectures:
- id: l02
  title: 操作系统的四个基本概念
  slides: [L02/slides.pdf]
  transcripts: [L02/transcript.docx]
```

| Field | Meaning |
| --- | --- |
| `title` | Course name shown in `output/index.md` |
| `lectures[].id` | Lecture number; `l2`, `02` and `L02` all become `L02` |
| `lectures[].title` | Lecture topic; the note title becomes `L02 Topic` |
| `lectures[].slides`, `transcripts` | Every file for that lecture; several are allowed |
| `options` | Run options for every lecture; `lectures[].options` overrides them per lecture |
| `options.thought_questions` | Write instructor thought questions with hints, folded solutions and summaries |
| `options.thought_question_terms` | What this instructor calls them, for more precise matching |

List only each lecture's own deck. When a transcript finishes the previous deck
or starts the next one, the skill reads the adjacent decks itself, so the
transcript decides what each lecture's notes cover. Changing options starts a
new run for that lecture; manually edited notes are still preserved.

## Layout

The notebook root keeps `.obsidian/`; each course folder has its own `input/`,
`workspace/` and `output/`. Helper `--root` is the course folder.

```text
<notebook-root>/                         Obsidian vault root
  .obsidian/                             Untouched
  computer-organization-and-architecture/   Course root (--root)
    input/course.yaml                    Optional manifest (lecture pairing/order)
    input/L02.pdf, input/L02.docx        Slides and transcripts
    workspace/L02/<run-id>/              Materials, plan, requests, chapters,
                                         sheets/crops, draft, revision, cache
    output/index.md                      Course directory
    output/L02/index.md                  Chapter links with summaries, synthesis
    output/L02/chapters/01-performance-metrics.md  One note per chapter (English file name)
    output/L02/assets/l02-isa-formats.png Referenced figures only
```

File and folder names are English; note content is Chinese. Each chapter note
has YAML properties (with its Chinese title as an alias for link completion),
previous/next and directory navigation at top and bottom, a key-point callout,
concept sections with formulas, examples, figures and Mermaid diagrams,
collapsed self-tests, footnotes on key results and a collapsed source list with
merged page ranges. Publication preserves manual edits: a conflicting file is
left untouched and the new version is saved as a candidate in workspace.
Earlier runs keep their original paths and `section-N.md` filenames.

Cross-chapter links use relative Markdown paths to the actual English filenames,
with Chinese display text. Writers reference stable chapter IDs; publication
resolves them and reports unknown or ambiguous targets. Math uses LaTeX in
prose, summaries, tables and figure captions. Image alt text stays short and
plain; the complete caption is a paragraph below the image so formulas render.

See [SKILL.md](skills/class-skipper/SKILL.md), the
[workflow contract](skills/class-skipper/references/workflow.md), the
[note style](skills/class-skipper/references/note-style.md) and
[visuals guide](skills/class-skipper/references/visuals.md).

## Development

```text
python -m venv .venv
.venv/bin/python -m pip install pypdfium2 python-docx python-pptx Pillow ruff   # Windows: .venv\Scripts\python
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m ruff check skills tools tests
.venv/bin/python -m ruff format --check skills tools tests
```

Tests use real small PDF/DOCX/PPTX/TXT fixtures and labeled response doubles; they
do not call a model. Real-run evidence is recorded separately in
[CODEX_SKILL_REPORT.md](docs/CODEX_SKILL_REPORT.md); the architecture is in
[DESIGN.md](docs/DESIGN.md).
