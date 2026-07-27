# Other registration tools (greedy, NiftyReg, elastix, MRtrix, MINC)

## greedy — fast affine + diffeomorphic
Module: ships inside the `itksnap` container (`module load itksnap`), since greedy is developed alongside ITK-SNAP. After loading, confirm the binary is on PATH with `which greedy`; some Neurodesk releases also expose it standalone (check `ml avail | grep -i greedy`). Very fast, ITK-based, transforms are ANTs/ITK-compatible.

```bash
# Affine (multimodal -> use NMI; same modality -> SSD or NCC)
greedy -d 3 -a -i fixed.nii.gz moving.nii.gz \
  -o affine.mat -ia-image-centers -m NMI -n 100x50x10

# Deformable, initialized by the affine
greedy -d 3 -i fixed.nii.gz moving.nii.gz \
  -it affine.mat -o warp.nii.gz -m NCC 2x2x2 -n 100x50x10 -s 3mm 1mm

# Apply (labels -> LABEL interp)
greedy -d 3 -rf fixed.nii.gz \
  -rm moving.nii.gz moving_warped.nii.gz \
  -ri LINEAR -r warp.nii.gz affine.mat
```
Use when you need ANTs-quality diffeomorphic warps but much faster (large cohorts, iterative template building). `-m`: `SSD`, `NCC <radius>`, `MI`, `NMI`.

## NiftyReg — block-matching affine + B-spline FFD (CPU/GPU)
Module: `module load niftyreg`.
```bash
reg_aladin -ref fixed.nii.gz -flo moving.nii.gz \
  -aff affine.txt -res moving_affine.nii.gz          # robust affine (outlier rejection)
reg_f3d -ref fixed.nii.gz -flo moving.nii.gz \
  -aff affine.txt -cpp cpp.nii.gz -res moving_nl.nii.gz   # nonlinear FFD
reg_resample -ref fixed.nii.gz -flo label.nii.gz \
  -trans cpp.nii.gz -res label_warped.nii.gz -inter 0    # -inter 0 = NN for labels
```
GPU: build/binaries with CUDA; set `export neurodesk_singularity_opts='--nv'`. `-cpp` stores the control-point grid (the transform); `reg_transform` composes/inverts.

## elastix — parameter-file-driven registration
Module: `module load elastix`. Fully reproducible via text parameter files (rigid/affine/bspline presets from the elastix model zoo).
```bash
elastix -f fixed.nii.gz -m moving.nii.gz \
  -p Par_rigid.txt -p Par_affine.txt -p Par_bspline.txt -out outdir/
transformix -in label.nii.gz -tp outdir/TransformParameters.2.txt -out lbl_out/
```
For labels set `(FinalBSplineInterpolationOrder 0)` in the parameter file (NN). elastix is the choice when you need exact, shareable parameter control (e.g. reproducing a published protocol).

## MRtrix — `mrregister` (diffusion / multi-tissue)
Module: `module load mrtrix3`.
```bash
mrregister moving.mif fixed.mif -type rigid_affine_nonlinear \
  -rigid rigid.txt -affine affine.txt -nl_warp warp_m2f.mif warp_f2m.mif
mrtransform moving.mif -warp warp_m2f.mif moving_warped.mif
```
Use for FOD-based registration in fixel/connectivity pipelines, where intensity registration of scalar maps is inappropriate.

## MINC — `bestlinreg` / `mincANTS` / `nlfit`
Module: `module load minctoolsv2` (minc-toolkit-v2). Relevant for MINC-format pipelines and the MNI/BIC ecosystem (e.g. CIVET-style). Convert to/from NIfTI with `mnc2nii`/`nii2mnc` and prefer one of the tools above unless you specifically need the MINC stack.

## Choosing among these
- Need ANTs-quality warps but faster, ITK-compatible output → **greedy**.
- Want robust linear with outlier rejection or GPU FFD → **NiftyReg**.
- Need an exactly reproducible, shareable protocol → **elastix**.
- Registering diffusion FODs → **mrregister**.
