# Reference data (fetched from OSF, not stored in git)

Code on GitHub, data on OSF.

- **OSF project:** zjqey — https://osf.io/zjqey/
- **Path:** `ground_truth/fmri_gt/functional-bold-to-mni/`
- **Files** (both on the MNI152NLin2009cAsym res-01 grid, 193x229x193 at 1 mm):
  - `template_T1w.nii.gz` — the template, for in-brain mutual information
  - `template_brain_mask.nii.gz` — the region NMI is measured in, and the placement reference

Fetch before grading:

    for f in template_T1w template_brain_mask; do
      osf -p zjqey fetch osfstorage/ground_truth/fmri_gt/functional-bold-to-mni/$f.nii.gz $f.nii.gz
    done

These are unmodified TemplateFlow files (tpl-MNI152NLin2009cAsym), redistributable under the
template's own licence; cite Fonov et al. 2011 and TemplateFlow with any use.
