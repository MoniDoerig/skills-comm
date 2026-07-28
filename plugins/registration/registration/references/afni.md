# AFNI registration reference

Module: `module load afni/24.1.02` (or latest). Key tools: `3dAllineate` (linear/affine), `3dQwarp` (nonlinear), `align_epi_anat.py` (EPI↔anat orchestrator), `@auto_tlrc`/`@SSwarper` (template normalization), `3dNwarpApply`, `3dNwarpCat`, `3dresample`, `3dSkullStrip`.

## When to use AFNI
- EPI↔anatomical alignment in an AFNI/`afni_proc.py` pipeline.
- Nonlinear warping with `3dQwarp` (and `@SSwarper` for skull-strip + MNI warp in one step).

## Affine: `3dAllineate`
```bash
3dAllineate -base ref.nii.gz -source moving.nii.gz \
  -prefix moving_in_ref.nii.gz \
  -1Dmatrix_save moving2ref.aff12.1D \
  -cost lpa -warp shift_rotate_scale -interp linear -final wsinc5
```
- `-cost`: `ls` (least squares, same modality), `lpa`/`lpc` (local Pearson, robust for EPI↔T1 — `lpc` for T1↔EPI opposite contrast), `mi`/`nmi` (cross-modal).
- `-warp`: `shift_rotate` (rigid), `shift_rotate_scale`, `affine_general` (12-DOF).
- Matrix is a 12-parameter `.aff12.1D` row (AFNI convention).

## EPI ↔ anatomical: `align_epi_anat.py`
```bash
align_epi_anat.py -anat T1.nii.gz -epi epi.nii.gz \
  -epi_base 0 -anat2epi -epi2anat \
  -cost lpc -volreg on -tshift off
```
Handles obliquity, motion, and produces both directions; the standard choice inside `afni_proc.py`.

## Nonlinear: `3dQwarp`
```bash
3dQwarp -base ref.nii.gz -source affine_aligned.nii.gz \
  -prefix qwarp_out -iwarp -blur 0 3
```
`-iwarp` also writes the inverse warp. For full skull-strip + nonlinear MNI normalization in one call use `@SSwarper`:
```bash
@SSwarper -input T1.nii.gz -base MNI152_2009_template_SSW.nii.gz -subid sub01
```

## Apply / concatenate warps
```bash
3dNwarpApply -nwarp 'qwarp_out_WARP.nii.gz moving2ref.aff12.1D' \
  -source label.nii.gz -master ref.nii.gz -ainterp NN -prefix label_warped.nii.gz
3dNwarpCat -warp1 W1.nii.gz -warp2 W2.nii.gz -prefix Wcat.nii.gz
```
Use `-ainterp NN` for labels/masks. `3dNwarpApply` reads a **space-separated, quoted** warp chain applied right-to-left.

## Skull-strip
```bash
3dSkullStrip -input T1.nii.gz -prefix T1_brain.nii.gz
```

## Gotchas
- AFNI may carry an oblique transform in the header; check with `3dinfo -obliquity` and deoblique consistently (`3dWarp -deoblique` or let `align_epi_anat.py` handle it).
- AFNI affine `.aff12.1D` is its own format; convert via `cat_matvec` or resample with native AFNI tools rather than mixing toolkits.
