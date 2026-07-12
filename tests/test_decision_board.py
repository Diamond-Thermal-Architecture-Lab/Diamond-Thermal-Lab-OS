from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from labos.decision_board.builder import build_decision_board
from labos.triage.engine import triage_case


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "labos_case.py"
EXAMPLE_CASE = REPO_ROOT / "cases" / "example-incomplete-gan-rf-pa"


def write_case(path: Path, *, patterns: str = "", geometry: str = "defined die area", power: str = "defined power density", boundary: str = "defined heat sink boundary") -> None:
    path.mkdir(parents=True)
    (path / "00_problem_intake.yml").write_text(
        f"""case_id: decision-board-case
title: Decision Board case
application: RF
device_type: GaN RF PA
customer_question: architecture screening
heat_source_geometry: {geometry}
power_or_power_density: {power}
current_material_stack: package_path defined; interface thermal resistance bounded
cooling_boundary: {boundary}
target_temperature_or_margin: improve margin
known_data: []
missing_data: []
confidentiality_level: public
""",
        encoding="utf-8",
    )
    if patterns:
        (path / "03_architecture_genomes.yml").write_text(patterns, encoding="utf-8")


def file_hashes(case_path: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(case_path.glob("[0-1][0-9]_*.?*") )
        if path.is_file()
    }


class DecisionBoardTests(unittest.TestCase):
    def test_incomplete_example_holds_for_data_and_defers_decision(self) -> None:
        result = build_decision_board(EXAMPLE_CASE)
        self.assertEqual(result.board_status, "HOLD_FOR_DATA")
        self.assertEqual(result.decision_state, "deferred")
        self.assertIn("Defer architecture selection", result.current_decision)

    def test_first_action_matches_triage_next_action(self) -> None:
        triage = triage_case(EXAMPLE_CASE)
        result = build_decision_board(EXAMPLE_CASE)
        self.assertEqual(result.next_actions[0].action, triage.next_best_action)

    def test_candidate_routes_use_canonical_ids_and_do_not_recommend(self) -> None:
        result = build_decision_board(EXAMPLE_CASE)
        self.assertTrue(result.candidate_routes)
        self.assertTrue(all(route.pattern_id.startswith("PAT-") and route.route_role == "screening_candidate" for route in result.candidate_routes))
        self.assertTrue(all("recommendation" in route.note.lower() or "candidate" in route.note.lower() for route in result.candidate_routes))

    def test_alias_normalizes_to_canonical_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_case(path, patterns="architectures:\n  - pattern_id: PAT-DIAMOND-SUBMOUNT\n")
            result = build_decision_board(path)
            self.assertEqual(result.relevant_pattern_ids, ["PAT-DIA-SUBMOUNT-001"])

    def test_gan_on_diamond_and_conventional_route_guardrails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_case(path, patterns="architectures:\n  - pattern_id: PAT-GAN-DIA-001\n  - pattern_id: PAT-CONV-PKG-001\n")
            result = build_decision_board(path)
            routes = {route.pattern_id: route for route in result.candidate_routes}
            self.assertIn("higher-integration-risk", routes["PAT-GAN-DIA-001"].note.lower())
            self.assertIn("legitimate neutral", routes["PAT-CONV-PKG-001"].note.lower())

    def test_diamond_candidate_requires_interface_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_case(
                path,
                patterns="architectures:\n  - pattern_id: PAT-DIA-SUBMOUNT-001\n",
                geometry="TODO",
            )
            result = build_decision_board(path)
            route = result.candidate_routes[0]
            self.assertTrue(any("interface thermal resistance" in item.lower() for item in route.required_validation))

    def test_no_pattern_case_does_not_invent_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_case(path)
            result = build_decision_board(path)
            self.assertEqual(result.candidate_routes, [])
            self.assertTrue(any(rule.rule_id == "BOARD-ROUTE-002" for rule in result.triggered_rules))

    def test_ready_for_human_decision_requires_explicit_comparison_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_case(path, patterns="architectures:\n  - pattern_id: PAT-CONV-PKG-001\n")
            result = build_decision_board(path)
            self.assertNotEqual(result.board_status, "READY_FOR_HUMAN_DECISION")
            (path / "04_design_space_scorecard.md").write_text("comparison_evidence: reviewed\n", encoding="utf-8")
            result = build_decision_board(path)
            self.assertEqual(result.board_status, "READY_FOR_HUMAN_DECISION")
            self.assertEqual(result.decision_state, "human_review_required")

    def test_claims_remain_guarded_for_unvalidated_case(self) -> None:
        result = build_decision_board(EXAMPLE_CASE)
        self.assertTrue(any("Customer-facing performance claims remain blocked" in guardrail for guardrail in result.claim_guardrails))

    def test_json_is_valid_deterministic_and_read_only(self) -> None:
        before = file_hashes(EXAMPLE_CASE)
        command = [sys.executable, str(SCRIPT), "decision-board", str(EXAMPLE_CASE), "--json"]
        first = subprocess.run(command, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        second = subprocess.run(command, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(first.stdout)["board_status"], "HOLD_FOR_DATA")
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(before, file_hashes(EXAMPLE_CASE))

    def test_invalid_path_returns_exit_two(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "decision-board", "cases/not-a-case"],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)


if __name__ == "__main__":
    unittest.main()
