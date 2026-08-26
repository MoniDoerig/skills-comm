# Reference data (fetched from OSF, not stored in git)

Code on GitHub, data on OSF.

- **OSF project:** zjqey — https://osf.io/zjqey/
- **Path:** `ground_truth/structural_gt/structural-mni-registration/`
- **Files** (all on the MNI152NLin2009cAsym res-01 grid, 193x229x193 at 1 mm):
  - `template_T1w.nii.gz` — the template, for in-brain image correlation
  - `template_brain_mask.nii.gz` — brain overlap and the correlation region
  - `template_probseg_GM.nii.gz`, `template_probseg_WM.nii.gz`, `template_probseg_CSF.nii.gz` —
    tissue priors, the reference for propagated-label overlap

Fetch before grading:

    for f in template_T1w template_brain_mask template_probseg_GM template_probseg_WM template_probseg_CSF; do
      osf -p zjqey fetch osfstorage/ground_truth/structural_gt/structural-mni-registration/$f.nii.gz $f.nii.gz
    done

These are unmodified TemplateFlow files (tpl-MNI152NLin2009cAsym), redistributable under the
template's own licence; cite Fonov et al. 2011 and TemplateFlow with any use.
