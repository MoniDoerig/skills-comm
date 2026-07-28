# Registration QC metrics — commands, interpretation, thresholds

Compute every metric with a validated binary. Load `module load ants/2.6.0 fsl/6.0.7.16 convert3d freesurfer/7.3.2`. The four families below are ordered by diagnostic value.

> **Threshold caveat (read once, apply everywhere):** absolute cutoffs depend on contrast, resolution, field strength, ROI size, and the registration target. A Dice of 0.75 is excellent for a thin structure and poor for whole-brain. Where you have a cohort, compute the metric distribution and flag outliers (e.g. > 2–3 SD from the median, or modified-z via MAD) instead of trusting a fixed number. The numbers below are starting heuristics, not laws.

## 1. Deformation regularity — Jacobian determinant (most diagnostic for nonlinear)

The Jacobian determinant of the displacement field measures local volume change. **Values ≤ 0 mean the warp folds space onto itself — a topology violation that is never acceptable** in a diffeomorphic normalization.

```bash
# From an ANTs SyN warp field:
CreateJacobianDeterminantImage 3 sub2mni_1Warp.nii.gz jac.nii.gz 0 0
#   args: dim  warpField  output  [doLogJacobian=0/1]  [useGeometric=0/1]

# Fraction of folding voxels, min/max, and spread:
fslstats jac.nii.gz -R                      # min and max
ImageMath 3 jac_neg.nii.gz m jac.nii.gz 0   # (or use c3d thresholding)
c3d jac.nii.gz -thresh -inf 0 1 0 -voxel-sum   # count voxels with det<=0

# Log-Jacobian SD (smoothness of volume change) — high SD = erratic deformation:
CreateJacobianDeterminantImage 3 sub2mni_1Warp.nii.gz logjac.nii.gz 1 0
fslstats logjac.nii.gz -m -s                 # mean (~0 ok), SD
```
FSL FNIRT alternative: `fnirtfileutils --in=warp_coef --ref=ref --jac=jac.nii.gz`.

**Interpretation**
- Any voxel with det ≤ 0 → **folding → FAIL** (note where; localize with the Jacobian heatmap in `visual-qc.md`).
- min Jacobian very small (e.g. < 0.1) or max very large (e.g. > 10) → extreme local compression/expansion → concerning even without folding.
- log-Jacobian SD much larger than your cohort's typical value → erratic warp → BORDERLINE/FAIL.
- Well-behaved SyN: det strictly positive, min/max within a modest range, smooth log-Jac map.

## 2. Intensity similarity (fixed vs warped-moving)

Match the metric to the modality pairing (same rule as registration): MI/NMI for cross-modal, CC for same-modal. Always restrict to a mask (the fixed brain) so background doesn't inflate the score.

```bash
# ANTs (negative numbers: more-negative = better match for MI/CC as implemented):
MeasureImageSimilarity -d 3 \
  -m MI[fixed.nii.gz,warped_moving.nii.gz,1,32] \
  -x fixed_brain_mask.nii.gz
MeasureImageSimilarity -d 3 \
  -m CC[fixed.nii.gz,warped_moving.nii.gz,1,4] \
  -x fixed_brain_mask.nii.gz

# FSL cross-correlation between two volumes:
fslcc -m mask.nii.gz fixed.nii.gz warped_moving.nii.gz

# Correlation ratio / NMI for a quick read (AFNI):
3ddot -docor -mask mask.nii.gz fixed.nii.gz warped_moving.nii.gz
```

**Interpretation**
- Compare against the *expected* range for this modality pair, ideally a cohort distribution. Similarity is best read relatively: a subject far below the cohort median is suspect even if its absolute number "looks fine".
- Similarity alone never proves success — a smooth blurry warp can score well. Treat it as necessary-not-sufficient and corroborate with overlap + visuals.

## 3. Label / segmentation overlap (strongest evidence when available)

If you have segmentations or an atlas warped into the same space, Dice/Jaccard is the closest thing to ground truth.

**Overlap needs two label maps in the *same* space — a warped parcellation alone is not enough.** You are comparing the moving labels (warped into the target) against a *reference* that already lives in the target space. In practice the reference is one of:
- an atlas/parcellation defined in the template space (e.g. an MNI-space atlas) — the usual choice for normalization-to-MNI QC;
- another subject's labels warped into the same target (cross-subject consistency);
- for tissue overlap, the template's GM/WM/CSF priors vs the subject's warped tissue segmentation.
If no reference label exists in the target space, you cannot compute Dice — fall back to similarity + visual evidence and lower confidence accordingly (see `rubric.md`).

```bash
# ANTs: full overlap stats (Dice, Jaccard, etc.) for all labels:
LabelOverlapMeasures 3 atlas_in_target.nii.gz target_atlas.nii.gz overlap.csv

# Per-pair Dice with c3d:
c3d ref_label.nii.gz warped_label.nii.gz -overlap 1   # repeat per label value

# FreeSurfer parcellation overlap:
mri_compute_overlap -a -all seg_a.mgz seg_b.mgz       # volumes
mris_compute_parc_overlap --s1 subj --s2 fsaverage --hemi lh --label aparc  # surface
```

**Interpretation (heuristics, size-dependent)**
- Whole-brain tissue (GM/WM/CSF) Dice ≳ 0.85 same-modal anatomical → healthy; 0.7–0.85 → check; < 0.7 → concerning.
- Per-ROI: a high *mean* Dice with one or two **very low ROIs** signals a localized failure → BORDERLINE, and name the ROI.
- Small/thin structures naturally score lower; judge each ROI against its own expectation, not a flat cutoff.
- Also useful: average symmetric **surface distance** / Hausdorff for boundary accuracy (`SurfaceDistanceMeasures`-style tools, or compute from label boundaries).

## 4. Tool convergence / final cost

Capture the registration's own final metric value and convergence from its log (ANTs prints per-stage convergence; FNIRT/elastix write logs). A stage that hit max-iterations without converging, or a final cost far from the cohort norm, is corroborating evidence for a problem.

## Putting metrics together
No metric is decisive alone except **folding (Jacobian ≤ 0) = FAIL**. Otherwise weigh: overlap (if present) > Jacobian regularity > similarity, and let visuals (next file) break ties and set confidence. Feed the assembled numbers into the rubric in `rubric.md`.
