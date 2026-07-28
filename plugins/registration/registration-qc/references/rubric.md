# QC rubric — mapping evidence to verdict × confidence

Two independent decisions. **Verdict** = is the registration usable? **Confidence** = how strongly does the evidence support that verdict? They are orthogonal: a registration can be decisively broken (FAIL/HIGH) or fine-but-thinly-evidenced (PASS/LOW).

The verdict is built up from five criteria (rated each, then rolled up), the same five used in the report template and the human verification form. Rate every criterion, then apply the hard-stop rules, then read the overall verdict and confidence.

## The five criteria (rate each Pass / Borderline / Fail)

**1. Boundary / structural correspondence** — do anatomical boundaries line up (edge overlay, checkerboard)?

| Rating | Picture |
|--------|---------|
| Pass | Edges hug corresponding boundaries (cortical ribbon, ventricles, subcortical); checkerboard continuous across tiles. |
| Borderline | Mild offset confined to one region; most boundaries align. |
| Fail | Systematic offset, or a region where structures clearly do not correspond. |

**2. Deformation regularity (no folding)** — Jacobian determinant of the warp.

| Rating | Picture |
|--------|---------|
| Pass | Strictly positive everywhere; smooth log-Jacobian; min/max in a modest range. |
| Borderline | No folding, but a localized extreme (very small/large det) or erratic log-Jac vs cohort. |
| Fail | **Any voxel ≤ 0 (folding).** |

**3. Label / tissue overlap** — Dice/Jaccard against a reference label map in the target space.

| Rating | Picture |
|--------|---------|
| Pass | Mean Dice healthy for the structures' size; no collapsed ROI. |
| Borderline | Good mean but one/two ROIs notably low (localized problem). |
| Fail | Broadly low overlap, or a core structure collapsed. |
| Not assessable | No reference labels in the target space → record as such (caps confidence). |

**4. Intensity similarity** — fixed vs warped-moving, correct metric for the modality pair, in-mask.

| Rating | Picture |
|--------|---------|
| Pass | Within the expected range / near the cohort median. |
| Borderline | Acceptable but below cohort typical. |
| Fail | Markedly low vs expectation. |

**5. Global alignment / no gross error** — correct target space and orientation, no swap, no whole-structure displacement.

| Rating | Picture |
|--------|---------|
| Pass | Correct space/orientation; brain sits where it should. |
| Borderline | Minor global offset within tolerance. |
| Fail | Gross displacement, wrong space, orientation mismatch, or moving/fixed swap. |

## Hard-stop rules (apply before declaring an overall verdict)
- Criterion 2 Borderline or Fail (any folding) → overall **cannot be PASS**.
- Criterion 5 Fail (gross error / wrong space / swap) → overall **FAIL**, and flag the cause as a likely pipeline bug, not a registration-quality issue.
- A quantitative warning (folding > 0%, Dice/similarity outlier vs cohort) blocks PASS unless the report explains why it is benign.
- Two criteria Fail, or any single Fail that affects a large contiguous region or core structure → overall **FAIL**.
- Best achievable verdict when a real but small/localized problem exists → **BORDERLINE**.

## The verdict axis (PASS / BORDERLINE / FAIL)

Decide on the *substance* of the alignment, weighting evidence: **folding > overlap > Jacobian smoothness > similarity**, with visuals as tie-breaker.

| Verdict | Picture |
|---------|---------|
| **PASS** | No folding (Jacobian strictly positive). Similarity within expected/cohort range. Overlap healthy where measurable (tissue Dice ≳ 0.85 same-modal; per-ROI generally good). Visuals: edges hug boundaries, checkerboard continuous, difference is mostly noise. |
| **BORDERLINE** | Globally usable but with a *localized* or *moderate* issue: one ROI with low Dice amid good mean, mild Jacobian irregularity (no folding), similarity acceptable-but-below-cohort, or a visual showing one region slightly off. Usable for some purposes, risky for analyses touching the affected region. |
| **FAIL** | A decisive failure on any axis: **any negative Jacobian / folding**; gross misalignment visible in overlay/mosaic; implausible deformation; markedly low overlap or similarity vs expectation; a whole structure/hemisphere displaced. |

**Hard rules**
- Negative Jacobian (folding) anywhere in a diffeomorphic normalization → **FAIL** (it's a broken topology, not a borderline aesthetic issue).
- Moving/fixed swapped, wrong space, or orientation mismatch detected → **FAIL** (and flag the cause — it's usually a pipeline bug, not a registration-quality issue).

## The confidence axis (HIGH / MEDIUM / LOW)

Confidence is about **evidentiary strength and agreement**, not about how good the registration looks.

| Confidence | Condition |
|-----------|-----------|
| **HIGH** | ≥ 3 independent lines of evidence available *and* they agree (e.g. overlap + Jacobian + similarity + visuals all consistent). Labels/warp present. The verdict is overdetermined. |
| **MEDIUM** | Evidence mostly agrees but **one line is missing** (e.g. no segmentations, so no Dice) or **one disagrees mildly**; or thresholds are only roughly applicable to this contrast. |
| **LOW** | **Sparse** evidence (only the warped image → similarity + visuals only), lines of evidence **conflict** (e.g. strong similarity but the Jacobian shows folding, or great Dice but visuals look wrong), or the case is **out-of-distribution** (unusual contrast, pathology, pediatric/atrophied brain) so thresholds are untrustworthy. |

**Evidence-availability cap:** with only a resampled image (no warp, no labels), confidence cannot exceed MEDIUM — you cannot see folding or measure overlap, so you're inferring from a partial picture.

**Conflict forces LOW (or re-examination):** if two strong lines disagree, do not paper over it with a confident verdict. Report the conflict, drop confidence to LOW, and recommend human inspection — conflicting evidence usually means one metric is being fooled (e.g. similarity rewarding a blurry over-regularized warp that folds).

## Worked examples

**PASS / HIGH** — MNI normalization. Jacobian strictly positive, log-Jac SD typical for the cohort; NMI within range; mean tissue Dice 0.90, all ROIs healthy; edge overlay and mosaic clean. Four agreeing lines → overdetermined.

**PASS / LOW** — Only the warped T1 in MNI was provided (no warp field, no labels). Similarity good, edge overlay looks aligned. Verdict PASS on what's visible, but no folding check and no overlap → confidence capped low; recommend retaining the warp for a fuller check.

**BORDERLINE / MEDIUM** — Mean Dice 0.86 but right hippocampus Dice 0.55; Jacobian positive but a localized hotspot near the right medial temporal lobe; similarity fine; no folding. Globally usable, but anything analyzing right MTL should not trust it. One clearly-affected region, evidence otherwise agrees → MEDIUM.

**FAIL / HIGH** — Jacobian shows 0.4% of voxels ≤ 0 (folding) in the right temporal lobe; mosaic confirms a buckled cortical ribbon there; per-ROI Dice collapses in that region. Multiple lines agree on a decisive failure.

**FAIL / LOW** — Only the warped image available; overlay shows the whole brain shifted ~1 cm inferiorly and similarity is poor — clearly wrong, so FAIL — but with no warp/labels and a possibly atypical input, the *cause* and extent are uncertain, so confidence is low and manual review is advised. (Note: verdict can be confident-looking while confidence stays low when evidence is thin; here the gross shift makes FAIL safe, but everything else is unmeasured.)

**BORDERLINE / LOW** — Cross-modal CT→MR. Similarity ambiguous (MI hard to threshold for this pair), no labels, visuals equivocal in one region, input is post-surgical (out-of-distribution). Can't commit to PASS or FAIL; flag for a human.

## Output discipline
Whatever the verdict/confidence, the report (Step 5 of SKILL.md) must:
1. State the **verdict and confidence** up front.
2. List the **evidence values** actually computed (and note what was unavailable).
3. Give the **reason in plain language** — the dominant driver and any conflict/gap — not just numbers.
4. Make a **recommendation** (use / use-with-caution-in-region-X / re-run with change Y / manual review).

For cohorts: compute each metric's distribution, mark subjects > 2–3 modified-z (MAD-based) as outliers, and surface those for human review rather than auto-failing — a population view makes the thresholds defensible.
