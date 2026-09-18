> Historical text-only baseline. Superseded by REBUILD_REPORT.md.

# Rebuild and verification report

Date: 2026-09-18. Human acceptance: pending.

## Delivered architecture

The original project, including Git history, uncommitted work, source materials,
credentials and outputs, was moved to `../class-skipper-old`. Its editable runtime
entry was reinstalled for the relocated path; archived source code was retained.
The new project has an independent virtual environment and no imports from the
old package. Private inputs and credentials were copied locally and are ignored.

The new agent implements the user's chosen flow: one complete-source planning
call, one writing call per major section (three concurrent by default), and one
whole-lecture editorial call that returns corrected content. Optional selective
vision precedes writing; sparse scans can be read before planning. No separate
concept-inventory, transcript-alignment, claim-classification, scoring or
approval stages are on the generation path.

## Actual API execution

All real remote tests used the user-authorized L02-L04 PDF/DOCX **text** and the
configured DeepSeek `deepseek-flash` model at `https://api.deepseek.com`. No page
images were sent remotely. Prices were not configured; dollar cost is unknown.

The first real iteration exposed a chapter that repeated the whole lecture and
one L03 chapter with invalid output structure. The writer now gets a compact
lecture map and an explicit requested-section scope. One bounded structural retry
receives the actual malformed answer and exact error. The editorial instruction
requires correcting fixable scope/repetition defects instead of only reporting
that they exist. These are refinements within the chosen four-step workflow.

The final three-lecture batch completed with exit 0. It reused the unchanged
planning responses; chapter writing and editorial revision were real new calls:

| Lecture | Major sections | Seconds | New API attempts | Editorial revision |
| --- | ---: | ---: | ---: | --- |
| l02 | 7 | 101.42 | 9 | completed |
| l03 | 8 | 114.03 | 10 | completed |
| l04 | 8 | 64.89 | 10 | completed |

A separate **fully uncached** single-lecture acceptance run used:

```bash
./class-skipper generate validation l02 --slides input/L02.pdf \
  --transcript input/L02.docx --title "操作系统 · 四个基本概念" --refresh
```

It finished in **101.72 seconds**, using **8 real calls**
(one plan, six chapter writes, one revision), with no failed attempts. It read all
37 source units / 101,765 extracted characters. Reported token usage:
120,552 input + 28,549 output = 149,101 total.
This is one observed local run, not a latency guarantee or a multi-course benchmark.

## Resume and command acceptance

```bash
./class-skipper batch os --manifest input/course.yaml --resume
./class-skipper generate os l02 --slides input/L02.pdf \
  --transcript input/L02.docx --title "Four fundamental concepts of OS" --resume
./class-skipper doctor
```

Both generation commands exited 0. The three-lecture resume made **zero new API
calls**, with measured per-lecture times 0.14 / 0.09 / 0.11 seconds. Single-lecture
resume made zero new calls and took 0.15 seconds. Doctor found no missing runtime
dependencies and made no API call. Timings include native parsing and image export.

## Output inspection

- `output/os/index.md` links all three existing notes in manifest order.
- The three notes contain 7 / 8 / 8 major sections and 36 / 36 / 43 H3 headings
  (including Q&A headings), with three local page illustrations each.
- All nine image paths exist; representative real PDF imagery was visually inspected.
  These are full physical PDF pages (the supplied PDF uses four slides per page),
  not automatically identified figure crops.
- Every section source footnote resolves; each document has one H1; no template
  placeholders or unclosed code/display-math blocks were found. Table delimiters
  and display-math layout are normalized without rewriting code or formulas.
- L02's mis-scoped Base-and-Bound chapter was replaced with the assigned topic.
  Spot inspection included definitions/protection, thread switching, address
  translation, fork return values, successful exec non-return, file interfaces
  and the final networking material. This is an agent spot check, not independent
  human content acceptance or a measured semantic coverage score.
- Remaining academic uncertainties stay visible. Some editorial caveats still
  mention details deferred by the lecture; they do not prevent note production.

## Automated checks and limitations

**Executed checks:** `python -m pytest -q` reported 12 passed (1.18 s);
`ruff check src tests` and `ruff format --check src tests` passed.

Tests exercise full-source final-tail retention, plan/write/revise orchestration,
editor failure preserving a draft, explicit incomplete-section output, batch
continuation, manual-edit protection, cache invalidation, precise JSON repair,
no remote calls without permission, safe paths and markup, real PDF/DOCX extraction,
real page rendering, and the optional vision path with an explicit model double.
Real Moonshot/Kimi visual understanding was **not** tested; no image-send permission
was inferred from text-only test authorization. Other course domains, scanned
lectures and other operating systems have not received equivalent real evaluation.
File locking currently targets macOS/Linux (fcntl); Windows is not supported yet.

The new project was tested on Apple Silicon macOS with Python 3.12.14. Exact
installed versions are in `requirements-tested.txt`. No heavy Docling model
weights, vector database, web service or separate orchestration framework is used.

Read `output/validation/l02/notes.md` for the independent cold-start example, or
`output/os/index.md` for the complete three-lecture library. Compare against the
originals and add your own annotations separately; human acceptance remains pending.
