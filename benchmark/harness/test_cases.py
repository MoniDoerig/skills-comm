"""cases.py without the Hub: the lookups on a cases table held in memory."""
import unittest

from benchmark.harness import cases

# Ids below case-100 are never drawn for real cases, and the subjects are placeholders.
TABLE = {
    "case-012": {"task": "structural-brain-extraction", "subject": "sub-a"},
    "case-011": {"task": "structural-brain-extraction", "subject": "sub-b"},
    "case-013": {"task": "structural-brain-extraction-7t", "subject": "sub-c"},
    "case-021": {"task": "diffusion-tensor-fit", "subject": "sub-d", "role": "control"},
    "case-022": {"task": "diffusion-tensor-fit", "subject": "sub-e", "role": "defect"},
}


class Cases(unittest.TestCase):
    def test_subjects_of_a_task_in_case_order(self):
        self.assertEqual(cases.subjects_of(TABLE, "structural-brain-extraction"), ["sub-b", "sub-a"])
        self.assertEqual(cases.subjects_of(TABLE, "structural-brain-extraction-7t"), ["sub-c"])
        self.assertEqual(cases.subjects_of(TABLE, "diffusion-brain-mask"), [])

    def test_a_case_resolves_to_its_subject(self):
        self.assertEqual(cases.resolve(TABLE, "structural-brain-extraction", "case-012"), "sub-a")

    def test_a_subject_passes_through(self):
        self.assertEqual(cases.resolve(TABLE, "structural-brain-extraction", "sub-a"), "sub-a")

    def test_a_case_of_another_task_is_refused(self):
        with self.assertRaises(SystemExit):
            cases.resolve(TABLE, "structural-brain-extraction", "case-013")

    def test_a_role_is_found_by_case_or_by_subject(self):
        self.assertEqual(cases.role_of(TABLE, "diffusion-tensor-fit", "case-022"), "defect")
        self.assertEqual(cases.role_of(TABLE, "diffusion-tensor-fit", "sub-d"), "control")

    def test_a_case_without_a_role_has_none(self):
        self.assertIsNone(cases.role_of(TABLE, "structural-brain-extraction", "case-012"))
        self.assertIsNone(cases.role_of(TABLE, "structural-brain-extraction", "sub-a"))

    def test_another_tasks_case_lends_no_role(self):
        self.assertIsNone(cases.role_of(TABLE, "structural-brain-extraction", "case-022"))


if __name__ == "__main__":
    unittest.main()
