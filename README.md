# class-skipper

[中文说明](README_ZH.md)

## Codex skill (Windows and macOS)

The portable [class-skipper skill](skills/class-skipper/SKILL.md) uses the current
Codex session for full reading/planning, chapter writing, optional selective visual
reading, and one editorial revision. It delegates independent chapters, visual
candidates and the single revision to available Codex subagents. Local Python
helpers handle parsing, response caching and protected publication. No provider
API key, `.env`, HTTP model client or legacy generation command is used in this mode.
Codex authentication and usage limits still apply. Without subagent tools, the
same workflow runs sequentially; image reading requires an image-capable host.

Install from this repository with Python 3.11+:

```powershell
# Windows PowerShell
python tools/install_skill.py
```

```bash
# macOS
python3 tools/install_skill.py
```

The installer uses `CODEX_HOME/skills/class-skipper` when `CODEX_HOME` is set,
otherwise `~/.agents/skills/class-skipper`. Use `--destination` with the exact skill
folder for a different host's configured skill location. It preserves a differing
installed skill instead of overwriting it. You can also copy the entire
`skills/class-skipper` folder into a skill directory; it does not depend on this
repository after copying. Local skill discovery is described in the
[official skill documentation](https://learn.chatgpt.com/docs/build-skills).

In Codex, invoke:

```text
Use $class-skipper to read every file in input/course.yaml, generate Chinese notes
in this workspace with subagents, inspect useful diagrams, and revise once.
```

Supply actual source paths or a course manifest and, optionally, an authorized
Obsidian vault destination. The skill installs only missing local parser packages
when needed. Plain text and Markdown helpers use the Python standard library;
PDF/DOCX/PPTX require `pypdfium2`, `python-docx`, and `python-pptx` respectively.
See [workflow.md](skills/class-skipper/references/workflow.md) for offline helper
commands and artifact contracts. The legacy application described below retains
its separate provider configuration and macOS/Linux requirements.

### Skill input, intermediate and output layout

Put lecture files in `input/`, optionally grouped by course and lecture. A manifest
makes slide/transcript pairing and lecture order explicit. The default skill root
is the current project directory. Explicit paths remain supported without moving
original sources. Run data and reasoning JSON artifacts are versioned
(`schema_version: 1`), UTF-8 and stored under `workspace/`; new runs preserve earlier
artifacts and caches.

```text
input/os/l02/                 User slides and transcripts
workspace/os/l02/<run-id>/    materials.json, run.json, status.json, plan.json
  requests/                  Exact reasoning requests
  chapters/                  Completed chapter response JSON
  visuals/pages/, crops/     Rendered pages and selected crops
  visuals/readings.json      Actual visual inspection results
  draft/notes.md             Complete draft for the single editorial pass
  revision/review.json       Editorial response
  final/document.json        Corrected structured lecture
  cache/                    Completed responses and refresh history
output/
  index.md                   Library/course directory
  os/index.md                Course/lecture directory
  os/l02/index.md            Lecture/chapter directory and synthesis
  os/l02/chapters/section-1.md
  os/l02/chapters/section-2.md
  os/l02/assets/diagram.png
```

Each major planned chapter becomes a separate Obsidian note with YAML properties,
a title, parent-index link, concept explanations, formulas, examples, Q&A and
source-location footnotes. Only final Markdown, navigation and referenced assets
are published. Open `output/` as an Obsidian vault and start at `index.md`.
Optional structured export places a self-contained single-course library under
the requested vault course folder, including its root index and course-ID folder,
so relative navigation remains valid. Publication protects edited indexes, chapter
notes and images; conflicting replacements stay in `workspace/`.

### Skill input, intermediate and output layout

Put lecture files in `input/`, optionally grouped by course and lecture. A manifest
makes slide/transcript pairing and lecture order explicit. The default skill root
is the current project directory. Explicit paths remain supported without moving
original sources. All intermediate JSON files are versioned (`schema_version: 1`),
UTF-8 and stored under `workspace/`; new runs preserve earlier artifacts and caches.

```text
input/os/l02/                 User slides and transcripts
workspace/os/l02/<run-id>/    materials.json, run.json, status.json, plan.json
  requests/                  Exact reasoning requests
  chapters/                  Completed chapter response JSON
  visuals/pages/, crops/     Rendered pages and selected crops
  visuals/readings.json      Actual visual inspection results
  draft/notes.md             Complete draft for the single editorial pass
  revision/review.json       Editorial response
  final/document.json        Corrected structured lecture
  cache/                    Completed responses and refresh history
output/
  index.md                   Library/course directory
  os/index.md                Course/lecture directory
  os/l02/index.md            Lecture/chapter directory and synthesis
  os/l02/chapters/section-1.md
  os/l02/chapters/section-2.md
  os/l02/assets/diagram.png
```

Each major planned chapter becomes a separate Obsidian note with YAML properties,
a title, parent-index link, concept explanations, formulas, examples, Q&A and
source-location footnotes. Only final Markdown, navigation and referenced assets
are published. Open `output/` as an Obsidian vault and start at `index.md`.
Optional structured export places a self-contained single-course library under
the requested vault course folder, including its root index and course-ID folder,
so relative navigation remains valid. Publication protects edited indexes, chapter
notes and images; conflicting replacements stay in `workspace/`.

Turn lecture slides and transcripts into structured study notes, then publish them
to a course folder in Obsidian. The workflow stays small:

**Read the complete material → plan the chapters → write each chapter → revise once.**

Optional Kimi vision adds relevant process and mechanism diagrams. It locates
regions, checks the actual crops, and places accepted figures beside the matching
explanation. A quality score never blocks publication; incomplete generation and
unresolved questions remain visible.

## Quick start

Run all commands from this directory. Python 3.11+ on macOS/Linux is required.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
cp .env.example .env
```

Fill `.env` with your own keys and model names. The tested configuration uses:

```dotenv
DEEPSEEK_API_KEY=your_key
CLASS_SKIPPER_TEXT_MODEL=deepseek-flash
CLASS_SKIPPER_REVIEW_MODEL=deepseek-flash
MOONSHOT_API_KEY=your_key
CLASS_SKIPPER_VISION_MODEL=kimi-k3
CLASS_SKIPPER_KIMI_BASE_URL=https://api.moonshot.cn/v1
```

Create `configs/local.yaml`:

```yaml
allow_remote_llm: true
vision: true
output: output
workspace: workspace
obsidian_vault: /absolute/path/to/your/Obsidian-vault
```

`allow_remote_llm` authorizes sending course text to the configured provider;
vision additionally sends PDF page images and crops to Kimi. Set `vision: false`
for text-only generation. Leave `obsidian_vault: ""` to disable automatic export.
Keys, local settings, private inputs, output and workspace are ignored by Git.
The repository launcher uses `.venv` when available.

```bash
./class-skipper doctor
```

Doctor checks text-provider configuration and dependencies without calling an API.

## Generate one lecture

```bash
./class-skipper generate os l02 \
  --slides input/L02.pdf --transcript input/L02.docx \
  --title "操作系统 · 四个基本概念" --course-name "operating-system"
```

`os` is a stable course ID; `l02` is a stable lecture ID. Use letters, digits,
underscores or hyphens for IDs. `--title` names the lecture. `--course-name` names
the Obsidian course folder and can contain Chinese or spaces. Without it, export
uses the course index title; a new single-lecture course initially uses its ID.

Repeat `--slides` or `--transcript` for multiple files. Transcripts are optional.
Supported inputs: PDF, PPTX, DOCX, TXT and Markdown. Supply a PDF export for PPTX
figures; image-only lectures need OCR text or a transcript before planning.

## Generate a course library

Put a manifest alongside the source files, for example `input/course.yaml`:

```yaml
title: operating-system
lectures:
  - id: l02
    title: Four fundamental concepts of OS
    slides: [L02.pdf]
    transcripts: [L02.docx]
  - id: l03
    title: process, syscall and fork
    slides: [L03.pdf]
    transcripts: [L03.docx]
```

```bash
./class-skipper batch os --manifest input/course.yaml --vision
```

Paths in the manifest resolve relative to the manifest. Lectures run in manifest
order; a failed lecture does not prevent later lectures from running. The manifest
`title` supplies the course index title and, by default, the Obsidian folder name.
A successful run automatically exports when `obsidian_vault` is configured.

## Obsidian publishing

Export existing notes without regenerating them or calling any model:

```bash
./class-skipper export os --course-name "operating-system"
```

Override the configured vault for one command:

```bash
./class-skipper export os --vault /absolute/path/to/vault --course-name "operating-system"
```

Point to the actual vault root, normally the folder containing `.obsidian`.
The current local setup publishes to:

```text
/Users/miniyuan/__miniyuan__/class-notes/miniyuan/operating-system/
├── index.md
├── l02.md
├── l03.md
├── l04.md
└── assets/
    ├── l02/
    ├── l03/
    └── l04/
```

The exporter rewrites lecture/image links to relative Markdown paths and copies
only referenced images. Open `operating-system/index.md` in the existing vault. No Obsidian
plugin is required; `.obsidian` settings and unrelated personal notes are untouched.

This is one-way publication, not bidirectional synchronization. Repeated exports
leave identical files unchanged. If a previously exported note or image has been
edited, conflicting files are preserved, the command exits with code 5, and a full
candidate remains in `workspace/obsidian/.../candidates/` for comparison. No
conflicting course files are published in that attempt. Removing an unchanged,
previously generated image that is no longer referenced is part of synchronization.
Automatic export runs only after successful generation; partial notes stay local.

## Files and controls

```text
input/                 Your source files and course manifests
output/<course>/       Final notes, course index and referenced images only
workspace/runs/        Extracted material, plans, drafts, reviews and visual checks
workspace/cache/       Reusable complete model responses
workspace/published/   Expected hashes for local generated files
workspace/backups/     Previous local publications
workspace/obsidian/    Vault export receipts and conflict candidates
workspace/reports/     Batch reports
```

| Option | Purpose |
| --- | --- |
| `--vision` / `--no-vision` | Enable diagram processing / use the faster text-only path |
| `--resume` | Explicitly request the default reuse of matching completed responses |
| `--refresh` | Make new model requests instead of reusing responses |
| `--no-review` | Skip the final editorial revision |
| `--vault`, `--course-name` | Override the destination vault and course folder |
| `--config`, `--env-file`, `--output`, `--workspace` | Global options; place before the command |

Additional settings are listed in `configs/default.yaml` and `src/class_skipper/config.py`.
Defaults include three concurrent chapter/network requests and at most three
accepted figures. Planning reads the complete extracted source; oversized input
fails explicitly without silently truncating it. The writing prompts follow
`references/original`, including concept headings, comparisons, explained formulas
and useful Q&A. First-time vision requires additional remote calls; cached reruns
can be much faster, but network and model latency vary.

Rerun the same command after a transport failure to complete missing work. Local
manual edits are also protected: a replacement stays in the run's `candidate`
folder instead of overwriting the edited lecture. Revision failure retains the
draft with a visible notice; it does not discard completed chapters.

Exit codes: `0` completed; `2` configuration/input/export error; `3` incomplete
lecture or batch failure; `5` manual edits preserved. A batch with a failed lecture
returns `3`; inspect its per-lecture results for the original code.

## Development and evidence

```bash
.venv/bin/python -m pip install pytest ruff
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests tools
.venv/bin/python -m ruff format --check src tests
```

Tests label model doubles explicitly. The real L02–L04 API/crop verification record
is in [REBUILD_REPORT.md](docs/REBUILD_REPORT.md); architecture and neighboring
project references are in [DESIGN.md](docs/DESIGN.md). Generated content still needs
academic judgment; automated checks do not establish complete semantic accuracy.
The original implementation is preserved in the neighboring `class-skipper-old`.
