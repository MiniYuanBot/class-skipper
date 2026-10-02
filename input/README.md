# Local course inputs

Place user-supplied PDF, PPTX, DOCX, TXT and Markdown sources here. Inputs remain
private and ignored by Git; never place drafts or generated notes in this folder.
Organize multiple courses as `<course>/<lecture>/slides.pdf` and
`<course>/<lecture>/transcript.docx`, or use a manifest to make grouping explicit.
Preserve all sources when a lecture has multiple slide decks or transcripts.

`course.yaml` defines the supplied L02–L04 lecture order. All paths in a manifest
resolve relative to that manifest, including paths into course/lecture subfolders.
The Codex skill reads all listed files and identifies any unassigned input files
before proceeding. Intermediates go to `workspace/`; final Obsidian chapter notes
and hierarchical `index.md` navigation go to `output/`.
