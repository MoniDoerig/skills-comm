#!/usr/bin/env python3
"""score_dataset_state.py — grade a Nipoppy study for the `nipoppy-fmriprep-default`
benchmark task.

This is the GRADER-side scorer. The submission is not an image but a directory tree that
`nipoppy` built, and it is graded by **running nipoppy against it** rather than by reading
what the agent wrote.

Why re-run rather than read the logs. The task's answer -- which participant-sessions
exist -- is a directory listing away, so a log or a TSV inside the submission proves
nothing on its own: an agent that did none of the work can write either. Re-running moves
the evidence out of the agent's reach. The selection comes from the agent's configuration,
exercised by the grader, and a study that was never really configured cannot produce one.

Two invocations, both against a copy, because re-running writes new logs:

    process --write-subcohort     the participant-sessions this study would run on
    process --simulate            one pair, which regenerates the pipeline command from
                                  the agent's own invocation.json and global_config.json

The second is what makes `work_dir` gradeable. The pipeline bundle ships `work_dir` as
"/work", a path that exists only inside a container bind; nothing here runs a container,
so an unfixed command would fail at runtime -- but the task launches with --simulate and
never reaches runtime. Regenerating the command is the only place the defect is visible.

Scored:

    pair_recall        of the participant-sessions in the dataset, the fraction this
                       study would run on. Near-binary in practice: a correctly built
                       study selects all of them and a broken one fails a rerun gate
                       instead, so this mainly catches a study built over part of the
                       dataset.
    work_dir_ok        the regenerated command's working directory lies inside the study
    config_ok          the container command is disabled and no pipeline variable is null

Validity gates:

    study_initialised        global_config.json and manifest.tsv exist
    pipeline_installed       the bundle the catalog ships
    rerun_selection          nipoppy could compute a selection from this study
    rerun_simulate           nipoppy could generate a pipeline command from this study
    no_invented_pairs        every selected pair is in the dataset
    not_executed_for_real    the task forbids a real run, and a real run leaves outputs

The two rerun gates are the forgery check, and they do it by construction: neither can
pass unless the study really is configured. They also absorb the failures that would
otherwise each need a gate -- a missing BIDS tree, an uninstalled pipeline and an unset
pipeline variable each make nipoppy exit non-zero with its own message, which is recorded
in the notes.

Pack layout (--pack DIR):
    rubric.json                     weights, gates, verdict thresholds, pipeline pins
    reference/expected_pairs.tsv    participant and session id per line, no header

Usage:
    score_dataset_state.py --study SUBMISSION_DIR --pack PACK_DIR [--json out.json]

Exit code is 0 when the submission is valid (not gate-failed), 1 otherwise.

Dependencies: nipoppy on PATH or at $NIPOPPY_BIN; standard library only.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Every metric is a fraction where more is better, so no lower-is-better set is needed.
# The name is kept because the harness imports every scorer the same way.
LOWER_BETTER = set()

_ANSI = re.compile(r"\x1b\[[0-9;]*m")
# A record starts with its level, optionally behind a bracketed timestamp: the log file
# writes "[2026-11-13 00:54:45] INFO ...", a terminal writes "INFO ...". Anything else
# continues the record before it, because long records are wrapped to the screen width.
_LEVEL = re.compile(r"^(?:\[[^\]]+\]\s*)?(INFO|WARNING|ERROR|DEBUG)\s")


def log_records(text):
    """The records of a log, each unwrapped back onto a single line."""
    out, cur = [], []
    for line in _ANSI.sub("", text).splitlines():
        m = _LEVEL.match(line)
        if m:
            if cur:
                out.append(" ".join(cur))
            cur = [line[m.end():]]
        elif cur:
            cur.append(line.strip())
    if cur:
        out.append(" ".join(cur))
    return [re.sub(r"\s+", " ", r).strip() for r in out]


def expected_pairs(pack):
    p = pack / "reference" / "expected_pairs.tsv"
    if not p.is_file():
        raise SystemExit(f"ERROR: no reference list at {p}")
    out = set()
    for line in p.read_text().splitlines():
        if line.strip():
            c = line.split("\t")
            out.add((c[0].strip(), c[1].strip() if len(c) > 1 else ""))
    return out


def pairs_from_tsv(path):
    out = set()
    for line in path.read_text().splitlines():
        if line.strip():
            c = line.split("\t")
            if len(c) >= 2:
                out.add((c[0].strip().removeprefix("sub-"), c[1].strip().removeprefix("ses-")))
    return out


def load_config(study):
    """global_config.json, which ships as JSONC and must survive its comments."""
    p = study / "global_config.json"
    if not p.is_file():
        return None
    try:
        return json.loads(re.sub(r"(?m)^\s*//.*$", "", p.read_text()))
    except json.JSONDecodeError:
        return None


def find_study(submission, notes):
    """The study root, which may be the submitted directory or one inside it."""
    if (submission / "global_config.json").is_file():
        return submission
    found = next((p.parent for p in sorted(submission.glob("*/global_config.json"))), None)
    if found is not None:
        notes.append(f"study root found at {found.name}/")
        return found
    return submission


def run_nipoppy(exe, study, rubric, extra, notes, label):
    """One nipoppy invocation against the study, captured rather than trusted."""
    cmd = [exe, "process", "--study", str(study),
           "--pipeline", rubric.get("pipeline", "fmriprep"),
           "--pipeline-version", rubric.get("pipeline_version", "24.1.1")] + extra
    timeout = rubric.get("rerun_timeout_s", 600)
    # nipoppy renders its log through rich, which wraps to the terminal width and will
    # break a long path across lines mid-token. Unwrapping then rejoins the halves with a
    # space, which would turn the pipeline command's working directory into a fragment
    # and read as wrong. Asking for a very wide terminal stops it wrapping at all.
    env = {**os.environ, "COLUMNS": "10000", "TERM": "dumb"}
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    except (subprocess.TimeoutExpired, OSError) as e:
        notes.append(f"{label}: {type(e).__name__} after {timeout}s")
        return None, ""
    text = (p.stdout or "") + (p.stderr or "")
    if p.returncode != 0:
        why = next((r for r in log_records(text) if r.startswith("ERROR")), "")
        notes.append(f"{label}: nipoppy exit {p.returncode}. {why[:160]}")
    return p.returncode, text


def work_dir_ok(records, study, notes):
    """Does the regenerated command put its working directory inside the study?"""
    cmds = [r for r in records
            if "--fs-license-file" in r and not r.lstrip().startswith("Descriptor string:")]
    if not cmds:
        notes.append("the rerun generated no pipeline command")
        return 0.0
    toks = cmds[0].split()
    w = next((toks[i + 1] for i, t in enumerate(toks) if t == "-w" and i + 1 < len(toks)), None)
    if w is None:
        notes.append("the regenerated command names no working directory")
        return 0.0
    inside = str(study.resolve()) in str(Path(w).resolve(strict=False))
    if not inside:
        notes.append(f"the regenerated command works in {w}, outside the study")
    return 1.0 if inside else 0.0


def config_score(cfg, notes):
    """A disabled container command, and no pipeline variable left unset."""
    if cfg is None:
        notes.append("global_config.json missing or unparseable")
        return 0.0
    parts = [1.0 if cfg.get("CONTAINER_CONFIG", {}).get("COMMAND", "unset") is None else 0.0]
    vals = [v for kinds in cfg.get("PIPELINE_VARIABLES", {}).values()
            for names in (kinds or {}).values()
            for d in (names or {}).values() for v in (d or {}).values()]
    if vals:
        parts.append(sum(v is not None for v in vals) / len(vals))
    else:
        notes.append("no PIPELINE_VARIABLES present; the pipeline was never installed")
        parts.append(0.0)
    return sum(parts) / len(parts)


def real_run_outputs(study):
    """Files a genuine fMRIPrep run leaves, which --simulate never writes."""
    root = study / "derivatives"
    if not root.is_dir():
        return 0
    return sum(1 for p in root.rglob("*")
               if p.is_file() and (p.name.endswith(".html") or p.suffix in {".nii", ".gz"}))


def score(study_dir, pack_dir):
    pack = Path(pack_dir)
    rubric = json.loads((pack / "rubric.json").read_text())
    notes = []
    submitted = find_study(Path(study_dir), notes)
    # Which nipoppy grades. NIPOPPY_BIN lets a harness point at the pinned install it
    # made after the agent stopped, which matters because an agent can write to anything
    # installed during its own run. No path is recorded in the rubric: it would be one
    # machine's, and a grader that silently found the wrong version would report a bad
    # environment as a bad submission.
    exe = os.environ.get("NIPOPPY_BIN") or shutil.which("nipoppy")
    if not exe:
        raise SystemExit("ERROR: no nipoppy on PATH; set NIPOPPY_BIN to the pinned install")

    want = expected_pairs(pack)
    cfg = load_config(submitted)
    installed = bool(list((submitted / "pipelines" / "processing").glob("*/config.json")))

    # Work on a copy: re-running writes logs, and a grader must not alter what it grades.
    tmp = Path(tempfile.mkdtemp(prefix="grade_nipoppy_"))
    selected, sel_rc, sim_rc, wd = set(), None, None, 0.0
    try:
        study = tmp / "study"
        shutil.copytree(submitted, study, symlinks=True, ignore_dangling_symlinks=True)

        out_tsv = tmp / "subcohort.tsv"
        sel_rc, _ = run_nipoppy(exe, study, rubric, ["--write-subcohort", str(out_tsv)],
                                notes, "selection")
        if out_tsv.is_file():
            selected = pairs_from_tsv(out_tsv)

        # The pair is taken from the reference, so the grader never depends on the agent
        # having chosen a particular one to demonstrate.
        pid, sid = sorted(want)[0] if want else ("", "")
        sim_rc, sim_text = run_nipoppy(
            exe, study, rubric,
            ["--participant-id", pid, "--session-id", sid, "--simulate"], notes, "simulate")
        if sim_rc == 0:
            wd = work_dir_ok(log_records(sim_text), study, notes)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    recall = len(selected & want) / len(want) if want else 0.0
    metrics = {"pair_recall": recall,
               "pairs_selected": float(len(selected)), "pairs_expected": float(len(want)),
               "pairs_invented": float(len(selected - want)),
               "work_dir_ok": wd, "config_ok": config_score(cfg, notes)}

    invented = sorted(selected - want)
    if invented:
        notes.append(f"selected pairs absent from the dataset: {invented[:5]}")
    gates = {
        "study_initialised": (submitted / "manifest.tsv").is_file() and cfg is not None,
        "pipeline_installed": installed,
        "rerun_selection": sel_rc == 0 and bool(selected),
        "rerun_simulate": sim_rc == 0,
        "no_invented_pairs": not invented,
        "not_executed_for_real": real_run_outputs(submitted) <= rubric.get("max_real_outputs", 0),
    }
    failures = [k for k, ok in gates.items() if not ok]

    weights = rubric["weights"]
    subs = {k: float(min(max(metrics[k], 0.0), 1.0)) for k in weights}
    quality = 100.0 * sum(weights[k] * subs[k] for k in weights) / sum(weights.values())
    if failures:
        quality = 0.0

    vt = rubric["verdict_thresholds"]
    if failures:
        verdict = "invalid"
    elif quality >= vt.get("complete", 99):
        verdict = "complete"
    elif quality >= vt["acceptable"]:
        verdict = "acceptable"
    elif quality >= vt["marginal"]:
        verdict = "marginal"
    else:
        verdict = "unacceptable"

    return {"verdict": verdict, "quality": round(quality, 2),
            "gate_failures": failures, "load_notes": notes,
            "metrics": {k: round(float(v), 4) for k, v in metrics.items()},
            "subscores": {k: round(v, 4) for k, v in subs.items()}}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Grade a Nipoppy study by re-running nipoppy on it.")
    ap.add_argument("--study", required=True, help="the submitted Nipoppy study directory")
    ap.add_argument("--pack", required=True, help="grader pack (rubric.json + reference/)")
    ap.add_argument("--json", help="write the result here as well as printing it")
    a = ap.parse_args(argv)
    result = score(a.study, a.pack)
    text = json.dumps(result, indent=2)
    print(text)
    if a.json:
        Path(a.json).write_text(text + "\n")
    return 0 if not result["gate_failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
