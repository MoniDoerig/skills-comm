# Transforms: conventions, conversion, composition, inversion

Transforms are the true output of registration. Getting them wrong — wrong format, wrong order, wrong interpolator — silently corrupts everything downstream. This file is the interop cheat-sheet.

## Format landscape

| Toolkit | Affine format | Nonlinear format | Coordinate space |
|---------|--------------|------------------|------------------|
| ANTs / ITK | `.mat` (ITK txt), `.h5` (composite) | displacement field `*Warp.nii.gz` | physical **LPS** |
| FSL | `.mat` (FLIRT 4×4) | warp field (`fnirt --fout`) or coef (`--cout`) | FSL **scaled-voxel** (not world) |
| AFNI | `.aff12.1D` (12 params/row) | `*_WARP.nii.gz` | physical (with possible obliquity) |
| FreeSurfer | `.lta` | `.m3z` / warp | header-aware (RAS/tkRAS) |
| greedy / NiftyReg / elastix | ITK `.mat` / `cpp.nii.gz` / `TransformParameters.txt` | ITK warp / control points | physical (ITK = LPS) |

**The trap:** an FSL `.mat` and an ANTs `.mat` are both "4×4 affines" but live in different coordinate conventions. Feeding one to the other's apply step produces a plausible-looking but wrong result. Always convert.

## Conversions (use `c3d_affine_tool`, module `convert3d`, and `lta_convert`)

```bash
# FSL FLIRT .mat  ->  ITK/ANTs .mat
c3d_affine_tool -ref ref.nii.gz -src moving.nii.gz \
  flirt.mat -fsl2ras -oitk ants_affine.mat

# ITK/ANTs .mat  ->  FSL FLIRT .mat
c3d_affine_tool -ref ref.nii.gz -src moving.nii.gz \
  -itk ants_affine.mat -ras2fsl -o flirt.mat

# FreeSurfer .lta  ->  others
lta_convert --inlta xfm.lta --outitk xfm_itk.txt   # also --outfsl, --outmni, --outreg
```
For nonlinear fields, convert the volume's intent/format with care; when in doubt, **resample with the toolkit that produced the warp** rather than porting the field.

## Composition order (the #1 logic bug)

Each toolkit has its own application order — internalize the one you're using:

- **ANTs `antsApplyTransforms -t A -t B`** applies the list **right-to-left**: B first, then A. To move subject→template list `Warp` then `Affine`. To invert the whole chain, reverse the list, invert each affine with `[aff.mat,1]`, and swap `Warp`↔`InverseWarp`.
- **FSL** concatenation `convert_xfm -concat B2C A2B` gives A→C (matrix product `B2C * A2B`). `applywarp -w` warps follow the field's own direction.
- **AFNI `3dNwarpApply -nwarp 'W A.aff12.1D'`** applies the quoted, space-separated chain **right-to-left** (affine first here because it's last).

When composing affine + nonlinear across stages, **collapse to one composite** where possible (`antsApplyTransforms -o [comp.nii.gz,1]`, `3dNwarpCat`, `reg_transform -comp`) and reuse it — fewer interpolations, fewer ordering mistakes.

## Inversion

| Toolkit | Invert affine | Invert nonlinear |
|---------|--------------|------------------|
| ANTs | `[aff.mat,1]` in the `-t` list | use the saved `*InverseWarp.nii.gz` (SyN is diffeomorphic) |
| FSL | `convert_xfm -inverse` | `invwarp -w warp -o invwarp -r ref` |
| AFNI | `cat_matvec mat -I` | `3dQwarp -iwarp` saves it; or `3dNwarpCat -iwarp` |
| greedy/NiftyReg | `-r ... ` with `,-1` / `reg_transform -invAff` | greedy `-wp`/inverse; NiftyReg `reg_transform -invNrr` |

For non-diffeomorphic warps (FNIRT, FFD) the numerical inverse is approximate; prefer tools that store an explicit inverse.

## Interpolation — choose by image type

| Image being resampled | Correct interpolator |
|-----------------------|---------------------|
| Continuous intensity (T1, EPI, fMRI stat map) | linear (`-n Linear` / `trilinear`); `wsinc5`/`BSpline` for final high-quality |
| Label map / parcellation / atlas | nearest-neighbor or `GenericLabel` (ANTs) — **never linear** |
| Binary mask | nearest-neighbor (then re-binarize if any smoothing slipped in) |
| Probability map (0–1) | linear |

Using linear on a label map blends label indices into meaningless intermediate integers — a silent, common, serious bug. `GenericLabel` (ANTs) is the safest for multi-label maps because it interpolates each label's membership and picks the argmax.

## Sanity checks before trusting a transform
```bash
PrintHeader moving.nii.gz          # ANTs: dims, spacing, direction
c3d ref.nii.gz -info               # quick header
fslhd image.nii.gz | grep -i form  # qform/sform codes
```
Mismatched orientation (LAS vs RAS), wrong qform/sform, or a moving/fixed swap explains the large majority of "the registration is garbage" reports — check headers first.
