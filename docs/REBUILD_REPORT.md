# Workspace and mechanism-figure verification

Date: 2026-09-18. Human acceptance: pending.

## Delivered changes

- `output` contains only final Markdown notes, their referenced PNG assets and
  the course index. Extracted sources, plans, chapter drafts, visual evidence,
  editorial changes, request usage, receipts and backups live in `workspace`.
- Migrated existing intermediates and prior validation output without deleting
  them. Expected publication hashes were preserved rather than treating modified
  user notes as generated. Manual edits still cause a workspace candidate and
  exit code 5, leaving the existing notes intact.
- Optional remote **kimi-k3** inspects PDF pages, selects process/mechanism regions,
  renders padded crops and checks the actual crops separately. Photos, text-only
  slides and unhelpful charts are excluded. Truncated labels/addresses cause a
  crop to be omitted; other candidates can fill the remaining slots.
- Locator explanations are not sent to the crop verifier. Verification uses high
  reasoning effort to reduce anchoring and arrow-endpoint mistakes. Network calls
  run concurrently; native PDF rendering stays sequential for thread safety.
- Writers insert application-owned figure markers next to the matching
  explanation. The editor may omit irrelevant figures. Only referenced accepted
  crops are copied into output; no whole-page fallback or orphan assets remain.
- The complete-material plan → chapter writing → single revision workflow remains.
  No quality-score publication gate was added. `--no-vision` provides text-only
  generation; unchanged successful responses are reused automatically.
- A separate 15-second connection timeout avoids waiting the full generation
  timeout to establish a connection. Actual model response latency still varies.

## Actual remote execution

The user-authorized L02–L04 PDF/DOCX text was sent to DeepSeek `deepseek-flash`,
and PDF page/crop images were sent to Moonshot `kimi-k3`. These were real calls,
separate from mocked unit tests. Keys were used only for authentication.

The final batch completed with exit 0 after a resumable connection failure.
The preceding pass had two connection timeouts for one L04 chapter; the resume
reused all completed work, filled that chapter, and completed editorial revision.
The original failure record is retained in `workspace/acceptance-first-pass.json`.

This was an **incremental acceptance run**: completed lectures, visual recognition
and planning were reused. Only the missing L04 chapter and its final revision
required new requests. It is not a fully cold latency benchmark.

| Lecture | Source units | Source characters | Chapters | Published figures | Seconds | New API attempts | Revision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| l02 | 37 | 101,765 | 6 | 3 | 0.29 | 0 | completed |
| l03 | 40 | 103,894 | 8 | 3 | 0.27 | 0 | completed |
| l04 | 45 | 116,929 | 8 | 3 | 44.31 | 2 | completed |

A subsequent unchanged batch also exited 0 and made **0 new API calls**.
Per-lecture elapsed time was **0.3 / 0.27 / 0.42 seconds**. Timings are observed local
runs, not guarantees. The earlier L04 fresh visual run took 335.17 seconds. During
iteration, one connection attempt waited about 301 seconds before its successful
10-second retry, motivating the new connection timeout. A later text response took
234.8 seconds and lacked source IDs; the bounded structural retry completed in
17.23 seconds. Remote provider response time remains a practical limitation.

## Inspection and checks

- Inspected actual mechanism crops across all three lectures. Examples include
  system-call mode switching, Base/Bound translation, interrupt-controller flow,
  the complete I/O request lifecycle and request/response communication.
- A truncated L03 context-switch crop was rejected in real Kimi verification and
  replaced by the complete interrupt-controller diagram. Low-effort early readings
  that confused colored memory regions motivated the independent high-effort check.
- Corrected the distinction between `mode bit` and `sysmode` numeric encodings;
  reinforced protection-direction translation (the OS is protected FROM user
  processes, not BY them). Checked the final L02 wording.
- All **9 published image references** resolve locally; no unused image
  assets, intermediate JSON files, unresolved placement markers or incomplete
  chapter placeholders remain in output. All source footnotes resolve, every
  major chapter has Q&A, and published file hashes match workspace receipts.
- `pytest -q`: **18 passed**. Ruff checks and formatting checks passed. Doctor
  found no missing runtime dependencies and made no API requests.
- Tests cover orchestration, full-input retention, manual-edit preservation,
  clean output/backups, workspace separation, exact-response caching, JSON retries
  (including Kimi reasoning preservation), native PDF/DOCX parsing, crop geometry,
  rejected-image omission, inline placement and source-safe formatting. Model
  doubles in these tests are explicitly labeled; they do not prove visual quality.

## Remaining limits

Model interpretation and academic completeness are not guaranteed by these checks.
The checks are agent inspection, not independent human acceptance. Vision was tested
on these three lectures, not arbitrary courses. Image-only lectures need OCR or a
transcript for full-material planning. PPTX figures require PDF export. File locking
currently targets macOS/Linux. First-time remote vision costs additional calls and
time; `--no-vision` skips it. No dollar-cost estimate was made.

Read `output/os/index.md` for the regenerated library. Machine-readable evidence is
in `workspace/acceptance-batch.json`, `workspace/warm-batch.json`,
`workspace/verification.json` and per-run directories. The earlier text-only rebuild
record is retained as `docs/BASELINE_TEXT_REPORT.md` and is historical.

## Obsidian publication and bilingual documentation

The user selected the existing vault at
`/Users/miniyuan/__miniyuan__/class-notes/miniyuan`. Published 3 final lecture
notes and 9 referenced images under its `operating-system` folder, with a course index.
Relative note/image links were checked against actual files. Repeating the real
export left all 13 file timestamps unchanged. An actual cached batch completed
with automatic vault publication and zero new model requests; its record is
`workspace/obsidian-batch.json`. Obsidian UI rendering was not independently tested.

`obsidian_vault` enables automatic publication after successful generation;
`export` publishes existing notes without model calls. Export hashes, locks and
conflict candidates stay in workspace. Changed vault notes/images are preserved,
including modified images that would otherwise become obsolete. Unrelated files
and `.obsidian` settings are outside the publication scope.

Rewrote README.md and README_ZH.md with matching installation, generation, batch,
Obsidian, configuration, recovery and limitation sections. The explicit user
request for a Chinese README takes precedence over the earlier English-only
project documentation guideline, which has been updated accordingly.

Final local checks: **25 tests passed**; Ruff checks and formatting passed. New
local tests cover links/assets, idempotence, manual-edit candidates, missing
assets/path rejection, CLI export without model credentials, automatic export,
and safe removal of obsolete generated images. These tests use temporary vaults;
the real publication and link checks above used the requested vault.
