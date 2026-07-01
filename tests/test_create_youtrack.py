import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "kirpr", "scripts"))
import create_youtrack as cy  # noqa: E402


def make_plan(**over):
    plan = {
        "tracker": "youtrack",
        "parent": "SAS-200",
        "tasks": [
            {"key": "01-schema", "summary": "Schema", "description": "body A"},
            {"key": "02-model", "summary": "Model", "description": "body B"},
        ],
        "edges": [{"from": "01-schema", "to": "02-model"}],
    }
    plan.update(over)
    return plan


class TestValidatePlan(unittest.TestCase):
    def test_valid_plan_passes(self):
        cy.validate_plan(make_plan())  # no raise

    def test_missing_parent_raises(self):
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(make_plan(parent=""))

    def test_empty_tasks_raises(self):
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(make_plan(tasks=[]))

    def test_task_missing_field_raises(self):
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(make_plan(tasks=[{"key": "x", "summary": "y"}]))

    def test_duplicate_key_raises(self):
        dup = [
            {"key": "a", "summary": "s", "description": "d"},
            {"key": "a", "summary": "s", "description": "d"},
        ]
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(make_plan(tasks=dup, edges=[]))

    def test_edge_unknown_key_raises(self):
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(make_plan(edges=[{"from": "01-schema", "to": "ghost"}]))

    def test_cycle_raises(self):
        edges = [
            {"from": "01-schema", "to": "02-model"},
            {"from": "02-model", "to": "01-schema"},
        ]
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(make_plan(edges=edges))


class TestDetectCycle(unittest.TestCase):
    def test_acyclic_returns_none(self):
        self.assertIsNone(cy.detect_cycle(["a", "b"], [{"from": "a", "to": "b"}]))

    def test_cycle_returns_path(self):
        cyc = cy.detect_cycle(["a", "b"], [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}])
        self.assertIsNotNone(cyc)


class TestLoadPlan(unittest.TestCase):
    def test_bad_json_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "plan.json")
            with open(p, "w", encoding="utf-8") as f:
                f.write("{ not json")
            with self.assertRaises(cy.PlanError):
                cy.load_plan(p)

    def test_missing_file_raises(self):
        with self.assertRaises(cy.PlanError):
            cy.load_plan("/nonexistent/dir/plan.json")


class TestValidatePlanRobustness(unittest.TestCase):
    def test_non_dict_plan_raises(self):
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(["not", "a", "dict"])

    def test_non_dict_task_raises(self):
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(make_plan(tasks=["not-a-dict"], edges=[]))

    def test_non_dict_edge_raises(self):
        with self.assertRaises(cy.PlanError):
            cy.validate_plan(make_plan(edges=["not-a-dict"]))


if __name__ == "__main__":
    unittest.main()
