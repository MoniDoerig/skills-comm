import json
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
