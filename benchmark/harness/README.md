# Benchmark grading harness

Automated, uniform grading for the neuroimaging benchmark. An open-weight model runs a task
prompt unattended (it picks its own tools), produces the required output files, and this harness scores
it against a frozen reference — producing a numeric, rankable result.

## The two planes

The model *doing* a task needs a full neuroimaging stack (tools, a scheduler, often a GPU); the
grader is pure `numpy`/`nibabel`/`scipy`. So the pipeline splits, and the split is also the
anti-leak boundary:

```
 EXECUTION PLANE  (self-hosted runner)                GRADING PLANE  (any github-hosted runner)
 ─────────────────────────────────────────────        ──────────────────────────────────────────
 reads the task prompt from tasks.json                 downloads submissions/<task>/
 agent picks and runs its own tools                    fetches the reference into pack/reference/
 writes the required output files          ──────►      runs the scorer via grade_wrapper.py
 never sees the reference                              emits a ranked-ready envelope JSON
```

The reference NIfTIs live only in the grading plane (pulled from the Hub at grade time), so the
ground truth is never in the agent's input.

The execution plane is whatever environment supplies the task's tools — the current sweeps use a
self-hosted Neurodesk runner, but nothing in the harness depends on that. A plane that can run the
task prompt and write the required output paths can be graded.

## Files

| file | role |
|---|---|
| `run_manifest.json` | one entry per gradeable task: which pack, which scorer, the prediction flag (`--mask`/`--seg`/`--pred`), the detail shape, and the reference location + filenames. The single source of truth the tooling reads. |
| `fetch_reference.py` | pulls a task's reference NIfTIs from the Hugging Face dataset `neurodeskorg/skills-comm-ground-truth` at the revision pinned in the manifest, into its `pack/reference/`. The dataset is gated, so this needs a read token in `HF_TOKEN` for an account with access. Idempotent. |
| `grade_wrapper.py` | the uniform front-end. Dispatches to the correct scorer, wraps the result in a stable envelope, and aggregates many envelopes into a ranked leaderboard. |

## The output contract (why grading is deterministic)

Every gradeable task prompt in `tasks.json` mandates exact output paths. The primary output is
always `submissions/<task_id>/output.nii.gz`. Registration tasks also require a transformed
segmentation or mask, and brain-extraction tasks can include `stripped.nii.gz`. One
`submissions/` tree holds one folder per task, so a run over many tasks stays namespaced. The
grader reads only the paths in `run_manifest.json`; it does not search for outputs.

## The scoring model — a tier *and* a number

Each scorer runs a cascade of gates, then a score, then one override — and you always get a
rankable number:

1. **Validity gates** (binary, native grid, non-empty, plausible volume, plus task-specific gates
   like no-dura-inclusion, lesion-retained, no-class-collapse). Any failure → `verdict = "invalid"`,
   `score = 0`.
2. **Quality** (only if all gates pass) → a weighted 0–100 from per-metric subscores, banded into
   `unacceptable / marginal / acceptable` at the pack's `verdict_thresholds`.
3. **`indistinguishable`** overrides the band when *every* scored metric lands inside what the pack's
   own references achieve. Each pack sets that bar from its calibration: a consensus-calibrated pack
   asks for every metric at least as good as the worst held-out tool, an inter-rater-calibrated pack
   asks for full marks on every metric. It is a separate test, not a score threshold — so a submission
   can be `indistinguishable` without scoring 100, and `score` is **not** monotonic with the tier.

`valid` and `score` are independent: a submission can be valid but score low (e.g. a mask that
passes every gate but overlaps the reference poorly). Only `invalid` forces the score to 0.

Two packs carry a one-page figure of the whole cascade — reference construction, gates, weights, and
a worked case where the gate and the score disagree. They are worth reading before the others,
because they cover the two ways a pack is calibrated:

| figure | calibration | shows |
|---|---|---|
| [`structural-brain-extraction`](../graders/structural-brain-extraction/README.md) | consensus of a tool panel, leave-one-tool-out | a mask that scores ~71 on metrics yet fails a gate |
| [`clinical-wmh-segmentation`](../graders/clinical-wmh-segmentation/README.md) | inter-rater, three expert tracings | a mask that finds every lesion (F1 = 1.0) and still only reaches `marginal` |

## Envelope schema (`schema_version 1.0`)

`grade_wrapper.py grade` emits one JSON per submission:

```json
{ "task_id": "...", "model": "...", "condition": "baseline|skill", "timestamp": "...Z",
  "valid": true, "verdict": "indistinguishable", "score": 100.0, "tiebreak": 1.0,
  "gate_failures": [], "detail": { "kind": "binary|multiclass", ... },
  "raw": { ...full untouched scorer output for drill-down... } }
```

`detail` normalises the two scorer families: `binary` carries `metrics` + `subscores`; `multiclass`
carries `per_class`. `tiebreak` (mean Dice) breaks ties at equal `score`.

## Running it

```bash
# list the live (gradeable) task IDs — the functional subset of the full catalog
python grade_wrapper.py list            # add --verbose for scorer + detail kind

# fetch the grader-side reference for a task (gated dataset; export HF_TOKEN first)
python fetch_reference.py --task clinical-wmh-segmentation

# grade one submission -> envelope JSON
# --submission-dir is the working root; the grader looks for
# <root>/submissions/<task_id>/output.nii.gz (so one root can hold many tasks)
python grade_wrapper.py grade \
  --task clinical-wmh-segmentation --submission-dir ./run_qwen \
  --model qwen --condition baseline --out results/qwen.json

# rank many envelopes -> leaderboard.json (per-task ranking + model x task matrix)
python grade_wrapper.py aggregate --glob "results/*.json" --out results/leaderboard.json
```

Add a task by giving it an entry in `run_manifest.json` (pack, scorer, flag, reference) — no
code change needed.

The full task catalog (`tasks.json`) stays complete; the automated subset is the manifest.
Live tasks also carry `"grading": "automated"` in `tasks.json`, so the functional set is
queryable from the catalog itself. `run_manifest.json` remains the source of truth for what the
harness grades.

## CI

`.github/workflows/grade.yml` drives this on GitHub:

- **`grade`** — reusable (`workflow_call`) + manual: scores one real submission and uploads its
  envelope. The execution-plane workflow calls this per run.
- **`selftest`** — on every push touching `harness/` or `graders/`: synthesises a perfect
  submission (a copy of the reference) and a broken one (all-zeros), and asserts the grader
  returns `indistinguishable`/100 and `invalid` respectively. Runs entirely on a github-hosted
  runner — it validates the grading contract without involving the execution plane at all.
