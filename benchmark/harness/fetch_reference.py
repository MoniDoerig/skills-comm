#!/usr/bin/env python3
"""Fetch a task's grader-side reference NIfTIs into its pack/reference/.

Policy: code on GitHub, reference data on the Hugging Face Hub. This runs in the GRADING plane
only — never in the plane where the agent produces its answer, so the ground truth is never
exposed to the model.

Reads run_manifest.json for the task's ref_dir + reference_files and pulls each from the reference
dataset repo at the pinned revision, so a grading run scores against an exact, named reference set.
The repo is public: no token is required. Idempotent — files already present are left untouched.

    python fetch_reference.py --task clinical-wmh-segmentation
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download


def fetch(task_id, manifest_path, graders_root=None, force=False, revision=None):
    manifest_path = Path(manifest_path)
    m = json.load(open(manifest_path))
    if task_id not in m["tasks"]:
        raise SystemExit(f"ERROR: task '{task_id}' not in {manifest_path}")
    spec = m["tasks"][task_id]
    root = Path(graders_root).resolve() if graders_root else manifest_path.resolve().parent.parent
    defaults = m["defaults"]
    repo_id = defaults["reference_repo"]
    repo_type = defaults.get("reference_repo_type", "dataset")
    rev = revision or defaults.get("reference_revision")
    ref_dir = spec["ref_dir"]                        # e.g. clinical_gt/clinical-wmh-segmentation
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
            raise SystemExit(f"ERROR: could not fetch {remote} from {repo_id}\n"
                             f"{type(e).__name__}: {e}")
        # Copy out of the shared cache so the pack owns its reference and a later cache sweep
        # cannot empty it mid-run.
        shutil.copyfile(got, local)
    print(f"reference ready: {dest}")
    return dest


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch a task's reference into its grader pack.")
    ap.add_argument("--task", required=True)
    ap.add_argument("--manifest", default=str(Path(__file__).parent / "run_manifest.json"))
    ap.add_argument("--graders-root")
    ap.add_argument("--force", action="store_true", help="re-fetch even if present")
    ap.add_argument("--revision", help="override the revision pinned in the manifest")
    a = ap.parse_args(argv)
    fetch(a.task, a.manifest, a.graders_root, a.force, a.revision)
    return 0


if __name__ == "__main__":
    sys.exit(main())
