# Reference data (fetched from OSF, not stored in git)

Code on GitHub, data on OSF.

- **OSF project:** zjqey — https://osf.io/zjqey/
- **Path:** `ground_truth/diffusion_gt/diffusion-brain-mask/`
- **Files:**
  - `consensus_mask.nii.gz` — STAPLE consensus of dwi2mask + SynthStrip + HD-BET +
    AFNI 3dSkullStrip, on the diffusion grid of ds001226 sub-CON02 ses-preop acq-AP
  - `consensus_zones.nii.gz` — 0 = background, 1 = margin, 2 = core

Fetch before grading:

    osf -p zjqey fetch osfstorage/ground_truth/diffusion_gt/diffusion-brain-mask/consensus_mask.nii.gz consensus_mask.nii.gz
    osf -p zjqey fetch osfstorage/ground_truth/diffusion_gt/diffusion-brain-mask/consensus_zones.nii.gz consensus_zones.nii.gz
