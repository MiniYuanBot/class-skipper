# class-skipper

[中文说明](README_ZH.md)

## Codex skill (Windows and macOS)

The portable [class-skipper skill](skills/class-skipper/SKILL.md) uses the current
Codex session for full reading/planning, chapter writing, optional selective visual
reading, and one editorial revision. It delegates independent chapters, visual
candidates and the single revision to available Codex subagents. Local Python
helpers handle parsing, response caching and protected publication. No provider
API key, `.env` or HTTP model client is used.
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
commands and artifact contracts.

## Skill input, intermediate and output layout

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

## Development and evidence

Tests use the Python standard-library unittest runner. Install local parser and
check dependencies, then run from this directory (use `python3` on macOS):

```text
python -m pip install pypdfium2 python-docx python-pptx Pillow ruff PyYAML
python -m unittest discover -s tests -v
python -m ruff check skills tools tests
python -m ruff format --check skills tools tests
```

The local fixture tests cover parsing, caching, protected publication and export;
they do not call a model. Separate real Codex exercise evidence and platform limits
are recorded in [CODEX_SKILL_REPORT.md](docs/CODEX_SKILL_REPORT.md). The current
architecture is described in [DESIGN.md](docs/DESIGN.md).
