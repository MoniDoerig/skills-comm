# ANTs registration reference

Module: `module load ants/2.6.0` (or latest). Key binaries: `antsRegistration`, `antsRegistrationSyN.sh`, `antsRegistrationSyNQuick.sh`, `antsApplyTransforms`, `antsBrainExtraction.sh`, `ImageMath`, `CreateJacobianDeterminantImage`, `MeasureImageSimilarity`, `LabelOverlapMeasures`, `CreateTiledMosaic`.

## When to use ANTs
- Gold-standard inter-subject **nonlinear** normalization (SyN is consistently top-ranked in registration benchmarks).
- Anything needing diffeomorphic (invertible, topology-preserving) warps.
- Multimodal registration via Mattes MI.

## Quickest correct path: the SyN wrapper scripts

`antsRegistrationSyN.sh` runs a sane rigid → affine → SyN pipeline with good defaults. Use `...SyNQuick.sh` for ~5–10× faster, slightly lower-quality (good for QC/drafts).

```bash
# Inter-subject, same modality (T1 -> MNI T1), full quality
antsRegistrationSyN.sh -d 3 \
  -f MNI152_T1_1mm_brain.nii.gz \   # fixed (reference)
  -m subject_T1_brain.nii.gz \      # moving
  -o sub2mni_ -n 8                  # output prefix, threads

# Transform type via -t :  r(rigid) a(affine) s(rigid+affine+SyN, default)
#   so(SyN only)  b(rigid+affine+B-spline SyN)  br / bo (B-spline variants)
# Quick draft:
antsRegistrationSyNQuick.sh -d 3 -f fixed.nii.gz -m moving.nii.gz -o out_ -t s
```

Outputs (prefix `sub2mni_`): `*Warped.nii.gz` (moving in fixed space), `*InverseWarped.nii.gz`, `*0GenericAffine.mat`, `*1Warp.nii.gz`, `*1InverseWarp.nii.gz`.

**Cross-modality** (e.g. T2 moving → T1 fixed): the wrapper uses MI by default for the linear stages, which is correct; just pass the two different-contrast images.

## Full control: `antsRegistration`

Use when you need custom metrics, masks, multi-metric stages, or non-default schedules.

```bash
antsRegistration --dimensionality 3 --float 1 \
  --output [out_,out_Warped.nii.gz] \
  --interpolation Linear \
  --winsorize-image-intensities [0.005,0.995] \
  --use-histogram-matching 0 \
  --initial-moving-transform [fixed.nii.gz,moving.nii.gz,1] \
  --transform Rigid[0.1] \
    --metric MI[fixed.nii.gz,moving.nii.gz,1,32,Regular,0.25] \
    --convergence [1000x500x250x100,1e-6,10] --shrink-factors 8x4x2x1 --smoothing-sigmas 3x2x1x0vox \
  --transform Affine[0.1] \
    --metric MI[fixed.nii.gz,moving.nii.gz,1,32,Regular,0.25] \
    --convergence [1000x500x250x100,1e-6,10] --shrink-factors 8x4x2x1 --smoothing-sigmas 3x2x1x0vox \
  --transform SyN[0.1,3,0] \
    --metric CC[fixed.nii.gz,moving.nii.gz,1,4] \
    --convergence [100x70x50x20,1e-6,10] --shrink-factors 8x4x2x1 --smoothing-sigmas 3x2x1x0vox
```

Metric selection inside stages:
- Same contrast deformable stage: `CC[fixed,moving,1,4]` (cross-correlation, radius 4).
- Different contrast: `MI[fixed,moving,1,32]` (Mattes MI, 32 bins) for all stages.
- `Regular,0.25` = sample 25% of voxels (speed); use a fixed/moving **mask** with `--masks [fixedMask,movingMask]` to focus the metric.

## Applying transforms (`antsApplyTransforms`)

**Order matters: transforms are applied in the reverse of the order listed, and the *last* listed is applied *first*.** To take a subject image into MNI you list warp then affine:

```bash
antsApplyTransforms -d 3 \
  -i subject_image.nii.gz \
  -r MNI152_T1_1mm.nii.gz \
  -o subject_in_mni.nii.gz \
  -t sub2mni_1Warp.nii.gz \
  -t sub2mni_0GenericAffine.mat \
  -n Linear
```

- **Label/mask images → `-n GenericLabel`** (or `NearestNeighbor`). Never resample a parcellation/segmentation with `Linear`.
- To go the **other way** (MNI → subject), use the inverse warp and invert the affine: `-t [sub2mni_0GenericAffine.mat,1] -t sub2mni_1InverseWarp.nii.gz` (note reversed order and `,1` for affine inversion).
- Compose a single displacement field for reuse: add `-o [composite_warp.nii.gz,1]`.

## Brain extraction (do before inter-subject/cross-modal)
```bash
antsBrainExtraction.sh -d 3 -a T1.nii.gz \
  -e template.nii.gz -m template_brainprob.nii.gz -o bex_
```
Or use `mri_synthstrip` (FreeSurfer) / `hd-bet` for a faster modern alternative.

## Notes
- `--float 1` halves memory with negligible accuracy loss.
- For very large initial offsets, `--initial-moving-transform [f,m,1]` (the `1`) does a center-of-mass init.
- ANTs reads `$ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS`; set it or use `-n`.
