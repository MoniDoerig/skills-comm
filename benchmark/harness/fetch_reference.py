#!/usr/bin/env python3
"""Fetch a task's grader-side reference NIfTIs from OSF into its pack/reference/.

Policy: code on GitHub, reference data on OSF (public project, no auth). This runs in the
GRADING plane only — never in the plane where the agent produces its answer, so the ground
truth is never exposed to the model.

Reads run_manifest.json for the task's osf_ref_dir + reference_files and fetches each with
the osfclient CLI. Idempotent: files already present are left untouched.

    python fetch_reference.py --task clinical-wmh-segmentation
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def fetch(task_id, manifest_path, graders_root=None, force=False):
    manifest_path = Path(manifest_path)
    m = json.load(open(manifest_path))
    if task_id not in m["tasks"]:
        raise SystemExit(f"ERROR: task '{task_id}' not in {manifest_path}")
    spec = m["tasks"][task_id]
    root = Path(graders_root).resolve() if graders_root else manifest_path.resolve().parent.parent
    proj = m["defaults"]["osf_project"]
    ref_root = m["defaults"]["osf_ref_root"]                 # e.g. osfstorage/ground_truth
    ref_dir = spec["osf_ref_dir"]                            # e.g. clinical_gt/clinical-wmh-segmentation
    dest = root / spec["pack_dir"] / "reference"
    dest.mkdir(parents=True, exist_ok=True)

    for fname in spec["reference_files"]:
        local = dest / fname
        if local.exists() and not force:
            print(f"  [skip] {fname} already present")
            continue
        remote = f"{ref_root}/{ref_dir}/{fname}"
        cmd = ["osf", "-p", proj, "fetch"] + (["-f"] if force else []) + [remote, str(local)]
        print(f"  [fetch] {remote} -> {local}")
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 or not local.exists():
            raise SystemExit(f"ERROR: OSF fetch failed for {remote}\n"
                             f"cmd: {' '.join(cmd)}\nstdout:{r.stdout}\nstderr:{r.stderr}")
    print(f"reference ready: {dest}")
    return dest


def main(argv=None):
    ap = argparse.ArgumentParser(description="Fetch a task's OSF reference into its pack.")
    ap.add_argument("--task", required=True)
    ap.add_argument("--manifest", default=str(Path(__file__).parent / "run_manifest.json"))
    ap.add_argument("--graders-root")
    ap.add_argument("--force", action="store_true", help="re-fetch even if present")
    a = ap.parse_args(argv)
    fetch(a.task, a.manifest, a.graders_root, a.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
