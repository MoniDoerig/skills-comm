# Provenance — how this grader pack was calibrated

Frozen output of a one-time calibration on **ds002790 `sub-0006`**, T1w at 1 mm, registered to
**MNI152NLin2009cAsym** (TemplateFlow, `res-01`, 193 × 229 × 193 at 1 mm). Not re-derived at
grade time.

## What is graded, and why it is not the warped image

A registration is a spatial transform. The obvious thing to grade — how much the warped T1w
resembles the template — turns out to be nearly useless for separating a good registration from a
mediocre one: correlation is dominated by gross head position and is largely saturated once *any*
affine has been applied. On this subject, in-brain correlation is 0.57 for an affine and 0.78–0.84
for a nonlinear warp, but the tissue that actually moved tells a much sharper story.

So the task hands the agent the subject's **tissue segmentation** alongside the T1w and asks for
it to be carried through the same transform with nearest-neighbour interpolation. The grader then
measures **where the tissue landed**. This is label propagation, the standard way registration is
evaluated, and it is tool-agnostic: every registration package can apply its own transform to a
second image.

The segmentation is an agent **input**, not a reference.

## The reference is the template, not another tool

Grading against fMRIPrep's MNI output — which is what the earlier version of this task did —
measures agreement with one implementation of one pipeline, not registration quality. Instead the
reference is the **template's own tissue priors** (`label-{GM,WM,CSF}_probseg`), which state where
each tissue belongs in MNI space independently of any registration software.

A population prior is not a per-subject truth, so no absolute Dice threshold would be defensible.
The scale is therefore relative and data-derived:

- **full marks** = the median of four accepted nonlinear registrations on this subject;
- **zero credit** = the median of three affine-only registrations.

The score reads directly as *"how far between a 12-DOF affine and a typical nonlinear warp is
this?"* Anchoring the floor on the affine rather than on a slack multiple of the accepted spread
matters here, because the accepted tools agree closely — WM Dice within 0.065 of each other — and
a slack-based floor would sit inside that spread and make scoring brittle.

## Label convention

The supplied segmentation uses **1 = GM, 2 = WM, 3 = CSF**. This was verified from the data, not
assumed: mean T1w intensity per label is 156 k / 233 k / 82 k, and WM is the brightest tissue on a
T1w, which fixes the mapping. `rubric.json` carries it as `tissue_labels` so the scorer never
guesses.

The scorer additionally reports (never scores) `suspected_label_permutation` when some other
assignment of the same labels would score better — the signature of an agent that re-segmented
the image with a different convention instead of warping the file it was given. That turns a
confusing near-zero into an actionable one.

## The panel

Seven registrations, all from the raw T1w to the template, each emitting a warped T1w and a
propagated segmentation:

| tool | kind | WM Dice | GM Dice | in-brain corr | verdict |
|---|---|---|---|---|---|
| **ANTs SyN** (`antsRegistrationSyN.sh -t s`) | nonlinear | 0.855 | 0.787 | 0.826 | **reference** |
| **NiftyReg** (`reg_aladin` + `reg_f3d`) | nonlinear | 0.846 | 0.746 | 0.842 | **reference** |
| **fMRIPrep** (transform shipped with ds002790) | nonlinear | 0.840 | 0.761 | 0.784 | **reference** |
| **FSL** (`flirt` + `fnirt`) | nonlinear | 0.791 | 0.706 | 0.736 | **reference** |
| ANTs affine (`-t a`) | affine | 0.701 | 0.635 | 0.579 | candidate → unacceptable |
| FSL `flirt` 12 DOF | affine | 0.698 | 0.629 | 0.581 | candidate → unacceptable |
| NiftyReg `reg_aladin` | affine | 0.695 | 0.624 | 0.571 | candidate → unacceptable |

Three independent nonlinear families (ANTs, FSL, NiftyReg) plus fMRIPrep's shipped transform,
which is ANTs-based and therefore correlated with the SyN arm — it is included because it is the
answer a reader would expect to see, not because it adds independence.

**The separation is unambiguous**: every nonlinear arm sits at WM Dice ≥ 0.791, every affine arm
at ≤ 0.701, and the three affine implementations agree with each other to within 0.006. That
tight affine cluster is what makes it a trustworthy zero point.

FSL FNIRT is the weakest accepted arm (0.791, quality 61). It is run without a `--config`,
because the shipped configs are tuned for FSL's own MNI152 (MNI152NLin6Asym) and the reference
space here is MNI152NLin2009cAsym. Including it widens the accepted envelope and makes the task
*more* forgiving of an FSL-based answer, which is the right direction for fairness.

## Metrics and weights

| metric | weight | full marks | zero credit |
|---|---|---|---|
| WM Dice | 0.30 | 0.8429 | 0.6977 |
| GM Dice | 0.25 | 0.7536 | 0.6291 |
| brain Dice | 0.20 | 0.9772 | 0.9604 |
| in-brain correlation | 0.15 | 0.8049 | 0.5786 |
| CSF Dice | 0.10 | 0.3430 | 0.2552 |

WM carries the most weight because it is the most sensitive to nonlinear quality. CSF carries the
least: the template CSF prior at 0.5 is only 94.5 cm³, mostly ventricles, against 267 cm³ of
subject CSF, so the two definitions differ and Dice is capped low for everyone. It still moves in
the right direction (0.255 affine → 0.343 nonlinear) and is kept at low weight.

Image correlation is measured **inside the template brain mask**, so an agent that leaves the
skull on is not penalised for it.

## Gates

`warped_on_template_grid`, `dseg_on_template_grid`, `warped_finite_in_brain`, `valid_labels`,
`nonempty`, `brain_volume_plausible` (1270–2420 cm³), `brain_in_place` (propagated brain centre
of mass within 5 mm of the template's).

`warped_finite_in_brain` is deliberately not "no NaN anywhere": NiftyReg and some other
resamplers write NaN outside the field of view rather than zero, which is a convention, not a
defect. Non-finite values are zeroed on load and judged only where they matter — inside the brain.

## Validation

### Negative control

An agent that resamples onto the template grid without registering at all scores WM Dice 0.386
and is rejected by `brain_in_place`. This is the control that matters most, because the template
grid can be reached by resampling alone.

### Perturbing the best accepted registration

| perturbation | verdict | quality |
|---|---|---|
| self | indistinguishable | 100.0 |
| blur 4 mm (image only) | acceptable | 86.5 |
| shift 2 mm | marginal | 41.4 |
| shift 5 mm | **invalid** (`brain_in_place`) | 0 |
| shift 10 mm | **invalid** (`brain_in_place`) | 0 |
| empty segmentation | **invalid** | 0 |

Blurring the warped image only moves the correlation term, which is why it stays acceptable — the
propagated labels are untouched, and the labels are what carry the score.

### Malformed submissions

| submission | result |
|---|---|
| labels permuted (re-segmented, wrong convention) | marginal, with `suspected_label_permutation` naming the fix |
| binary mask instead of a segmentation | **invalid** (`valid_labels`) |
| segmentation on a different grid | **invalid** (`dseg_on_template_grid`) |

## Runtime

Not a barrier, which was worth checking before building the task: **ANTs SyN at 1 mm took 7
minutes** on 10 cores. FSL FNIRT was the slowest at 25 minutes, NiftyReg under 2. All fit inside a
45-minute agent budget, so the skill arm cannot be penalised for choosing a slower-but-better
tool.

## Reference data (on OSF)

`reference/template_*.nii.gz` are **not** in git — they belong on OSF (zjqey,
`ground_truth/structural_gt/structural-mni-registration/`). They are unmodified TemplateFlow
files, redistributable under the template's own licence. Fetch them before grading; see
`reference/README.md`.

## Departure from the earlier task definition

The pre-existing `structural-mni-registration` entry was manually graded, asked only for a warped
T1w, and named fMRIPrep's MNI output as the comparison. That grades agreement with one pipeline
rather than registration quality, and — as the numbers above show — the image-similarity metric it
implies barely separates an affine from a nonlinear warp.
