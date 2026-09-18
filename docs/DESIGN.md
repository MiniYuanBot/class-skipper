# Design: keep the teaching workflow visible

The user chose four operations: read all material, understand and plan the note
framework, fill sections, review and revise. The implementation follows that
sequence directly in `engine.py`. Model calls return small JSON envelopes around
Markdown chapters, not individually classified claims and evidence-ID graphs.

## Local references inspected

- `../SlideNote/slidenote/notes/direct.py`: generate by coherent context, bounded
  repair, response caching and configurable concurrency. Adapted at chapter level.
- `../SlideNote/slidenote/notes/lecture_weave.py`: separate source understanding
  from lecture-level organization. This implementation uses one full-source plan
  and one full-source revision rather than a page-note intermediate for every page.
- `../SlideNote/slidenote/notes/quality.py`: explanation, examples, coherence and
  figure integration differ from source coverage. Keyword scores are not truth
  checks, so this agent asks an editor to make concrete corrections, not grant a
  publication score.
- `../marker/marker/renderers/markdown.py`: keep rendered text and image assets
  distinct. Figures use application-owned relative paths, never model URLs.
- `../docling/docs/examples/export_figures.py`: referenced source images remain
  separate reusable files; distinguish full-page illustrations from figure crops.

No code was copied from these projects. Their design ideas informed a much smaller
implementation using native PDF/Office extraction and the existing authorized API.

## Deliberate boundaries

- Source IDs identify readable pages or transcript segments, not individual claims.
  References are checked against real sources; this does not prove entailment.
- The whole lecture is read before planning. Chapter calls see their relevant
  original passages and a compact lecture map, avoiding repeated whole-lecture
  generation inside each chapter. The final editor sees all original passages.
- Model plans and complete responses are cached. There is no separate model call
  to approve each intermediary artifact.
- Editorial uncertainty is reported, not used as a score gate. Transport failure,
  missing chapter output and unsafe overwrite are different conditions.
- Optional vision considers all PDF pages but publishes only verified mechanism
  crops. Text-only runs do not automatically publish source illustrations.
- The original guide's conflicting H1 instructions are resolved as one standalone
  document title, with body hierarchy starting at H2. Unhelpful template padding,
  fabricated analogies and invented physical meanings are avoided.


## Mechanism figures and clean publication (2026-09-18)

SlideNote's `slidenote/figures.py` informed region-first extraction: normalize
boxes, reject text-only regions, preserve surrounding labels and record rejected
candidates. The figure-extractor skill similarly recommends rendering complete
vector/text regions rather than extracting embedded raster fragments. This
implementation uses existing PDFium rendering (no new extraction dependency),
Kimi K3 remote localization, 2.5% page-space padding around proposed regions,
and a second visual check of the actual crop. Truncated mechanism labels or
addresses reject the crop; the next suitable candidate is considered. PDF rendering
is sequential because PDFium is not thread safe; network requests run concurrently.
Only accepted mechanism diagrams are offered to the writer, using application-owned
placement markers next to the explanation. Final rendering resolves known markers;
unrecognized markers and unreferenced assets do not become published figures.

Kimi K3 uses `reasoning_effort: low` for page localization and `high` for crop
verification, with its always-on reasoning. The verifier sees only the actual
crop, not the locator's explanation, to reduce anchoring on a mistaken reading. Structural retry
preserves the full assistant message, including reasoning content. See the
[official K3 guide](https://platform.kimi.ai/docs/guide/kimi-k3-quickstart).

`workspace/runs` stores each run, `workspace/cache` stores response reuse,
`workspace/published` stores expected final-file hashes, `workspace/backups`
preserves prior publications, and `workspace/reports` stores course run reports.
`output` only holds notes, referenced assets and indexes. The one-time migration
script in `tools/migrate_workspace.py` preserves expected hashes rather than
reclassifying modified notes as generated.

Network connection establishment has a separate 15-second timeout; the configurable
response timeout remains available for actual generation. This follows an observed
300-second connection timeout whose successful retry generated a chapter in 10 seconds.
After successful editorial revision, only the editor's remaining uncertainties are
published, so resolved chapter-level concerns do not reappear as stale warnings.
