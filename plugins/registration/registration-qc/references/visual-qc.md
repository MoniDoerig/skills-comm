# Visual QC — generating the diagnostic images with tools

Render visuals with validated tools; do not draw them with custom matplotlib unless assembling a final multi-panel figure from already-generated PNGs. Load `module load ants/2.6.0 fsl/6.0.7.16 afni convert3d`. Each view below answers a specific question.

## Edge / contour overlay (most informative single view)
Boundaries of one image drawn over the other — exposes exactly where structures fail to line up.

```bash
# FSL: red fixed-image outline on the warped-moving image
slices warped_moving.nii.gz fixed.nii.gz -o edge_overlay.png
# fsleyes render (headless) with an edge-mode overlay:
fsleyes render --outfile edge.png \
  warped_moving.nii.gz \
  fixed.nii.gz -ot edge -lw 2 -cm red
```
AFNI equivalent: `@chauffeur_afni ... -edgy_ulay` draws ulay edges over the olay.

**Read:** edges should hug the corresponding boundaries (cortical ribbon, ventricles, subcortical structures). Systematic offsets or a region where edges sit inside/outside the tissue = misregistration there.

## Checkerboard
Alternating tiles of fixed and warped — structures must run continuously across tile borders.

```bash
# Primary (reliable): fsleyes renders a checkerboard by alternating the two volumes.
# Easiest robust route in practice is the ITK-SNAP / 3D Slicer interactive checkerboard,
# or fsleyes with the two volumes loaded and the top one in checkerboard alpha mode:
fsleyes render --outfile checker.png \
  fixed.nii.gz warped_moving.nii.gz -dr 0 1 -a 50

# c3d can also build a checkerboard volume (then screenshot/mosaic it), but its syntax
# is fiddly — prefer the viewer routes above unless scripting a headless batch:
c3d fixed.nii.gz warped_moving.nii.gz -checkerboard 8x8x8 -o checker.nii.gz
```

**Read:** vessels, sulci, and ventricle walls should be continuous across the checker boundaries; a "brick wall" discontinuity at every tile edge = misalignment.

## Difference / absolute-difference image
Residual anatomical structure after subtraction indicates leftover misregistration (for same-modal pairs).

```bash
fslmaths fixed.nii.gz -sub warped_moving.nii.gz -abs absdiff.nii.gz
fslstats absdiff.nii.gz -m -p 95          # mean and 95th pct of residual
```
**Read:** for same-contrast registration a good result leaves mostly noise; visible edges/ghosts of anatomy = residual misalignment. (Less meaningful across modalities.)

## Jacobian heatmap (localizes deformation problems)
Overlay the Jacobian determinant (from `metrics.md`) with a diverging colormap centered at 1.

```bash
fsleyes render --outfile jac_map.png \
  fixed.nii.gz \
  jac.nii.gz -cm brain_colours_diverging -dr 0 2 -a 60
```
**Read:** smooth, gentle variation around 1 is healthy. Sharp hotspots, values driven to 0, or any negative region (folding) pinpoint where the warp broke — name that region in the report.

## Mosaic / lightbox (for the report and batch review)
Multi-slice screenshots that a human can scan quickly.

```bash
# ANTs tiled mosaic with an RGB overlay:
ConvertScalarImageToRGB 3 warped_moving.nii.gz rgb.nii.gz none hot
CreateTiledMosaic -i fixed.nii.gz -r rgb.nii.gz -o mosaic.png \
  -a 0.35 -t -1x-1 -d 2 -p mask -s [4,mask-low,mask-high]

# FSL: one PNG row per image, plus a browsable HTML index across many subjects:
slicesdir -o fixed_*.nii.gz warped_*.nii.gz      # creates slicesdir/index.html

# AFNI: publication-style multi-slice montage with overlay edges:
@chauffeur_afni -ulay fixed.nii.gz -olay warped_moving.nii.gz \
  -prefix qc -montx 5 -monty 3 -set_dicom_xyz 0 0 0 -opacity 5 -edgy_ulay
```

**Use:** embed the mosaic in the QC report. For a cohort, `slicesdir` gives one HTML page to triage everyone and mark the failures for human review.

## Which views for which case
- Cross-subject nonlinear to MNI: **edge overlay + Jacobian heatmap + mosaic** (folding and regional accuracy are the risks).
- Within-subject rigid (EPI↔T1, longitudinal): **edge overlay + checkerboard** (small shifts/rotations are the risk).
- Same-modal longitudinal: add the **difference image** (sensitive to subtle residual shift).

Visuals are what move confidence up (corroboration) and what resolve BORDERLINE verdicts — always generate at least the edge overlay and a mosaic.
