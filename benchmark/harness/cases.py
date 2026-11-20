"""Case ids for the tasks graded per subject.

`cases.json` lives in the gated reference dataset, beside the references and the
calibration, and maps a case id to the task and subject it stands for:

    {"cases": {"case-012": {"task": "structural-brain-extraction", "subject": "sub-XXXX",
                            "dataset": "ds002790", "version_pin": "2.0.0", ...}, ...}}

Real case ids run from case-100 to case-999 and are drawn at random. case-000 to case-099
are never drawn, so examples and tests use them and never name a real case.

A benchmark run names a case, never a subject, so an agent cannot look its subject up
anywhere public. The harness reads this file at the two moments it needs the subject:
before the agent starts (to fetch the data under the case name) and at grading time.
The subject lists therefore no longer appear in run_manifest.json or tasks.json.

A case may carry the `prompt_version` it was staged for. When a task's prompt changes
what the agent is given, its new cases get new ids and the old ones stay, so a run of the
old prompt still resolves; a batch draws only the cases of the task's current version.
"""
import json
from pathlib import Path

DEFAULT_FILE = "cases.json"


def load(manifest, revision=None, force=False):
    """The cases of the manifest's reference dataset at its pinned revision."""
    from huggingface_hub import hf_hub_download   # only the fetch needs the Hub
    d = manifest["defaults"]
    rev = revision or d.get("reference_revision")
    got = hf_hub_download(repo_id=d["reference_repo"],
                          repo_type=d.get("reference_repo_type", "dataset"),
                          filename=d.get("cases_file", DEFAULT_FILE),
                          revision=rev, force_download=force)
    return json.loads(Path(got).read_text())["cases"]


def subjects_of(cases, task_id):
    """The subjects a task is graded on, in case-id order, each once: a subject staged
    for more than one prompt version has a case for each."""
    return list(dict.fromkeys(c["subject"] for _, c in sorted(cases.items())
                              if c["task"] == task_id))


def referenced_subjects_of(cases, task_id):
    """The subjects of a task with a `record` that have a reference: all but its defect
    cases, which the wrapper grades on the agent's record alone."""
    return list(dict.fromkeys(c["subject"] for _, c in sorted(cases.items())
                              if c["task"] == task_id and c.get("role") != "defect"))


def resolve(cases, task_id, case_or_subject):
    """A case id becomes its subject; a subject id passes through unchanged, so the
    scripts keep working for anyone who names the subject directly."""
    c = cases.get(case_or_subject)
    if c is None:
        return case_or_subject
    if c["task"] != task_id:
        raise SystemExit(f"ERROR: {case_or_subject} is a case of {c['task']}, not of {task_id}")
    return c["subject"]


def role_of(cases, task_id, case_or_subject):
    """The case's role, for a task whose cases have one; None otherwise.

    A role says what a case is for when a task is reported by more than one rate rather
    than by one pass rate. Most tasks' cases carry none. Looked up by case id, or by
    subject for anyone who names the subject directly.
    """
    c = cases.get(case_or_subject)
    if c is None:
        # a subject with cases for more than one prompt version: the one with a role
        mine = [v for v in cases.values()
                if v["task"] == task_id and v["subject"] == case_or_subject]
        c = next((v for v in mine if v.get("role")), mine[0] if mine else None)
    if c is None or c["task"] != task_id:
        return None
    return c.get("role")
