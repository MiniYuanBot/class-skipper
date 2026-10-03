# Local course inputs

Place user-supplied PDF, PPTX, DOCX, TXT and Markdown sources here. Inputs remain
private and ignored by Git; never place drafts or generated notes in this folder.
For new skill runs, place each course's inputs under
`<notebook-root>/<course-folder>/input/`, using `LXX/slides.pdf` and
`LXX/transcript.docx` if useful, or a manifest to make grouping explicit.
This repository's existing input fixture remains at its supplied paths; do not
move original files to match the new generated-output layout.
Preserve all sources when a lecture has multiple slide decks or transcripts.

`course.yaml` defines the supplied L02–L04 lecture order. All paths in a manifest
resolve relative to that manifest, including paths into course/lecture subfolders.
The Codex skill reads all listed files and identifies any unassigned input files
before proceeding. Intermediates go to `workspace/`; final Obsidian chapter notes
and hierarchical `index.md` navigation go to `output/`.
