#!/usr/bin/env python3
"""Uniform grading front-end for the benchmark.

The task scorers emit different result shapes and take differently named prediction flags.
This wrapper is the single entry point the CI grading job calls. It:

  1. looks a task up in run_manifest.json (task -> pack, scorer, prediction flag, detail shape),
  2. finds the agent's submission at the ONE contracted path (no fuzzy file discovery),
  3. runs the correct scorer as a subprocess,
  4. wraps the raw result in a stable envelope with a numeric, rankable `score`
     plus run provenance (model, condition, timestamp),
  5. normalises the per-scorer detail block under a common `detail` key.

`aggregate` mode reads many envelopes and produces a ranked leaderboard.json.

Every run ends with a run report (run_report.md, given to the agent by the harness, not
by the task's prompt) that says whether the task's input could support it. The wrapper reads
the report of every run and keeps it in the envelope. It grades it only for a task whose
cases carry a role (control or defect) and whose manifest entry names the report as its
`record`, and then reads it itself, so the scorer never sees a case it has no reference for:

    defect    passes when the report says input_usable: false; input_usable: true is a
              missed defect, and no report is no answer. Whether the run went on to write
              an output is recorded (`stopped`), not graded: the report does not tell the
              agent what to do with an input it doubts
    control   a report that says input_usable: false is a false alarm and fails; otherwise
              the output is scored as for any other case. A missing report is noted, not
              failed, so the control rate stays comparable with runs that wrote none

On every other task the report is kept and not graded: the output is scored whatever the
report says, so a task whose data is poor but workable (a motion-corrupted scan) is graded
on what the agent made of it.

The three scorers are never modified — all cross-scorer uniformity lives here.

Envelope schema (schema_version 1.0):

    {
      "schema_version": "1.0",
      "task_id": str,
      "subject": str | null,        # the subject graded, for a task graded per subject
      "role": str | null,           # the case's role in cases.json, for a task whose cases
                                    # have one; reported apart, never pooled
      "record": dict | null,        # the agent's run report, on every task; graded only
                                    # where the manifest names it as the task's `record`
      "record_graded": bool,        # whether the report was graded
      "stopped": bool | null,       # defect cases: whether the run wrote no output
      "model": str,                 # e.g. "qwen"           (runner-supplied)
      "condition": str,             # "baseline" | "skill"  (runner-supplied)
      "timestamp": str,             # ISO-8601 UTC          (runner-supplied or now)
      "scorer": str,                # scorer filename
      "pack": str,                  # pack dir (relative)
      "valid": bool,                # == (no gate failures)
      "verdict": str,               # invalid|unacceptable|marginal|acceptable|within_reference_variability
      "score": float,               # 0..100 quality  -> PRIMARY RANK KEY
      "tiebreak": float,            # secondary rank key (mean Dice), for equal scores
      "gate_failures": [str],
      "load_notes": [str],
      "detail": {"kind": "binary"|"multiclass", ...},
      "raw": {...}                  # full untouched scorer output, for drill-down
    }
"""
import argparse
import glob
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    from . import cases as cases_mod       # imported as benchmark.harness.grade_wrapper
except ImportError:
    import cases as cases_mod              # run as a script from this directory

SCHEMA_VERSION = "1.0"

# Ordering of the verdict vocabulary, worst -> best. Used only for display/tie context;
# ranking is on the numeric `score`, which is already monotonic with the verdict tier.
VERDICT_ORDER = ["invalid", "unacceptable", "marginal", "acceptable", "within_reference_variability"]


def _utcnow_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve_root(manifest_path: Path, override: str | None) -> Path:
    """graders_root holds graders/ ; default = parent of the manifest's directory."""
    return Path(override).resolve() if override else manifest_path.resolve().parent.parent


def _mean_dice(raw: dict, detail_kind: str) -> float:
    """Secondary rank key: mean Dice across whatever the task measures. 0.0 if absent."""
    if detail_kind == "multiclass":
        pc = raw.get("per_class", {})
        vals = [c.get("dice") for c in pc.values() if isinstance(c, dict) and c.get("dice") is not None]
        return round(sum(vals) / len(vals), 4) if vals else 0.0
    d = (raw.get("metrics") or {}).get("dice")
    return round(float(d), 4) if d is not None else 0.0


def _normalise_detail(raw: dict, detail_kind: str) -> dict:
    """Fold each scorer's drill-down into one shape the dashboard can load uniformly."""
    if detail_kind == "multiclass":
        return {"kind": "multiclass", "per_class": raw.get("per_class", {})}
    return {"kind": "binary",
            "metrics": raw.get("metrics", {}),
            "subscores": raw.get("subscores", {})}


def grade(task_id, submission_dir, manifest_path, graders_root=None,
          model="unknown", condition="baseline", timestamp=None, subject=None):
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    if task_id not in manifest["tasks"]:
        raise SystemExit(f"ERROR: task '{task_id}' not in {manifest_path}. "
                         f"Known: {', '.join(sorted(manifest['tasks']))}")
    spec = manifest["tasks"][task_id]
    # A task graded per subject needs the subject named, and it has to be one of its
    # own; a task with one reference takes none. Checked here, not left to str.format,
    # where a missing subject is a KeyError and a wrong one a quiet path to nothing.
    allowed = spec.get("subjects") or []
    role = None
    named = subject
    if spec.get("per_subject") and not allowed:
        # The subjects live in the gated cases.json, not in the manifest: the allowed
        # list comes from there, and a case id becomes its subject. The role comes from
        # there too, and goes into the envelope whatever the submission holds, so a run
        # that wrote nothing is still counted on the rate it belongs to.
        cs = cases_mod.load(manifest, spec.get("reference_revision"))
        allowed = cases_mod.subjects_of(cs, task_id)
        if subject is not None:
            role = cases_mod.role_of(cs, task_id, subject)
            subject = cases_mod.resolve(cs, task_id, subject)
    if spec.get("per_subject"):
        if subject is None:
            raise SystemExit(f"ERROR: '{task_id}' is graded per subject; pass --subject.\n"
                             f"Available: {', '.join(allowed) if allowed else '(none listed)'}")
        if allowed and subject not in allowed:
            raise SystemExit(f"ERROR: '{subject}' is not a subject of '{task_id}'.\n"
                             f"Available: {', '.join(allowed)}")
    elif subject:
        raise SystemExit(f"ERROR: '{task_id}' has a single reference; --subject does not "
                         "apply to it")
    fields = {"task_id": task_id, "subject": subject or ""}
    root = _resolve_root(manifest_path, graders_root)

    scorer = root / spec["scorer"]
    pack = root / spec["pack_dir"]
    if not scorer.exists():
        raise SystemExit(f"ERROR: scorer not found: {scorer}")
    # A pack carries either one rubric, or rubrics/policy.json for the tasks graded per
    # subject, which fetch_reference.py --subject merges with the subject's gated part
    # into reference/rubric.json. Requiring rubric.json of a per-subject pack would mean
    # keeping a copy of one subject's calibration at the pack root, where nothing reads
    # it and nothing says which subject it describes.
    if not ((pack / "rubric.json").exists() or (pack / "rubrics" / "policy.json").is_file()):
        raise SystemExit(f"ERROR: no rubric.json and no rubrics/policy.json in pack: {pack}")

    # The contracted path: the task's own, else the manifest default for a task graded
    # per subject (submission_path, one level deeper) or for one with a single reference.
    defaults = manifest["defaults"]
    template = (spec.get("submission_output_path")
                or defaults["submission_path" if subject else "submission_output_path"])
    # A blinded run is given its case id, and the prompt's {subject} is that id, so its
    # output sits under the case id. One named by subject writes under the subject.
    # A run that stopped short may leave only its report, so the report counts too.
    record_tpl = spec.get("record")
    report_tpl = record_tpl or defaults.get(
        "run_report_path" if subject else "run_report_output_path")
    if named != subject and any(
            (Path(submission_dir) / t.format(**{**fields, "subject": named})).exists()
            for t in (template, report_tpl) if t):
        fields["subject"] = named
    out_rel = template.format(**fields)
    pred = Path(submission_dir) / out_rel

    record, rec_note, rec_rel = None, None, None
    if report_tpl:
        rec_rel = report_tpl.format(**fields)
        record, rec_note = _read_record(Path(submission_dir) / rec_rel)
    graded = bool(record_tpl) and role in ("control", "defect")
    if graded:
        if role == "defect":
            outputs = [rel for rel in [out_rel] + [
                           r.format(**fields) for r in list((spec.get("required_inputs") or {}).values())
                           + list((spec.get("optional_inputs") or {}).values())]
                       if _wrote(Path(submission_dir) / rel, Path(submission_dir) / rec_rel)]
            return _envelope(task_id, spec, model, condition, timestamp,
                             raw=_grade_defect(record, rec_note, rec_rel, outputs),
                             subject=subject, role=role, record=record, record_graded=True)
        if record is not None and record["input_usable"] is False:
            return _envelope(task_id, spec, model, condition, timestamp,
                             raw={"verdict": "invalid", "quality": 0.0,
                                  "gate_failures": ["usable_input_called_unusable"],
                                  "load_notes": [f"{rec_rel} calls the input unusable, and "
                                                 f"it is usable"]},
                             subject=subject, role=role, record=record, record_graded=True)
        rec_notes = [rec_note] if rec_note else []
    else:
        rec_notes = []

    if not pred.exists():
        # A missing contracted output is a submission failure, not a harness crash:
        # report it as an invalid verdict so it still lands on the leaderboard at 0.
        return _envelope(task_id, spec, model, condition, timestamp,
                         raw={"verdict": "invalid", "quality": 0.0,
                              "gate_failures": ["missing_output"],
                              "load_notes": [f"no submission at {out_rel}"]},
                         subject=subject, role=role, record=record, record_graded=graded)

    # Build: python <scorer> <pred_flag> <pred> --pack <pack> --json <tmp> [extra inputs]
    result_json = Path(submission_dir) / f".grade_{task_id}.json"
    cmd = [sys.executable, str(scorer), spec["pred_flag"], str(pred),
           "--pack", str(pack), "--json", str(result_json)]
    for flag, rel in (spec.get("required_inputs") or {}).items():
        cand = Path(submission_dir) / rel.format(**fields)
        if not cand.exists():
            return _envelope(
                task_id, spec, model, condition, timestamp,
                raw={"verdict": "invalid", "quality": 0.0,
                     "gate_failures": [f"missing_required_output:{cand.name}"],
                     "load_notes": [f"no submission at {rel.format(**fields)}"]},
                subject=subject, role=role, record=record, record_graded=graded,
            )
        cmd += [flag, str(cand)]
    for flag, rel in (spec.get("optional_inputs") or {}).items():
        cand = Path(submission_dir) / rel.format(**fields)
        if cand.exists():
            cmd += [flag, str(cand)]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    # Scorers exit 1 on gate failure by design — that is NOT a harness error. A harness
    # error is: no result file written (crash / bad args). Detect that explicitly.
    if not result_json.exists():
        raise SystemExit(f"ERROR: scorer produced no result for {task_id} (exit {proc.returncode}).\n"
                         f"cmd: {' '.join(cmd)}\nstderr:\n{proc.stderr}")
    raw = json.load(open(result_json))
    result_json.unlink(missing_ok=True)
    raw["load_notes"] = list(raw.get("load_notes", [])) + rec_notes
    return _envelope(task_id, spec, model, condition, timestamp, raw, subject=subject,
                     role=role, record=record, record_graded=graded)


def _read_record(path):
    """The agent's run report, or None with the reason it could not be read.

    Only `input_usable` is graded, and it has to be a JSON boolean: "false" as a string, or
    0, is no answer. `completed` and `reason` are kept for whoever reads the envelope.
    """
    if not path.is_file():
        return None, f"no report at {path.name}"
    try:
        rec = json.loads(path.read_text())
    except (ValueError, OSError) as e:
        return None, f"{path.name} could not be read: {type(e).__name__}"
    if not isinstance(rec, dict) or not isinstance(rec.get("input_usable"), bool):
        return None, f"{path.name} has no boolean input_usable"
    completed = rec.get("completed")
    return {"completed": completed if isinstance(completed, bool) else None,
            "input_usable": rec["input_usable"], "reason": rec.get("reason")}, None


def _wrote(path, report):
    """Whether the run wrote this output. A task whose output is its case directory holds
    the report there too, so the directory counts only for what else is in it."""
    if path.is_dir():
        return any(p != report for p in path.rglob("*") if p.is_file())
    return path.exists()


def _grade_defect(record, rec_note, rec_rel, outputs):
    """A defect case: the input cannot support the task, and the report is the answer.

    The flag is what the case tests. Whether the run stopped there or went on to write an
    output is recorded as `stopped` for whoever reads the envelope, and not graded: nothing
    the agent is given says which to do.
    """
    stopped = not outputs
    wrote = "stopped there" if stopped else f"went on to write {', '.join(outputs)}"
    if record is None:
        return {"verdict": "invalid", "quality": 0.0, "gate_failures": ["record_missing"],
                "load_notes": [rec_note], "stopped": stopped}
    if record["input_usable"]:
        return {"verdict": "unacceptable", "quality": 0.0, "gate_failures": [],
                "load_notes": [f"{rec_rel} calls the input usable, and it is not"],
                "stopped": stopped}
    return {"verdict": "acceptable", "quality": 100.0, "gate_failures": [],
            "load_notes": [f"{rec_rel} calls the input unusable; the run {wrote}"],
            "stopped": stopped}


def _envelope(task_id, spec, model, condition, timestamp, raw, subject=None, role=None,
              record=None, record_graded=False):
    detail_kind = spec["detail_kind"]
    gate_failures = raw.get("gate_failures", [])
    return {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "subject": subject,
        "role": role,
        "record": record,
        "record_graded": record_graded,
        "stopped": raw.get("stopped"),
        "model": model,
        "condition": condition,
        "timestamp": timestamp or _utcnow_iso(),
        "scorer": Path(spec["scorer"]).name,
        "pack": spec["pack_dir"],
        "valid": not gate_failures,
        "verdict": raw.get("verdict", "invalid"),
        "score": float(raw.get("quality", 0.0)),
        "tiebreak": _mean_dice(raw, detail_kind),
        "gate_failures": gate_failures,
        "load_notes": raw.get("load_notes", []),
        "detail": _normalise_detail(raw, detail_kind),
        "raw": raw,
    }


def _rank(subs):
    """Rank submissions best -> worst: primary score desc, then mean-Dice tiebreak desc."""
    ordered = sorted(subs, key=lambda e: (e["score"], e["tiebreak"]), reverse=True)
    for i, e in enumerate(ordered, 1):
        e["rank"] = i
    return ordered


def aggregate(envelope_glob, out_path):
    """Read many envelopes and emit a ranked leaderboard: per-task ranking + a wide matrix."""
    files = sorted(glob.glob(envelope_glob))
    envs = [json.load(open(f)) for f in files]
    by_task = {}
    for e in envs:
        by_task.setdefault(e["task_id"], []).append(e)

    tasks = {}
    for tid, subs in sorted(by_task.items()):
        ranked = _rank(subs)
        tasks[tid] = [
            {"rank": e["rank"], "model": e["model"], "condition": e["condition"],
             "verdict": e["verdict"], "valid": e["valid"], "score": round(e["score"], 2),
             "tiebreak": e["tiebreak"], "gate_failures": e["gate_failures"]}
            for e in ranked
        ]

    # Wide matrix: (model, condition) -> {task_id: score}, plus a mean across tasks.
    matrix = {}
    for e in envs:
        key = f"{e['model']}::{e['condition']}"
        matrix.setdefault(key, {"model": e["model"], "condition": e["condition"], "scores": {}})
        matrix[key]["scores"][e["task_id"]] = round(e["score"], 2)
    for row in matrix.values():
        s = list(row["scores"].values())
        row["mean_score"] = round(sum(s) / len(s), 2) if s else 0.0

    board = {"generated": _utcnow_iso(), "schema_version": SCHEMA_VERSION,
             "n_submissions": len(envs), "tasks": tasks,
             "matrix": sorted(matrix.values(), key=lambda r: r["mean_score"], reverse=True)}
    if out_path:
        json.dump(board, open(out_path, "w"), indent=2)
    return board


def main(argv=None):
    ap = argparse.ArgumentParser(description="Uniform grading front-end + leaderboard aggregator.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("grade", help="grade one submission -> envelope JSON")
    g.add_argument("--task", required=True, help="task_id (must be in the manifest)")
    g.add_argument("--subject", help="the subject graded, for a task graded per subject "
                                     "(per_subject in the manifest); its output is read at "
                                     "submissions/<task_id>/<subject>/")
    g.add_argument("--case", dest="subject", help="the case id a run names; the reference "
                                                  "dataset's cases.json maps it to the subject, "
                                                  "and the output is read under the subject")
    g.add_argument("--submission-dir", required=True, help="dir holding submission/output.nii.gz")
    g.add_argument("--manifest", default=str(Path(__file__).parent / "run_manifest.json"))
    g.add_argument("--graders-root", help="override; default = parent of the manifest's dir")
    g.add_argument("--model", default="unknown")
    g.add_argument("--condition", default="baseline", help="baseline | skill")
    g.add_argument("--timestamp", help="ISO-8601; default = now (UTC)")
    g.add_argument("--out", help="write the envelope here (also printed to stdout)")

    a = sub.add_parser("aggregate", help="many envelopes -> ranked leaderboard.json")
    a.add_argument("--glob", required=True, help="glob for envelope JSONs, e.g. 'results/*.json'")
    a.add_argument("--out", required=True)

    ls = sub.add_parser("list", help="print the live (gradeable) task IDs from the manifest")
    ls.add_argument("--manifest", default=str(Path(__file__).parent / "run_manifest.json"))
    ls.add_argument("--verbose", action="store_true", help="also show scorer + detail kind")

    args = ap.parse_args(argv)
    if args.cmd == "list":
        tasks = json.load(open(args.manifest))["tasks"]
        for tid in sorted(tasks):
            if args.verbose:
                s = tasks[tid]
                print(f"{tid:42s} {Path(s['scorer']).name:22s} {s['detail_kind']}")
            else:
                print(tid)
        return 0
    if args.cmd == "grade":
        env = grade(args.task, args.submission_dir, args.manifest, args.graders_root,
                    args.model, args.condition, args.timestamp, args.subject)
        print(json.dumps(env, indent=2))
        if args.out:
            json.dump(env, open(args.out, "w"), indent=2)
        # Exit code mirrors validity so CI can branch, but the envelope is always written.
        return 0 if env["valid"] else 1
    if args.cmd == "aggregate":
        board = aggregate(args.glob, args.out)
        print(f"wrote {args.out}: {board['n_submissions']} submissions across "
              f"{len(board['tasks'])} tasks, {len(board['matrix'])} model×condition rows")
        return 0


if __name__ == "__main__":
    sys.exit(main())
