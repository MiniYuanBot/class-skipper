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
Use $class-skipper to read every file in <course-folder>/input/course.yaml, generate Chinese notes
in this workspace with subagents, inspect useful diagrams, and revise once.
```

Supply actual source paths or a course manifest and, optionally, an authorized
Obsidian vault destination. The skill installs only missing local parser packages
when needed. Plain text and Markdown helpers use the Python standard library;
PDF/DOCX/PPTX require `pypdfium2`, `python-docx`, and `python-pptx` respectively.
See [workflow.md](skills/class-skipper/references/workflow.md) for offline helper
commands and artifact contracts.

Notes lead with knowledge and necessary conditions, use plain language, and retain
useful derivations and examples. The shared writer/editor brief removes defensive
source commentary, duplicate explanations and unnecessary background, makes Q&A
test reasoning, and checks Markdown bold-label boundaries in the same revision.

## Skill input, intermediate and output layout

Open the notebook root as the Obsidian vault. Its `.obsidian/` stays there; each
course has its own `input/`, `output/` and `workspace/`. Helper `--root` selects the
course folder, not the vault root. Explicit source paths remain supported without
moving originals. A course manifest defines lecture pairing and reading order.

```text
<notebook-root>/                                      Obsidian vault root
  .obsidian/                                    Existing configuration
  computer-organization-and-architecture/        Course root (--root)
    input/course.yaml                           Optional course manifest
    input/L02/                                  Slides and transcripts
    workspace/L02/<run-id>/                      Materials, plans, requests,
                                                chapters, visuals, draft, revision,
                                                final document and response cache
    workspace/publication/                      Protected publication receipts
    output/index.md                             Ordered lecture directory
    output/L02/index.md                          Chapter directory and synthesis
    output/L02/chapters/section-1.md
    output/L02/chapters/section-2.md
    output/L02/assets/diagram.png                Referenced images only
  operating-systems/                            Another independent course
    input/
    output/
    workspace/
```

There is no repeated course-ID folder inside output/workspace. New lecture IDs
normalize to uppercase `LXX` (`l2` or `02` becomes `L02`). Chapter notes have YAML
properties, concise numbered titles, top/bottom previous/next links, directory
links, knowledge explanations, examples, Q&A and source footnotes.
Only final Markdown and referenced assets enter output. Start at the course's
`output/index.md`; do not open output as a separate vault. Optional export from a
separate workspace uses the same `<vault>/<course-folder>/output/LXX/` hierarchy,
creating empty input/workspace siblings when absent without copying private data
or changing `.obsidian/`. Publishing directly within the vault needs no export.
Old runs/caches and manual notes remain at their existing paths; no automatic
migration occurs. Publication/export preserves manual edits and saves conflicting
candidates under workspace.

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
