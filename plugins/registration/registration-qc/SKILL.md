---
name: registration-qc
description: >
  Quality-control a completed image registration and return a structured verdict —
  PASS / BORDERLINE / FAIL, each at HIGH / MEDIUM / LOW confidence — grounded in
  tool-computed metrics and generated visuals rather than guesswork. Use whenever
  the user wants to check, validate, QC, score, or decide whether to trust a
  registration/normalization/alignment: "did this registration work", "QC these
  warps", "is this aligned to MNI correctly", "check my coregistration", "score
  registration quality", "pass or fail this normalization", "the warp looks weird",
  "evaluate registration accuracy", or batch QC across a cohort. It computes
  similarity metrics, Jacobian-determinant regularity, and label/tissue overlap with
  validated tools (ANTs MeasureImageSimilarity, CreateJacobianDeterminantImage,
  LabelOverlapMeasures, c3d, FSL), renders overlay/checkerboard/edge/mosaic visuals,
  and applies an explicit rubric to emit a defensible verdict. ALWAYS compute
  metrics and render visuals with tools before writing custom Python.
---

# Registration QC (evidence-based verdict)

Decide whether a registration is good enough to use, and say how sure you are. The output is always a **verdict × confidence** pair backed by tool-computed evidence — never an unsupported eyeball judgment, never a single metric in isolation.

## Core principle: triangulate, don't trust one number

A registration that "ran without error" is not a correct one, and no single metric is sufficient:
- High intensity similarity can coexist with **folding** (a topologically broken warp).
- Good global overlap can hide a **regionally catastrophic** failure (e.g. one hemisphere, the ventricles, the brainstem).
- A visually fine overlay can mask **implausible deformation** that will bias downstream stats.

So QC combines **four independent lines of evidence** and reads the *agreement among them* as the confidence signal:
1. **Similarity** between warped-moving and fixed (NMI / CC / correlation ratio).
2. **Deformation regularity** — Jacobian determinant of the warp (any ≤0 = folding = automatic red flag).
3. **Label / tissue overlap** — Dice/Jaccard per ROI and for GM/WM/CSF, *when segmentations exist*.
4. **Visual inspection** — boundary/edge correspondence, checkerboard, difference, Jacobian map.

**Compute everything with tools first.** Python is only for parsing tool output, aggregating across subjects, and assembling the report (see "When Python is acceptable"). Do not hand-implement Dice, mutual information, or a Jacobian.

## Step 1 — Establish what you can measure

QC quality is capped by available evidence. Inventory inputs first:

| Available | Enables |
|-----------|---------|
| fixed + warped-moving image | similarity metrics, visual overlays/checkerboard/difference |
| the warp field (`*Warp.nii.gz` / `--fout` / `cpp`) | Jacobian determinant regularity (the single most diagnostic nonlinear metric) |
| segmentations / atlas labels in both spaces | Dice/Jaccard overlap (the strongest "ground-truth-like" evidence) |
| tissue priors or GM/WM/CSF masks | tissue-overlap Dice |
| only the resampled image (no warp, no labels) | similarity + visual only → **caps confidence at MEDIUM** |

If only the warped image exists, say so: the verdict can still be PASS/FAIL but confidence is limited by missing evidence.

## Step 2 — Compute the metric battery (tools)

A ready-to-run orchestrator lives in `scripts/` and is the preferred way to run Steps 2–3 (it calls the validated binaries, parses them, renders the visuals, and writes a report scaffold + metrics row — it does not compute metrics itself or decide the verdict). Use the one that fits the environment:
- `scripts/registration_qc.sh` — bash, house-style, pins modules; best for a single subject inside a scripted/scheduler pipeline.
- `scripts/registration_qc.py` — same binaries via subprocess, plus a `--cohort-csv` that accumulates rows and flags outliers (median/MAD modified z) across a cohort.

Both take `--fixed --moving-warped --outdir --subject` and optional `--warp` (Jacobian), `--moving-labels --ref-labels` (Dice; both in target space), `--mask`, `--mode same|cross`. Keep the script as the reproducibility record. Run the metrics by hand (below) only when you need a step the orchestrator doesn't cover.

Load modules (`module load ants/2.6.0 fsl/6.0.7.16 convert3d`) and run the metrics in `references/metrics.md`. Priority order:

1. **Jacobian determinant** (if a warp exists) — `CreateJacobianDeterminantImage`. Report: fraction of voxels ≤ 0 (folding), min/max, and SD of log-Jacobian. **Any negative Jacobian is a hard red flag.**
2. **Similarity** — `MeasureImageSimilarity` (Mattes MI / NMI for cross-modal, CC for same-modal) between fixed and warped-moving, inside the fixed brain mask.
3. **Label overlap** (if a reference label map exists in the target space — an atlas, or another labelled subject; a warped parcellation on its own is not enough) — `LabelOverlapMeasures` or `c3d` for mean Dice, per-ROI Dice, and tissue Dice.
4. **Tool's own final cost** — capture it from the registration log if available; a stage that didn't converge is a warning sign.

`references/metrics.md` gives exact commands, what good/bad looks like, and threshold guidance with caveats (thresholds are contrast/resolution/dataset-dependent — prefer comparison against a cohort distribution over absolute cutoffs).

## Step 3 — Generate visual QC (tools)

Visuals are decisive for BORDERLINE cases and for raising confidence. Generate, don't describe-from-imagination. Use the commands in `references/visual-qc.md`:
- **Edge/contour overlay** of fixed boundaries on warped-moving (or vice versa) — the most informative single view for boundary correspondence.
- **Checkerboard** of fixed vs warped — discontinuities at tile borders reveal misalignment.
- **Difference / absolute-difference** image — residual structure indicates leftover misregistration.
- **Jacobian heatmap** — localizes compression/expansion and folding.
- **Mosaic / lightbox** (`CreateTiledMosaic`, FSL `slicesdir`, AFNI `@chauffeur_afni`) — a multi-slice screenshot for the report and for batch review.

Save these as PNGs and reference them in the report; for cohorts, `slicesdir` produces a single browsable HTML index.

## Step 4 — Apply the rubric → verdict × confidence

Read `references/rubric.md` for the full decision logic and worked examples. The compressed logic:

**Verdict** (is it usable?):
- **PASS** — all available evidence consistent with good alignment: no folding, similarity in the expected range, good overlap (mean tissue Dice typically ≳ 0.8 for same-modal anatomical, per-ROI generally healthy), visuals show clean boundary correspondence.
- **FAIL** — clear failure on any decisive axis: visible gross misalignment, **negative Jacobians / folding**, implausible deformation, or markedly low overlap/similarity versus expectation.
- **BORDERLINE** — usable globally but with a localized or moderate problem (one region off, similarity acceptable-but-low, mild Jacobian irregularity), or evidence sits near thresholds.

**Confidence** (how strong is the evidence, NOT how good the registration is):
- **HIGH** — multiple independent lines agree (similarity + Jacobian + overlap + visuals all point the same way) and key evidence (labels, warp) is available. A clearly-broken registration is FAIL/HIGH.
- **MEDIUM** — evidence mostly agrees but a line is missing (e.g. no labels) or one disagrees mildly; or thresholds are borderline-reliable for this contrast.
- **LOW** — sparse evidence (only similarity available), lines of evidence **conflict** (e.g. great similarity but Jacobian folding), or the case is out-of-distribution so thresholds are untrustworthy.

Critically: **confidence reflects evidentiary strength and agreement, not registration quality.** Verdict and confidence vary independently — PASS/LOW (looks fine but thin evidence) and FAIL/HIGH (decisively broken) are both common and valid.

## Step 5 — Emit the structured report

ALWAYS output in this exact structure so results are comparable across subjects, auditable per criterion, and scorable against the human form. The five criteria are identical to those in `references/rubric.md` and the human verification form — do not rename them.

```
## Registration QC — <moving> → <fixed>

**Verdict: <PASS | BORDERLINE | FAIL>  ·  Confidence: <HIGH | MEDIUM | LOW>**

### Quantitative
| Metric | Value | Reference / cohort |
|--------|-------|--------------------|
| Folding (Jacobian ≤0) | <%> | 0% required |
| Jacobian min / max | <> / <> | strictly positive |
| log-Jacobian SD | <> | vs cohort |
| Similarity (<metric>, in-mask) | <> | expected range / cohort |
| Mean Dice (if labels) | <> | size-dependent |
| Worst ROI Dice | <name>=<> | flag if collapsed |

### Criteria
| Criterion | Rating | Notes |
|-----------|--------|-------|
| 1. Boundary / structural correspondence | Pass/Borderline/Fail | <edge + checkerboard observation> |
| 2. Deformation regularity (no folding) | Pass/Borderline/Fail | <Jacobian; HARD-STOP if folding> |
| 3. Label / tissue overlap | Pass/Borderline/Fail/Not assessable | <Dice; name collapsed ROIs> |
| 4. Intensity similarity | Pass/Borderline/Fail | <vs expected/cohort> |
| 5. Global alignment / no gross error | Pass/Borderline/Fail | <space, orientation, swap, displacement> |

### Reasoning
<2–4 sentences: which criteria drove the verdict, the dominant concern, and why
the confidence is what it is — name missing or conflicting evidence explicitly.>

### Visuals
<generated PNGs / slicesdir HTML>

### Recommendation
<use as-is / use with caution in region X / re-run with changes Y / manual review>
```

State the *reason* in plain terms (e.g. "folding in the right temporal lobe", "ventricle misalignment on axial checkerboard"), not just numbers. Roll the five criteria up to the verdict using the hard-stop rules in `references/rubric.md`. For cohort QC, also emit a one-line-per-subject summary table and flag outliers for human review.

## Step 6 — Write the paired human verification form

So AI and human ratings can be compared, write a blank copy of `references/human-verification-form.md` next to the report, using the **same criterion labels word-for-word**. Share a single timestamp across the report, the saved visuals, and the human form so the three pair unambiguously (e.g. `sub-04_syn_<TIMESTAMP>_{qc.png,ai_eval.md,human_eval.md}`). Tell the user to review the visuals, fill in the human form, and that agreement can then be scored criterion-by-criterion.

## When Python is acceptable (glue only)
After tools have produced metrics and visuals, use Python to: parse logs/CSVs, aggregate across subjects, compute cohort distributions and z-scores for outlier detection, and render the summary table/plots (`pandas`, `matplotlib`). Do **not** compute the core metrics (Dice, MI, Jacobian) in Python — call the validated binaries in `references/metrics.md`. Assembling the multi-panel figure from already-generated PNGs (nibabel + matplotlib) is fine.

## Constraints
- Folding (any Jacobian determinant ≤ 0) can never receive an overall PASS — it is a topology violation, not an aesthetic one.
- Never declare PASS from a single metric; require at least similarity + one corroborating line, and let visuals break ties.
- Confidence reflects evidentiary strength and agreement, not how good the registration looks. Verdict and confidence vary independently.
- With only a resampled image (no warp, no labels), confidence cannot exceed MEDIUM.
- If two strong lines of evidence conflict, do not paper over it — report the conflict, drop confidence, and recommend manual review.
- The five criterion labels in the report and the human form MUST match word-for-word; downstream agreement scoring depends on it.
- Keep the QC orchestrator (`scripts/registration_qc.sh` / `.py`) as the reproducibility record of exactly what was run; do not delete it after running.
- Compute metrics and render visuals with validated tools before writing Python. Verify each binary is available (`command -v` / `which`) before relying on it; do not assume a fixed version or install path.
