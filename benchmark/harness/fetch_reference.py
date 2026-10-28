#!/usr/bin/env python3
"""Fetch a task's grader-side reference NIfTIs into its pack/reference/.

Policy: code on GitHub, reference data on the Hugging Face Hub. This runs in the GRADING plane
only — never in the plane where the agent produces its answer, so the ground truth is never
exposed to the model.

Reads run_manifest.json for the task's ref_dir + reference_files and pulls each from the reference
dataset repo at the pinned revision, so a grading run scores against an exact, named reference set.

Access to the dataset is gated, which is what keeps the reference out of the execution plane: the
grading job supplies a read token via the HF_TOKEN environment variable, and the plane where the
agent works has none. Idempotent — files already present are left untouched.

    python fetch_reference.py --task clinical-wmh-segmentation
    python fetch_reference.py --task structural-brain-extraction --subject sub-0004

A task whose ref_dir carries {subject} keeps one reference directory per subject and needs
--subject; the manifest lists which subjects it has.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download


def fetch(task_id, manifest_path, graders_root=None, force=False, revision=None,
          subject=None):
    manifest_path = Path(manifest_path)
    m = json.load(open(manifest_path))
    if task_id not in m["tasks"]:
        raise SystemExit(f"ERROR: task '{task_id}' not in {manifest_path}")
    spec = m["tasks"][task_id]
    root = Path(graders_root).resolve() if graders_root else manifest_path.resolve().parent.parent
    defaults = m["defaults"]
    repo_id = defaults["reference_repo"]
    repo_type = defaults.get("reference_repo_type", "dataset")
    # A task may pin its own revision. The per-subject references were uploaded in a
    # later commit than the single-subject ones, and those still resolve at the older
    # pin, so one default for the whole manifest would move references nobody rebuilt.
    rev = revision or spec.get("reference_revision") or defaults.get("reference_revision")
    ref_dir = spec["ref_dir"]                        # e.g. clinical_gt/clinical-wmh-segmentation
    # A per-subject task keeps one reference directory per subject, so the subject has to
    # be named. It is checked against the manifest rather than interpolated blindly: a
    # typo would otherwise come back as a confusing 404 from the Hub.
    if "{subject}" in ref_dir:
        allowed = spec.get("subjects") or []
        if subject is None:
            raise SystemExit(
                f"ERROR: '{task_id}' is graded per subject; pass --subject.\n"
                f"Available: {', '.join(allowed) if allowed else '(none listed)'}")
        if allowed and subject not in allowed:
            raise SystemExit(f"ERROR: '{subject}' is not a subject of '{task_id}'.\n"
                             f"Available: {', '.join(allowed)}")
        ref_dir = ref_dir.replace("{subject}", subject)
    elif subject:
        raise SystemExit(f"ERROR: '{task_id}' has a single reference; --subject does not "
                         "apply to it")

    dest = root / spec["pack_dir"] / "reference"
    dest.mkdir(parents=True, exist_ok=True)

    for fname in spec["reference_files"]:
        local = dest / fname
        if local.exists() and not force:
            print(f"  [skip] {fname} already present")
            continue
        remote = f"{ref_dir}/{fname}"
        print(f"  [fetch] {repo_id}@{rev or 'main'}:{remote} -> {local}")
        try:
            got = hf_hub_download(repo_id=repo_id, repo_type=repo_type, filename=remote,
                                  revision=rev, force_download=force)
        except Exception as e:
            hint = ""
            if "401" in str(e) or "403" in str(e) or "gated" in str(e).lower():
                hint = ("\nThe dataset is gated. Set HF_TOKEN to a token whose account has been "
                        "granted\naccess, then retry. Request access on the dataset page.")
            raise SystemExit(f"ERROR: could not fetch {remote} from {repo_id}\n"
                             f"{type(e).__name__}: {e}{hint}")
        # Copy out of the shared cache so the pack owns its reference and a later cache sweep
        # cannot empty it mid-run.
        shutil.copyfile(got, local)
    # The rubric is code, not reference data: thresholds stay in the repo so the grading
    # criteria can be read without access to the gated dataset, and so they version with
    # the scorer that applies them. A per-subject task keeps one per subject; the chosen
    # one is placed where the scorer looks.
    if subject:
        src = root / spec["pack_dir"] / "rubrics" / f"{subject}.json"
        if not src.is_file():
            raise SystemExit(f"ERROR: no rubric for {subject} at {src}")
        shutil.copyfile(src, dest / "rubric.json")
        print(f"  [rubric] {src.name} -> {dest / 'rubric.json'}")

    print(f"reference ready: {dest}")
    return dest


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch a task's reference into its grader pack.")
    ap.add_argument("--task", required=True)
    ap.add_argument("--manifest", default=str(Path(__file__).parent / "run_manifest.json"))
    ap.add_argument("--graders-root")
    ap.add_argument("--force", action="store_true", help="re-fetch even if present")
    ap.add_argument("--revision", help="override the revision pinned in the manifest")
    ap.add_argument("--subject", help="which subject's reference to fetch, for the tasks "
                                      "that are graded per subject")
    a = ap.parse_args(argv)
    fetch(a.task, a.manifest, a.graders_root, a.force, a.revision, a.subject)
    return 0


if __name__ == "__main__":
    sys.exit(main())
