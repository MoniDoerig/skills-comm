# FreeSurfer registration reference

Module: `module load freesurfer/7.3.2`. Needs `SUBJECTS_DIR` and a license. Key tools: `mri_robust_register` (robust rigid, longitudinal), `mri_coreg` + `bbregister` (EPI/BOLD↔T1 boundary-based), `mri_vol2vol` (apply), `mri_synthstrip` (skull-strip), `mris_register` / `mri_surf2surf` (surface), `mri_synthmorph` (learning-based registration).

## When to use FreeSurfer
- **Robust within-subject / longitudinal** rigid registration with intensity-drift handling (`mri_robust_register`) — symmetric and unbiased, ideal for serial scans.
- **Boundary-based** EPI↔structural (`bbregister`) — exploits the WM surface, the most accurate functional-to-anatomical method.
- Surface-based cross-subject cortical alignment.

## Robust rigid / longitudinal: `mri_robust_register`
```bash
mri_robust_register --mov tp2.nii.gz --dst tp1.nii.gz \
  --lta tp2_to_tp1.lta --mapmov tp2_in_tp1.nii.gz \
  --satit                       # auto sensitivity; add --iscale for intensity scaling
```
For an unbiased midpoint between two timepoints (recommended for longitudinal studies) use `mri_robust_template`.

## BOLD/EPI → T1 (boundary-based): `bbregister`
Requires a recon-all'd subject (uses its WM surface):
```bash
bbregister --s sub01 --mov epi_example.nii.gz --reg epi2anat.lta --bold --init-coreg
```
`--init-coreg` runs `mri_coreg` for initialization; `--t2`/`--t1` selects contrast. Output `.lta` is FreeSurfer's transform format.

## Apply a transform: `mri_vol2vol`
```bash
mri_vol2vol --mov moving.nii.gz --targ target.nii.gz \
  --lta moving2target.lta --o moving_in_target.nii.gz --nearest   # --nearest for labels
```

## SynthMorph / SynthStrip (modern, contrast-agnostic)
```bash
mri_synthstrip -i T1.nii.gz -o T1_brain.nii.gz             # fast robust skull-strip, any contrast
mri_synthmorph -m affine moving.nii.gz fixed.nii.gz -o warped.nii.gz -t xfm.lta   # deep-learning registration
```
SynthMorph is useful when classic intensity methods struggle (unusual contrast, large deformation) and is fast on CPU.

## Surface-based cortical registration
After `recon-all`, cross-subject surface alignment uses `?h.sphere.reg`; resample data between subjects/atlases with:
```bash
mri_surf2surf --srcsubject sub01 --trgsubject fsaverage \
  --hemi lh --sval lh.thickness --tval lh.thickness.fsaverage.mgh
```
For multimodal surface matching (HCP-style) use Connectome Workbench MSM (`connectomeworkbench` module).

## Gotchas
- `.lta` is FreeSurfer-native; convert to other formats with `lta_convert` (`--outitk`, `--outfsl`, `--outmni`) when crossing toolkits.
- FreeSurfer conforms volumes to 256³ 1mm — register in the space you intend; use `--lta` (not `--reg`) for newer, header-aware transforms.
