from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from labos.triage.engine import triage_case


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "labos_case.py"


def write_case(path: Path, *, geometry: str = "defined die area", power: str = "defined power density", boundary: str = "defined heat sink boundary", question: str = "overheating symptom", extra: str = "") -> None:
    path.mkdir(parents=True)
    (path / "00_problem_intake.yml").write_text(
        f"""case_id: triage-case
title: Triage case
application: RF
device_type: GaN RF PA
customer_question: {question}
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
    if extra:
        (path / "03_architecture_genomes.yml").write_text(extra, encoding="utf-8")


class TriageEngineTests(unittest.TestCase):
    def test_incomplete_example_needs_data(self) -> None:
        result = triage_case(REPO_ROOT / "cases" / "example-incomplete-gan-rf-pa")
        self.assertEqual(result.status, "NEEDS_DATA")
        self.assertEqual(result.primary_classification, "insufficient_data")

    def test_missing_geometry_prevents_detailed_fem(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_case(path, geometry="TODO")
            result = triage_case(path)
            self.assertIn("heat_source_geometry", result.critical_missing_data)
            self.assertIn("Do not start detailed FEM", result.do_not_do_first[0])

    def test_missing_power_density_triggers_insufficient_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_case(path, power="uncertain")
            result = triage_case(path)
            self.assertEqual(result.primary_classification, "insufficient_data")
            self.assertIn("power_or_power_density", result.critical_missing_data)

    def test_missing_boundary_adds_boundary_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_case(path, boundary="unknown")
            result = triage_case(path)
            self.assertIn("cooling_boundary_limited", result.secondary_classifications)

    def test_diamond_without_interface_evidence_adds_interface_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_case(path, extra="architectures:\n  - pattern_id: PAT-DIAMOND-SUBMOUNT\n")
            (path / "00_problem_intake.yml").write_text((path / "00_problem_intake.yml").read_text().replace("interface thermal resistance bounded", "stack defined"), encoding="utf-8")
            result = triage_case(path)
            self.assertIn("interface_limited_candidate", result.secondary_classifications)
            self.assertIn("PAT-DIA-SUBMOUNT-001", result.relevant_pattern_ids)

    def test_material_candidate_requires_bounded_prerequisites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_case(path, question="architecture screening")
            result = triage_case(path)
            self.assertEqual(result.primary_classification, "material_limited_candidate")
            self.assertEqual(result.confidence, "medium")

    def test_measurement_limited_without_supporting_measurement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_case(path)
            result = triage_case(path)
            self.assertIn("measurement_limited", result.secondary_classifications)

    def test_bounded_interface_does_not_add_unbounded_interface_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_case(
                path,
                question="architecture screening",
                extra="architectures:\n  - pattern_id: PAT-DIAMOND-SUBMOUNT\n",
            )
            result = triage_case(path)
            self.assertNotIn("interface_limited_candidate", result.secondary_classifications)

    def test_interface_uncertainty_does_not_imply_package_uncertainty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_case(path, question="architecture screening")
            intake_path = path / "00_problem_intake.yml"
            intake_path.write_text(
                intake_path.read_text(encoding="utf-8").replace(
                    "interface thermal resistance bounded", "interface thermal resistance unknown"
                ),
                encoding="utf-8",
            )
            result = triage_case(path)
            self.assertNotIn("package_limited_candidate", result.secondary_classifications)

    def test_gan_on_diamond_stays_a_screening_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_case(path, extra="architectures:\n  - pattern_id: PAT-GAN-DIA-001\n")
            result = triage_case(path)
            self.assertIn("PAT-GAN-DIA-001", result.relevant_pattern_ids)
            self.assertTrue(any(rule.rule_id == "TRIAGE-DESIGN-002" for rule in result.triggered_rules))
            self.assertTrue(any("direct GaN-on-Diamond" in item for item in result.do_not_do_first))

    def test_alias_normalizes_and_conventional_route_is_neutral(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_case(
                path,
                extra="architectures:\n  - pattern_id: PAT-CONVENTIONAL-PACKAGE-UPGRADE\n",
            )
            result = triage_case(path)
            self.assertIn("PAT-CONV-PKG-001", result.relevant_pattern_ids)
            self.assertTrue(any(rule.rule_id == "TRIAGE-PACKAGE-002" for rule in result.triggered_rules))

    def test_cli_json_is_valid_and_read_only(self) -> None:
        case_path = REPO_ROOT / "cases" / "example-incomplete-gan-rf-pa"
        before = (case_path / "00_problem_intake.yml").read_bytes()
        completed = subprocess.run([sys.executable, str(SCRIPT), "triage", str(case_path), "--json"], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, check=False)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(json.loads(completed.stdout)["status"], "NEEDS_DATA")
        self.assertEqual(before, (case_path / "00_problem_intake.yml").read_bytes())

    def test_invalid_path_returns_exit_two(self) -> None:
        completed = subprocess.run([sys.executable, str(SCRIPT), "triage", "cases/not-a-case"], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(completed.returncode, 2)


if __name__ == "__main__":
    unittest.main()
