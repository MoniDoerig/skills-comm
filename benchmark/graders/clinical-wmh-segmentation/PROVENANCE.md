# Provenance — how this grader pack was built

Frozen reference for **WMH Segmentation Challenge 2017, Amsterdam/GE3T/100** (clinical FLAIR, native
FLAIR space). White-matter hyperintensities of presumed vascular origin (dementia / small-vessel axis).

## Ground truth

`lesion_mask.nii.gz` is the **primary expert WMH mask** (observers O1/O2 per the challenge's reference
standard [1], STRIVE-compliant), binarised to WMH (label 1; the dataset's label 2 "other pathology" is not
present for this subject). Native FLAIR space, 6.27 cm³, **115 foci**.

## Thresholds are data-derived from inter-rater agreement

The WMH Challenge [1] ships two additional raters (O3, O4) on the training subjects. Scoring each
against the primary gives a *measured* envelope rather than a literature guess:

| rater vs primary | Dice | lesion-wise F1 | volume error |
|---|---|---|---|
| O3 | 0.774 | 0.794 | 13 % |
| O4 | 0.792 | 0.876 | 4 % |

Envelope: **full marks = mean rater-vs-primary** (as good as another expert), **pass = a margin below
the worst rater**:

| metric | full | pass |
|---|---|---|
| Dice | 0.783 | 0.574 |
| lesion-wise F1 | 0.835 | 0.544 |
| abs. volume error | 9 % | 48.6 % |

Weights: Dice 0.40, lesion-wise F1 0.40, volume error 0.20 — F1 raised to parity with Dice because WMH
are many small foci where detection, not just boundary overlap, is the point.

## Validation

Against the pack: primary self → `indistinguishable` (q100); **O4 → `indistinguishable`** and **O3 →
`acceptable` (q90)** — the two real raters land at "as good as another expert"; dilate the mask by 2
voxels → `marginal` (Dice 0.24, +636 % volume — tiny lesions are unforgiving); erode by 1 →
`unacceptable`; empty → `invalid`.

## Data access (open, agent-runnable)

Images: DataverseNL DOI `10.34894/AECRSD`, open Dataverse access API (`curl .../api/access/datafile/<id>`,
no auth/DUA). FLAIR file id 325669, T1 id 325515 for this subject. The expert masks (primary id 325503,
O3 326449, O4 326442) are used to build this pack and live on OSF — never given to the agent.

## Caveats

- **n = 1 subject.** A new subject means a new pack; but the inter-rater envelope generalises the idea.
- **FLAIR is anisotropic** (~1.2 × 1.0 × 3.0 mm, 2D multi-slice) — realistic clinical WMH data.
- **Two extra raters, not a full distribution** — the envelope uses O3/O4 vs primary; more raters would
  tighten it. Still far better grounded than a fixed literature threshold.
- License CC-BY-NC-4.0 (non-commercial), fine for a benchmark.

## References

Thresholds here are **data-derived** (O3/O4 vs primary), not a literature prior — this reference is
*dataset / protocol provenance*, crediting the source of the reference standard and the multi-observer
masks the envelope is built on.

1. H. J. Kuijf, J. M. Biesbroek, J. de Bresser, et al., "Standardized Assessment of Automatic
   Segmentation of White Matter Hyperintensities and Results of the WMH Segmentation Challenge,"
   *IEEE Trans. Med. Imaging* 38(11):2556–2568, 2019. doi:10.1109/TMI.2019.2905770.
