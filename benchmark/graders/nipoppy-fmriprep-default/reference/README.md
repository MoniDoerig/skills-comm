# Reference for `nipoppy-fmriprep-default`

Fetched from the gated dataset by `../../../harness/fetch_reference.py --task
nipoppy-fmriprep-default`; nothing here is committed.

| file | what it is |
|---|---|
| `expected_pairs.tsv` | the participant and session ids of every pair in the dataset, one per line, no header |
| `expected_command.txt` | the fMRIPrep command the reference study generates, with its paths masked, as a cross-check on the one the grader regenerates |

The pair list is derivable from the public dataset, so it is not an answer key in the
sense the other packs use. It is gated for consistency, and so that one place defines
what the dataset contained when the task was calibrated.
