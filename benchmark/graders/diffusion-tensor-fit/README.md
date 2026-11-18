# Grader: `diffusion-tensor-fit`

Grades a **diffusion tensor fit and the record of the acquisition it was fitted from**.

**What it tests: whether the acquisition was read before it was fitted.** A tensor fit runs on
any gradient table a tool can parse and exits cleanly whatever went into it, so a finished fit
says nothing about whether the acquisition could support one. The graded answer is not the map but a short record the task asks
for first: how many volumes the series holds, how many are b0s, how many are
diffusion-weighted, how many of those carry a non-zero gradient vector, and whether the
acquisition can support a tensor fit. The maps are the deliverable wherever it can.

## The reference

Each case's acquisition is staged for the agent by the harness from the gated reference
dataset
[`neurodeskorg/skills-comm-ground-truth`](https://huggingface.co/datasets/neurodeskorg/skills-comm-ground-truth),
and the case's `truth.json` records what that staged acquisition contains. Truth is computed
from the staged files themselves, not from any published copy: a b-value of 50 or more makes a
volume diffusion-weighted, a gradient vector shorter than 1e-3 carries no direction, and a
tensor needs six.

## Scorer

```bash
# fetch the case's truth (see reference/README.md), then:
python3 score_tensor_fit.py --submission submissions/diffusion-tensor-fit/<case>/ --pack . [--json result.json]
```

The submission is the case's output directory: `acquisition.json`, and `output.nii.gz` (FA)
with `md.nii.gz` where the acquisition supports a fit.

## Metrics

Weighted quality, renormalised over the metrics that apply to the case:

- **usability_correct** (0.50) — the record's verdict on whether the acquisition can support
  a fit
- **directions_correct** (0.30) — the count of diffusion-weighted volumes with a non-zero
  gradient vector, exact
- **inventory_correct** (0.10) — volumes, b0s and diffusion-weighted volumes, each exact
- **fit_delivered** (0.10) — the FA map is there; scored only where the acquisition supports
  a fit

## Validity gates

- **report_present** — `acquisition.json` is there, parses, and carries every field of the
  contract with the right type
- **no_fabricated_fit** — no metric map where the acquisition cannot support a tensor fit

## Verdicts

`complete` ≥ 99.9 (every field right), `acceptable` ≥ 60, `marginal` ≥ 30, else
`unacceptable`; any gate failure is `invalid`. The reasons are in
[`rubrics/policy.json`](rubrics/policy.json).
