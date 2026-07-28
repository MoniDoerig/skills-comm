# Human Registration QC Verification Form

Complete this form after reviewing the generated visuals (edge overlay, checkerboard, Jacobian heatmap, mosaic / `slicesdir`). Use the same scale as the AI evaluation (Pass / Borderline / Fail) and the same criterion labels so agreement can be computed.

The AI evaluation for this case is at: `qc/<subject>_<target>_<timestamp>_ai_eval.md`

---

## Case Information

| Field | Value |
|-------|-------|
| **Subject / moving image** | |
| **Fixed / target (e.g. MNI152)** | |
| **Registration tool & transform** | |
| **Warp field available?** | Yes / No |
| **Reference labels in target space?** | Yes / No (which) |
| **Visuals reviewed** | |
| **Rater name** | |
| **Date reviewed** | |
| **Time spent (minutes)** | |

---

## Quantitative Review

| Metric | Value (from AI eval) | Within expected? |
|--------|----------------------|------------------|
| Folding (Jacobian ≤0) | | Yes / No |
| Jacobian min / max | | Yes / No / Uncertain |
| log-Jacobian SD | | Yes / No / Uncertain |
| Similarity (in-mask) | | Yes / No / Uncertain |
| Mean Dice (if labels) | | Yes / No / N/A |

*Any folding (> 0%) is a hard fail regardless of other metrics.*

---

## Visual Criteria

Rate each: **Pass**, **Borderline**, or **Fail**. Add brief notes for any Borderline/Fail.

### 1. Boundary / structural correspondence

Do anatomical boundaries (cortical ribbon, ventricles, subcortical structures) line up in the edge overlay and run continuously across the checkerboard tiles?

| | |
|-|-|
| **Rating** | Pass / Borderline / Fail |
| **Notes** | |

### 2. Deformation regularity (no folding)

Is the Jacobian strictly positive and smoothly varying? Any negative region (folding) is an automatic Fail; localize it on the Jacobian heatmap.

| | |
|-|-|
| **Rating** | Pass / Borderline / Fail |
| **Notes** | |

### 3. Label / tissue overlap

Is Dice healthy for the structures' size, with no collapsed ROI? Mark **Not assessable** if no reference labels exist in the target space.

| | |
|-|-|
| **Rating** | Pass / Borderline / Fail / Not assessable |
| **Notes** | |

### 4. Intensity similarity

Is the fixed-vs-warped similarity within the expected range / near the cohort median for this modality pair?

| | |
|-|-|
| **Rating** | Pass / Borderline / Fail |
| **Notes** | |

### 5. Global alignment / no gross error

Correct target space and orientation, no moving/fixed swap, no whole-structure displacement?

| | |
|-|-|
| **Rating** | Pass / Borderline / Fail |
| **Notes** | |

---

## Overall Verdict

| | |
|-|-|
| **Overall rating** | Pass / Borderline / Fail |
| **Confidence** | High / Medium / Low |

*Hard stops: no overall Pass if criterion 2 is Borderline/Fail (folding) or if a quantitative warning is unexplained; overall Fail if criterion 5 fails (gross error / wrong space / swap).*

---

## Free-Text Notes

*(Unusual contrast, pathology, post-surgical anatomy, atrophy, FOV, or anything that makes the judgement uncertain.)*

---

## Recommended Action

- [ ] None — registration acceptable for downstream use
- [ ] Use with caution in region: *(specify)*
- [ ] Re-run with changes: *(specify — e.g. mask, metric, initialization, transform model)*
- [ ] Manual review / exclude subject

---

## Agreement Check (optional — fill in after reviewing the AI eval)

| Criterion | Your rating | AI rating | Agreement? |
|-----------|-------------|-----------|------------|
| 1. Boundary / structural correspondence | | | Yes / No |
| 2. Deformation regularity (no folding) | | | Yes / No |
| 3. Label / tissue overlap | | | Yes / No |
| 4. Intensity similarity | | | Yes / No |
| 5. Global alignment / no gross error | | | Yes / No |
| **Overall verdict** | | | Yes / No |
| **Confidence** | | | Yes / No |

**Notes on disagreements:**
