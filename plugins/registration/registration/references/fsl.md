# FSL registration reference

Module: `module load fsl/6.0.7.16`. Set output type: `export FSLOUTPUTTYPE=NIFTI_GZ`. Key tools: `flirt` (linear), `fnirt` (nonlinear FFD), `applywarp`, `convert_xfm`, `invwarp`, `epi_reg`, `bet`, `fslmaths`, `fslhd`, `slicesdir`.

## When to use FSL
- Fast, robust **linear** (affine) registration (`flirt`).
- Nonlinear normalization to MNI with the standard FNIRT config.
- EPI→structural with fieldmap unwarping and BBR (`epi_reg`).

## Linear registration: `flirt`

```bash
flirt -in moving.nii.gz -ref ref.nii.gz \
  -omat moving2ref.mat -out moving_in_ref.nii.gz \
  -dof 12 -cost corratio -interp trilinear
```
- `-dof`: 6 (rigid), 7 (rigid+global scale), 9 (traditional), 12 (affine).
- `-cost`: `corratio` (default, good intra-modal), `mutualinfo`/`normmi` (cross-modal), `normcorr` (same modality), `bbr` (boundary-based, needs `-wmseg`).
- The `.mat` is a **FLIRT-format** 4×4 in FSL scaled-voxel space — not world space. Convert to ITK/ANTs with `c3d_affine_tool` (see `transforms.md`).

Concatenate / invert FLIRT matrices:
```bash
convert_xfm -omat A2C.mat -concat B2C.mat A2B.mat   # A2C = B2C * A2B
convert_xfm -omat ref2moving.mat -inverse moving2ref.mat
```

## Nonlinear: `fnirt` (always initialize with `flirt`)

```bash
# 1) affine init
flirt -in T1_brain.nii.gz -ref $FSLDIR/data/standard/MNI152_T1_2mm_brain.nii.gz \
  -omat aff.mat -dof 12
# 2) nonlinear (run on whole head, not brain-only, with the standard config)
fnirt --in=T1.nii.gz --aff=aff.mat \
  --config=T1_2_MNI152_2mm \
  --cout=warp_coef.nii.gz --fout=warp_field.nii.gz --iout=T1_in_mni.nii.gz
```

Apply / invert the warp:
```bash
applywarp -i label.nii.gz -r $FSLDIR/data/standard/MNI152_T1_2mm.nii.gz \
  -w warp_field.nii.gz -o label_in_mni.nii.gz --interp=nn   # nn for labels!
invwarp -w warp_field.nii.gz -o inv_warp.nii.gz -r T1.nii.gz
```

## EPI → structural with distortion correction: `epi_reg`

The right tool for functional/diffusion EPI to the subject's T1; uses BBR and optional fieldmap:
```bash
epi_reg --epi=func_example.nii.gz \
  --t1=T1.nii.gz --t1brain=T1_brain.nii.gz \
  --out=func2struct \
  [--fmap=fmap_rads.nii.gz --fmapmag=fmap_mag.nii.gz --fmapmagbrain=fmap_mag_brain.nii.gz \
   --echospacing=0.00059 --pedir=-y]
```
Output `func2struct.mat` (FLIRT) + `func2struct_warp.nii.gz` if a fieldmap was given.

## Skull-strip first when needed
```bash
bet T1.nii.gz T1_brain.nii.gz -f 0.4 -R    # tune -f; -R for robust center estimation
```

## Gotchas
- FLIRT `.mat` is **not** interchangeable with ANTs/ITK without `c3d_affine_tool -fsl2ras` (see `transforms.md`).
- Always `--interp=nn` / `-interp nearestneighbour` for label and mask resampling.
- Run `fnirt` on the **whole-head** image (with `--aff` from brain-extracted FLIRT) per FSL's standard recipe; the configs assume this.
