import json
import shutil
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from benchmark.harness import grade_wrapper


class GradeWrapperTests(unittest.TestCase):
    def test_missing_required_secondary_output_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            harness = root / "harness"
            pack = root / "graders" / "registration"
            submission = root / "run"
            harness.mkdir()
            pack.mkdir(parents=True)
            (pack / "rubric.json").write_text("{}")

            scorer = pack / "score.py"
            scorer.write_text(
                "import argparse\n"
                "p = argparse.ArgumentParser()\n"
                "p.add_argument('--warped', required=True)\n"
                "p.add_argument('--dseg', required=True)\n"
                "p.add_argument('--pack', required=True)\n"
                "p.add_argument('--json', required=True)\n"
                "p.parse_args()\n"
            )

            manifest = {
                "defaults": {"submission_output_path": "submissions/{task_id}/output.nii.gz"},
                "tasks": {
                    "registration": {
                        "pack_dir": "graders/registration",
                        "scorer": "graders/registration/score.py",
                        "pred_flag": "--warped",
                        "detail_kind": "registration",
                        "required_inputs": {
                            "--dseg": "submissions/{task_id}/dseg.nii.gz"
                        },
                    }
                },
            }
            manifest_path = harness / "run_manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            output = submission / "submissions" / "registration" / "output.nii.gz"
            output.parent.mkdir(parents=True)
            output.touch()

            result = grade_wrapper.grade("registration", submission, manifest_path)

            self.assertEqual(result["verdict"], "invalid")
            self.assertEqual(result["gate_failures"], ["missing_required_output:dseg.nii.gz"])

    def test_per_subject_task_is_graded_at_the_subject_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            harness = root / "harness"
            pack = root / "graders" / "bet"
            submission = root / "run"
            harness.mkdir()
            (pack / "rubrics").mkdir(parents=True)
            (pack / "rubrics" / "policy.json").write_text("{}")

            # A scorer that reports back which mask it was given.
            scorer = pack / "score.py"
            scorer.write_text(
                "import argparse, json\n"
                "p = argparse.ArgumentParser()\n"
                "p.add_argument('--mask', required=True)\n"
                "p.add_argument('--stripped')\n"
                "p.add_argument('--pack', required=True)\n"
                "p.add_argument('--json', required=True)\n"
                "a = p.parse_args()\n"
                "json.dump({'verdict': 'acceptable', 'quality': 80.0, 'gate_failures': [],\n"
                "           'metrics': {'dice': 0.9}, 'mask': a.mask}, open(a.json, 'w'))\n"
            )

            manifest = {
                "defaults": {
                    "submission_output_path": "submissions/{task_id}/output.nii.gz",
                    "submission_path": "submissions/{task_id}/{subject}/output.nii.gz",
                },
                "tasks": {
                    "bet": {
                        "pack_dir": "graders/bet",
                        "scorer": "graders/bet/score.py",
                        "pred_flag": "--mask",
                        "detail_kind": "binary",
                        "optional_inputs": {
                            "--stripped": "submissions/{task_id}/{subject}/stripped.nii.gz"
                        },
                        "per_subject": True,
                        "subjects": ["sub-01", "sub-02"],
                    },
                    "single": {
                        "pack_dir": "graders/bet",
                        "scorer": "graders/bet/score.py",
                        "pred_flag": "--mask",
                        "detail_kind": "binary",
                    },
                },
            }
            manifest_path = harness / "run_manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            output = submission / "submissions" / "bet" / "sub-01" / "output.nii.gz"
            output.parent.mkdir(parents=True)
            output.touch()

            result = grade_wrapper.grade("bet", submission, manifest_path, subject="sub-01")

            self.assertEqual(result["verdict"], "acceptable")
            self.assertEqual(result["subject"], "sub-01")
            self.assertEqual(Path(result["raw"]["mask"]), output)

            # The other subject's output is not there: a missing output, not a crash.
            other = grade_wrapper.grade("bet", submission, manifest_path, subject="sub-02")
            self.assertEqual(other["gate_failures"], ["missing_output"])
            self.assertEqual(other["subject"], "sub-02")

            # The id and the task have to agree.
            with self.assertRaises(SystemExit):
                grade_wrapper.grade("bet", submission, manifest_path)
            with self.assertRaises(SystemExit):
                grade_wrapper.grade("bet", submission, manifest_path, subject="sub-09")
            with self.assertRaises(SystemExit):
                grade_wrapper.grade("single", submission, manifest_path, subject="sub-01")

    def test_a_cases_role_reaches_the_envelope_even_without_a_submission(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            harness = root / "harness"
            pack = root / "graders" / "fit"
            submission = root / "run"
            harness.mkdir()
            (pack / "rubrics").mkdir(parents=True)
            (pack / "rubrics" / "policy.json").write_text("{}")
            scorer = pack / "score.py"
            scorer.write_text(
                "import argparse, json\n"
                "p = argparse.ArgumentParser()\n"
                "p.add_argument('--submission', required=True)\n"
                "p.add_argument('--pack', required=True)\n"
                "p.add_argument('--json', required=True)\n"
                "a = p.parse_args()\n"
                "json.dump({'verdict': 'complete', 'quality': 100.0, 'gate_failures': []},\n"
                "          open(a.json, 'w'))\n"
            )
            manifest = {
                "defaults": {"submission_output_path": "submissions/{task_id}/output.nii.gz",
                             "submission_path": "submissions/{task_id}/{subject}/output.nii.gz"},
                "tasks": {"fit": {"pack_dir": "graders/fit", "scorer": "graders/fit/score.py",
                                  "pred_flag": "--submission",
                                  "submission_output_path": "submissions/{task_id}/{subject}",
                                  "detail_kind": "record", "per_subject": True}},
            }
            manifest_path = harness / "run_manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            table = {"case-031": {"task": "fit", "subject": "sub-01", "role": "control"},
                     "case-032": {"task": "fit", "subject": "sub-02", "role": "defect"}}
            (submission / "submissions" / "fit" / "sub-01").mkdir(parents=True)

            with mock.patch.object(grade_wrapper.cases_mod, "load", return_value=table):
                done = grade_wrapper.grade("fit", submission, manifest_path, subject="case-031")
                empty = grade_wrapper.grade("fit", submission, manifest_path, subject="case-032")

            self.assertEqual((done["role"], done["subject"], done["verdict"]),
                             ("control", "sub-01", "complete"))
            # nothing written for the defect case: still invalid, and still counted as one
            self.assertEqual((empty["role"], empty["gate_failures"]),
                             ("defect", ["missing_output"]))

    def test_a_blinded_run_is_found_under_its_case_id(self):
        # the prompt's {subject} is the case id, so that is where a blinded run writes
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            harness = root / "harness"
            pack = root / "graders" / "fit"
            submission = root / "run"
            harness.mkdir()
            (pack / "rubrics").mkdir(parents=True)
            (pack / "rubrics" / "policy.json").write_text("{}")
            (pack / "score.py").write_text(
                "import argparse, json\n"
                "p = argparse.ArgumentParser()\n"
                "p.add_argument('--submission', required=True)\n"
                "p.add_argument('--pack', required=True)\n"
                "p.add_argument('--json', required=True)\n"
                "a = p.parse_args()\n"
                "json.dump({'verdict': 'complete', 'quality': 100.0, 'gate_failures': [],\n"
                "           'load_notes': [a.submission]}, open(a.json, 'w'))\n"
            )
            manifest = {
                "defaults": {"submission_output_path": "submissions/{task_id}/output.nii.gz",
                             "submission_path": "submissions/{task_id}/{subject}/output.nii.gz"},
                "tasks": {"fit": {"pack_dir": "graders/fit", "scorer": "graders/fit/score.py",
                                  "pred_flag": "--submission",
                                  "submission_output_path": "submissions/{task_id}/{subject}",
                                  "detail_kind": "record", "per_subject": True}},
            }
            manifest_path = harness / "run_manifest.json"
            manifest_path.write_text(json.dumps(manifest))
            table = {"case-031": {"task": "fit", "subject": "sub-01", "role": "defect"}}
            (submission / "submissions" / "fit" / "case-031").mkdir(parents=True)

            with mock.patch.object(grade_wrapper.cases_mod, "load", return_value=table):
                env = grade_wrapper.grade("fit", submission, manifest_path, subject="case-031")

            self.assertEqual((env["verdict"], env["subject"], env["role"]),
                             ("complete", "sub-01", "defect"))
            self.assertTrue(env["load_notes"][0].endswith("case-031"))


class RecordGateTests(unittest.TestCase):
    """A task graded on the run report (`record`): defect cases are graded on it, controls
    can fail on it."""

    TABLE = {"case-061": {"task": "strip", "subject": "sub-01", "role": "control"},
             "case-062": {"task": "strip", "subject": "sub-02", "role": "defect"}}

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        pack = root / "graders" / "strip"
        (pack / "rubrics").mkdir(parents=True)
        (pack / "rubrics" / "policy.json").write_text("{}")
        # a scorer that passes anything it is given, so only the gate decides
        (pack / "score.py").write_text(
            "import argparse, json\n"
            "p = argparse.ArgumentParser()\n"
            "p.add_argument('--mask', required=True)\n"
            "p.add_argument('--pack', required=True)\n"
            "p.add_argument('--json', required=True)\n"
            "a = p.parse_args()\n"
            "json.dump({'verdict': 'within_reference_variability', 'quality': 97.0,\n"
            "           'gate_failures': [], 'load_notes': []}, open(a.json, 'w'))\n"
        )
        (root / "harness").mkdir()
        self.manifest = root / "harness" / "run_manifest.json"
        self.manifest.write_text(json.dumps({
            "defaults": {"submission_output_path": "submissions/{task_id}/output.nii.gz",
                         "submission_path": "submissions/{task_id}/{subject}/output.nii.gz"},
            "tasks": {"strip": {"pack_dir": "graders/strip", "scorer": "graders/strip/score.py",
                                "pred_flag": "--mask", "detail_kind": "binary",
                                "optional_inputs": {
                                    "--stripped": "submissions/{task_id}/{subject}/stripped.nii.gz"},
                                "record": "submissions/{task_id}/{subject}/report.json",
                                "per_subject": True}}}))
        self.run = root / "run"

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, case, record=None, files=()):
        d = self.run / "submissions" / "strip" / case
        d.mkdir(parents=True, exist_ok=True)
        if record is not None:
            (d / "report.json").write_text(record if isinstance(record, str) else json.dumps(record))
        for f in files:
            (d / f).touch()

    def grade(self, case):
        with mock.patch.object(grade_wrapper.cases_mod, "load", return_value=self.TABLE):
            return grade_wrapper.grade("strip", self.run, self.manifest, subject=case)

    def test_a_flagged_defect_passes(self):
        self.write("case-062", {"completed": False, "input_usable": False,
                                "reason": "the top of the brain is cut off"})
        env = self.grade("case-062")
        self.assertEqual((env["verdict"], env["score"], env["role"], env["subject"]),
                         ("acceptable", 100.0, "defect", "sub-02"))
        self.assertEqual(env["record"], {"completed": False, "input_usable": False,
                                         "reason": "the top of the brain is cut off"})

    def test_a_flagged_defect_passes_whether_or_not_it_stopped(self):
        for files, stopped in (((), True), (("output.nii.gz",), False), (("stripped.nii.gz",), False)):
            with self.subTest(files=files):
                shutil.rmtree(self.run, ignore_errors=True)
                self.write("case-062", {"completed": True, "input_usable": False, "reason": "x"},
                           files=files)
                env = self.grade("case-062")
                self.assertEqual((env["verdict"], env["score"], env["stopped"]),
                                 ("acceptable", 100.0, stopped))

    def test_a_directory_output_holding_only_the_report_is_no_output(self):
        spec = json.loads(self.manifest.read_text())
        spec["tasks"]["strip"]["submission_output_path"] = "submissions/{task_id}/{subject}"
        self.manifest.write_text(json.dumps(spec))
        self.write("case-062", {"completed": False, "input_usable": False, "reason": "x"})
        self.assertTrue(self.grade("case-062")["stopped"])
        self.write("case-062", files=("output.nii.gz",))
        self.assertFalse(self.grade("case-062")["stopped"])

    def test_a_defect_called_usable_is_a_missed_detection(self):
        for files in ((), ("output.nii.gz",)):
            with self.subTest(files=files):
                self.write("case-062", {"completed": True, "input_usable": True,
                                        "reason": "looks fine"}, files=files)
                env = self.grade("case-062")
                self.assertEqual((env["verdict"], env["score"], env["gate_failures"]),
                                 ("unacceptable", 0.0, []))

    def test_a_defect_without_a_report_fails(self):
        for record in (None, '{"input_usable": "false"}', '{"usable": false}', "not json"):
            with self.subTest(record=record):
                self.write("case-062", record, files=("output.nii.gz",))
                env = self.grade("case-062")
                self.assertEqual(env["gate_failures"], ["record_missing"])

    def test_a_control_called_unusable_is_a_false_alarm_even_with_a_mask(self):
        self.write("case-061", {"input_usable": False, "reason": "x"}, files=("output.nii.gz",))
        env = self.grade("case-061")
        self.assertEqual((env["verdict"], env["role"], env["gate_failures"]),
                         ("invalid", "control", ["usable_input_called_unusable"]))

    def test_a_control_is_scored_with_or_without_a_record(self):
        self.write("case-061", {"input_usable": True, "reason": "fine"}, files=("output.nii.gz",))
        env = self.grade("case-061")
        self.assertEqual((env["verdict"], env["score"]), ("within_reference_variability", 97.0))
        (self.run / "submissions" / "strip" / "case-061" / "report.json").unlink()
        env = self.grade("case-061")
        self.assertEqual((env["verdict"], env["record"]), ("within_reference_variability", None))
        self.assertIn("no report at report.json", env["load_notes"])

    def test_a_task_without_a_record_keeps_the_report_and_scores_the_output(self):
        spec = json.loads(self.manifest.read_text())
        del spec["tasks"]["strip"]["record"]
        spec["defaults"]["run_report_path"] = "submissions/{task_id}/{subject}/report.json"
        self.manifest.write_text(json.dumps(spec))
        report = {"completed": True, "input_usable": False, "reason": "heavy motion"}
        for case in ("case-061", "case-062"):
            with self.subTest(case=case):
                self.write(case, report, files=("output.nii.gz",))
                env = self.grade(case)
                self.assertEqual((env["verdict"], env["record"], env["record_graded"]),
                                 ("within_reference_variability", report, False))

if __name__ == "__main__":
    unittest.main()
