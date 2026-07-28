---
name: registration
description: >
  Perform medical/neuroimaging image registration by selecting and invoking the
  right pre-installed Neurodesk tool (ANTs, FSL, AFNI, FreeSurfer, greedy, NiftyReg,
  elastix, c3d) rather than reimplementing registration in Python. Use whenever the
  user wants to align, register, normalize, warp, resample, or spatially transform
  images — rigid/affine/nonlinear registration, registering to a template/atlas
  (MNI), within- or cross-subject alignment, EPI-to-anatomical (BBR/epi_reg),
  longitudinal registration, multimodal (T1↔T2↔CT) alignment, or applying/
  composing/inverting transforms. Trigger on "register", "align these scans", "warp
  to MNI", "normalize to template", "coregister", "apply this transform", "spatial
  normalization", "antsRegistration", "FLIRT/FNIRT", "SyN", or any task where two
  images must be brought into the same space. ALWAYS prefer loading a Neurodesk
  module and calling a validated tool over writing custom registration code.
---

# Image Registration (Neurodesk, tool-first)

Bring images into spatial correspondence using the validated registration software already shipped in Neurodesk. The job of this skill is to pick the correct tool for the problem and drive it from the command line — **not** to reimplement registration math in Python.

## Core principle: do not reimplement registration

Image registration is a mature, heavily validated field. Every tool below has had thousands of person-years of testing on real clinical and research data, with carefully tuned optimizers, multi-resolution schedules, and metric implementations. A hand-rolled scipy/numpy affine fit or a from-scratch mutual-information optimizer will be slower, less robust, and almost certainly wrong at the boundaries (interpolation, intensity normalization, masking, convergence). It also throws away interoperability: downstream tools expect transforms in ANTs/ITK or FSL/FLIRT formats, not a bespoke matrix.

**Therefore: load a module and call a tool first.** Python is for orchestration, parsing, and header bookkeeping — never for the registration itself (see "When Python is acceptable"). If you find yourself about to write an optimization loop over image intensities, stop and pick a tool from the table below. **This holds even when the user explicitly asks for a scipy/numpy/scikit-image alignment**: treat that as a request to *register these images*, satisfy it with the right tool, and offer a thin Python wrapper only for batching — do not hand-write the alignment to match the literal phrasing.

## Step 0 — Discover and load the tool

Neurodesk exposes every package as an Lmod module. Discover and load before doing anything else.

**Shell / agent (default):**
```bash
ml avail                      # list installed containers/modules
module load ants/2.6.0        # or: ml ants/2.6.0
module load fsl/6.0.7.16
antsRegistration --version    # confirm the binary is on PATH
```

**Jupyter / notebook context** (Neurodesk's Python `module` helper):
```python
import module
await module.load('ants/2.6.0')
await module.load('fsl/6.0.7.16')
await module.list()
```

Pin explicit versions for reproducibility, but treat the version numbers shown throughout this skill as **illustrative** — discover the versions actually installed with `ml avail` rather than assuming a specific one exists. Confirm the binary is on PATH after loading (`command -v` / `--version`). If a needed tool is missing, say so and suggest `ml avail` / an alternative rather than substituting Python. For GPU-accelerated binaries (e.g. NiftyReg CUDA, FSL eddy_cuda), set `export neurodesk_singularity_opts='--nv'` before invoking.

## Step 1 — Classify the registration problem

Four axes determine the tool and its settings. Establish all four before choosing.

| Axis | Options | Why it matters |
|------|---------|----------------|
| **Transform model** | rigid (6 DOF) · affine (12 DOF) · nonlinear/deformable (SyN, FFD/B-spline, FNIRT, Qwarp, greedy diffeo) | Determines tool capability and runtime |
| **Modality match** | intra-modal (same contrast) · inter-modal / multimodal (T1↔T2, EPI↔T1, CT↔MR, PET↔MR) | **Sets the similarity metric** (see below) |
| **Subject relationship** | intra-subject (motion, longitudinal, cross-modal in one subject) · inter-subject (to template/atlas/MNI) | Intra-subject usually rigid/affine; inter-subject usually needs nonlinear |
| **Special structure** | EPI distortion · surface-based · DWI · whole-slide/2D histology · lesion/abnormality present | May require a dedicated path (epi_reg/BBR, MSM, mrregister, masking) |

**Metric ↔ modality rule (the most common mistake):**
- *Same contrast* (e.g. T1→T1, longitudinal T1): cross-correlation (`CC`/`NCC`) or mean-squares (`MeanSquares`/`MSQ`). Highest sensitivity when intensities are comparable.
- *Different contrast* (T1↔T2, EPI↔T1, CT↔MR, PET↔MR): mutual information (`MI`/`Mattes`) or normalized MI. Never use mean-squares across modalities.
- *EPI↔T1 specifically*: prefer a boundary-based cost (FSL `epi_reg`/BBR or FreeSurfer `bbregister`) — it exploits the WM/GM boundary and beats plain MI for this case.

## Step 2 — Select the tool

Pick from this table, then open the matching reference file for the exact, copy-pasteable command.

| Problem | Recommended tool | Module | Reference |
|---------|-----------------|--------|-----------|
| Inter-subject **nonlinear** to template (MNI), general purpose | `antsRegistrationSyN[Quick].sh` (SyN) | `ants` | `references/ants.md` |
| Fully-custom multi-stage rigid→affine→SyN | `antsRegistration` | `ants` | `references/ants.md` |
| Affine/linear, fast, classic | FSL `flirt` | `fsl` | `references/fsl.md` |
| Nonlinear FFD after affine | FSL `fnirt` (+`flirt` init) | `fsl` | `references/fsl.md` |
| **EPI→T1** with fieldmap/BBR | FSL `epi_reg` / `bbregister` | `fsl`/`freesurfer` | `references/fsl.md`, `references/freesurfer.md` |
| Robust within-subject / longitudinal rigid | FreeSurfer `mri_robust_register` | `freesurfer` | `references/freesurfer.md` |
| BOLD/anat coregistration, EPI alignment | AFNI `align_epi_anat.py`, `3dAllineate` | `afni` | `references/afni.md` |
| Nonlinear warp, AFNI ecosystem | AFNI `3dQwarp` | `afni` | `references/afni.md` |
| Very fast affine + diffeomorphic (large data, GPU-friendly) | `greedy` | `itksnap` | `references/others.md` |
| Block-matching affine + B-spline FFD | NiftyReg `reg_aladin`, `reg_f3d` | `niftyreg` | `references/others.md` |
| Highly configurable parameter-file registration | `elastix` / `transformix` | `elastix` | `references/others.md` |
| Surface-based cortical alignment | FreeSurfer `mris_register` / Workbench MSM | `freesurfer`/`connectomeworkbench` | `references/freesurfer.md` |
| DWI/multi-tissue registration | MRtrix `mrregister` | `mrtrix3` | `references/others.md` |
| Affine matrix conversion / resampling glue | `c3d` / `c3d_affine_tool` | `convert3d` | `references/transforms.md` |

Where several tools fit, present the relevant options and their trade-offs (speed, accuracy, input/template needs, licensing) and let the user choose, rather than silently picking one. Offer a recommendation when asked or when context makes the choice clear.

**Sensible defaults when the user wants a recommendation:**
- Inter-subject to MNI: `antsRegistrationSyNQuick.sh -d 3 -f MNI -m moving -o out_` (quick) or the non-Quick version for publication-quality.
- Linear-only, fast: FSL `flirt`.
- Within-subject longitudinal: `mri_robust_register` (handles intensity drift, is symmetric/unbiased).

## Step 3 — Wrap it in a reproducible script and run

Do not run heavy registration commands ad hoc in the shell. Write a reproducible, named script — `analysis_<NN>_<description>.sh` (e.g. `analysis_02_t1_to_mni.sh`) — containing `set -euo pipefail`, the explicit pinned `module load` lines, `mkdir -p` for outputs/logs, the registration command from the reference file, and output existence checks (`test -s`). Keep the script as the record of exactly what was run.

Inside that script, always:
1. Inspect inputs first (`fslhd` / `c3d -info` / `PrintHeader`) — confirm dimensions, voxel size, and orientation agree with expectations; mismatched orientation is the #1 cause of "registration failed".
2. Consider a **brain mask / skull-strip** before inter-subject or cross-modal registration — extracranial tissue derails metrics. (`bet`, `antsBrainExtraction.sh`, `mri_synthstrip`, `hd-bet`.)
3. Initialize sensibly (center-of-mass or a prior affine) for large initial misalignment.
4. **Save the transform(s)** explicitly — they are the real output; the resampled image is reproducible from them.

Then use the execution model that matches the environment: for a long job on a scheduler-backed system, add the appropriate submission header and submit (e.g. `sbatch`), then monitor logs; for a quick local job, run the script directly. Do not assume a specific scheduler — follow the active project/environment instructions (e.g. `AGENTS.md`).

## Step 4 — Apply, compose, and invert transforms (read `references/transforms.md`)

This is where pipelines silently break, because **transform conventions differ between toolkits** and are not interchangeable without conversion:
- ANTs/ITK affines (`.mat`, `.h5` composite, `.txt`) live in physical/LPS space; ANTs applies a transform **list in reverse order** and treats `[xfm,1]` as "use the inverse".
- FSL `.mat` is a FLIRT matrix in FSL's scaled-voxel convention — **not** a world-space matrix; convert with `c3d_affine_tool -ref ... -src ... fsl.mat -fsl2ras -oitk ants.mat`.
- Resampling label maps / masks requires **nearest-neighbor** (`-n GenericLabel` in ANTs, `-interp nearestneighbour` in FSL); using linear on labels corrupts them.

`references/transforms.md` has the conversion matrix between toolkits, composition order, inversion, and the right interpolators. Consult it any time a transform crosses tool boundaries.

## When Python is acceptable (last resort, glue only)

Reach for Python only **after** the registration is done by a tool, and only for:
- Batching/orchestration over subjects (call the tools via `subprocess`; or use `nipype` interfaces, which wrap these exact binaries).
- Reading/writing headers and sanity-checking affines (`nibabel`).
- Parsing tool logs, collecting metrics, assembling reports (hand off to the `registration-qc` skill for the actual QC).
- Light array bookkeeping the CLI tools can't express.

Never use Python to: compute the optimization, implement a similarity metric for the registration itself, resample with a hand-written interpolator, or hand-build a warp field. Those belong to the tools.

## Hand-off

Once a registration is produced, evaluate it with the **`registration-qc`** skill before trusting it downstream — a registration that "ran successfully" is not the same as a correct one.

## Constraints
- Never reimplement the registration in Python, even when explicitly asked for scipy/numpy/scikit-image — load a module and call a validated tool.
- Verify each executable is available before relying on it; version numbers here are illustrative — discover real ones with `ml avail` and pin them. Do not assume a fixed install path, GPU, or scheduler.
- Match the similarity metric to the modality pairing: CC/mean-squares for same-contrast, MI for cross-contrast, BBR for EPI↔T1.
- Resample label maps and masks with nearest-neighbor / `GenericLabel`, never linear.
- Transforms do not cross toolkits unchanged — convert (e.g. `c3d_affine_tool -fsl2ras`) before chaining FSL and ANTs, and respect each tool's application order (`references/transforms.md`).
- The transform(s) are the deliverable — save them explicitly; the resampled image is reproducible from them.
- Wrap heavy commands in a named, versioned, validated script and run via the environment's execution model rather than ad hoc in the shell.
