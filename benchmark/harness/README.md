# Benchmark grading harness

Automated, uniform grading for the neuroimaging benchmark. An open-weight model runs a task
prompt unattended (it picks its own tools), produces one output file, and this harness scores
it against a frozen reference — producing a numeric, rankable result.

## The two planes

The model *doing* a task needs the full neuroimaging stack (Lmod modules, SLURM, GPU); the
grader is pure `numpy`/`nibabel`/`scipy`. So the pipeline splits, and the split is also the
anti-leak boundary:

```
 EXECUTION PLANE  (Neurodesk self-hosted runner)      GRADING PLANE  (any github-hosted runner)
 ─────────────────────────────────────────────        ──────────────────────────────────────────
 reads the task prompt from tasks.json                 downloads submission/output.nii.gz
 agent picks tools, module load, sbatch                fetches the OSF reference into pack/reference/
 writes ONE file: submission/output.nii.gz  ──────►    runs the scorer via grade_wrapper.py
 never sees the reference                              emits a ranked-ready envelope JSON
```

The reference NIfTIs live only in the grading plane (pulled from OSF at grade time), so the
ground truth is never in the agent's input.

## Files

| file | role |
|---|---|
| `run_manifest.json` | one entry per gradeable task: which pack, which scorer, the prediction flag (`--mask`/`--seg`/`--pred`), the detail shape, and the OSF reference location + filenames. The single source of truth the tooling reads. |
| `fetch_reference.py` | pulls a task's reference NIfTIs from OSF (public project `zjqey`, no auth) into its `pack/reference/`. Idempotent. |
| `grade_wrapper.py` | the uniform front-end. Dispatches to the correct scorer (the three scorers are **never modified**), wraps the result in a stable envelope, and aggregates many envelopes into a ranked leaderboard. |

## The output contract (why grading is deterministic)

Every gradeable task prompt in `tasks.json` mandates one exact output path — the graded file is
always `submission/output.nii.gz` (brain-extraction tasks also write `submission/stripped.nii.gz`).
The grader reads **only** that path: no guessing which of several NIfTIs the agent meant, no
grading of intermediates or copied inputs.

## The scoring model — a tier *and* a number

Each scorer runs a two-tier cascade, and you always get a rankable score:

1. **Validity gates** (binary, native grid, non-empty, plausible volume, plus task-specific gates
   like no-dura-inclusion, lesion-retained, no-class-collapse). Any failure → `verdict = "invalid"`,
   `score = 0`.
2. **Quality** (only if all gates pass) → a weighted 0–100 from per-metric subscores, then banded
   into `unacceptable / marginal / acceptable / indistinguishable`. `indistinguishable` means "as
   good as the reference expects" and always scores 100, so the `score` is monotonic with the tier.

`valid` and `score` are independent: a submission can be valid but score low (e.g. a mask that
passes every gate but overlaps the reference poorly).

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

# fetch the grader-side reference for a task (public OSF, no auth)
python fetch_reference.py --task clinical-wmh-segmentation

# grade one submission -> envelope JSON
python grade_wrapper.py grade \
  --task clinical-wmh-segmentation --submission-dir ./run_qwen \
  --model qwen --condition baseline --out results/qwen.json

# rank many envelopes -> leaderboard.json (per-task ranking + model x task matrix)
python grade_wrapper.py aggregate --glob "results/*.json" --out results/leaderboard.json
```

Add a task by giving it an entry in `run_manifest.json` (pack, scorer, flag, OSF reference) — no
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
  submission (a copy of the OSF reference) and a broken one (all-zeros), and asserts the grader
  returns `indistinguishable`/100 and `invalid` respectively. Runs entirely on a github-hosted
  runner — it validates the grading contract with no Neurodesk dependency.
