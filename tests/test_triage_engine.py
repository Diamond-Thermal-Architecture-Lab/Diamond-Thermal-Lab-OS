from __future__ import annotations

import json
import hashlib
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


def write_thermomechanical_case(path: Path, extra: str = "") -> None:
    write_case(
        path,
        question="screen direct CVD diamond growth on a suspended membrane",
        extra=extra,
    )
    intake = path / "00_problem_intake.yml"
    intake.write_text(
        intake.read_text(encoding="utf-8").replace(
            "current_material_stack: package_path defined; interface thermal resistance bounded",
            "current_material_stack: direct CVD diamond grown on a suspended membrane",
        ),
        encoding="utf-8",
    )


def write_evidence(
    path: Path,
    evidence_id: str,
    status: str,
    *,
    reviewed_by: str = "",
    measurement_reference_ids: list[str] | None = None,
    case_id: str = "triage-case",
) -> None:
    directory = path / "evidence"
    directory.mkdir(exist_ok=True)
    (directory / f"{evidence_id}.json").write_text(
        json.dumps(
            {
                "evidence_id": evidence_id,
                "status": status,
                "reviewed_by": reviewed_by,
                "measurement_reference_ids": measurement_reference_ids or [],
                "case_id": case_id,
            }
        ),
        encoding="utf-8",
    )


def write_measurement(
    path: Path,
    measurement_id: str,
    evidence_id: str,
    quantity: str,
    status: str = "completed",
    *,
    reviewed_by: str = "",
    case_id: str = "triage-case",
) -> None:
    directory = path / "measurements"
    directory.mkdir(exist_ok=True)
    (directory / f"{measurement_id}.json").write_text(
        json.dumps(
            {
                "measurement_id": measurement_id,
                "evidence_id": evidence_id,
                "status": status,
                "quantity": quantity,
                "value": 1.0,
                "reviewed_by": reviewed_by,
                "case_id": case_id,
            }
        ),
        encoding="utf-8",
    )


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

    def test_gold_case_triggers_thermomechanical_guardrails(self) -> None:
        result = triage_case(REPO_ROOT / "cases" / "literature-2021-diamond-on-gan-membrane-stress")
        rule_ids = {rule.rule_id for rule in result.triggered_rules}
        self.assertEqual(result.thermomechanical_screening["status"], "needs_evidence")
        self.assertIn("thermomechanical_validation_needed", result.secondary_classifications)
        self.assertTrue(
            {
                "TRIAGE-THERMOMECH-001",
                "TRIAGE-THERMOMECH-003",
                "TRIAGE-THERMOMECH-005",
                "TRIAGE-THERMOMECH-006",
            }.issubset(rule_ids)
        )
        rule = next(item for item in result.triggered_rules if item.rule_id == "TRIAGE-THERMOMECH-003")
        self.assertTrue(rule.title)
        self.assertTrue(rule.triggering_inputs)
        self.assertTrue(rule.missing_evidence)
        self.assertTrue(rule.engineering_rationale)
        self.assertTrue(rule.evidence_boundary)

    def test_frozen_gold_case_baseline_is_unchanged(self) -> None:
        baseline = REPO_ROOT / "exports" / "literature-2021-diamond-on-gan-membrane-stress-baseline"
        expected = {
            "decision_board_preview.json": "cbe9fff37b0628e91bfebc0f4e22fe2df687596702174ac135dff061c8759430",
            "decision_board_preview.md": "e38d0651e2a612b08558a35e81181bb76161330054e2f3714a0a81cf21bb5833",
            "human_review_checklist.md": "6ee1ac064f30208361f5d445581b853515505f7d46fb9e230d04137815a2d58c",
            "review_manifest.json": "975a7dd162886b4b3932dbdb6be234071b5be013e51b05eac7c323fb512e81fe",
        }
        actual = {
            name: hashlib.sha256((baseline / name).read_bytes()).hexdigest()
            for name in expected
        }
        self.assertEqual(actual, expected)

    def test_thermomechanical_context_does_not_predict_failure(self) -> None:
        result = triage_case(REPO_ROOT / "cases" / "literature-2021-diamond-on-gan-membrane-stress")
        thermo_findings = [rule.finding.lower() for rule in result.triggered_rules if "THERMOMECH" in rule.rule_id]
        self.assertFalse(any("will fail" in finding or "will crack" in finding or "will delaminate" in finding for finding in thermo_findings))

    def test_missing_process_history_is_a_qualitative_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_thermomechanical_case(path, "growth temperature: unknown")
            result = triage_case(path)
            self.assertIn("TRIAGE-THERMOMECH-002", {rule.rule_id for rule in result.triggered_rules})
            self.assertIn("thermomechanical_validation_needed", result.secondary_classifications)

    def test_fixture_identifiers_do_not_satisfy_thermal_boundary(self) -> None:
        for declaration in ("plasma frequency: 2.45 GHz", "fixture ID: 3", "reactor run 12"):
            with self.subTest(declaration=declaration), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "case"
                write_thermomechanical_case(path, declaration)
                self.assertIn("TRIAGE-THERMOMECH-005", {rule.rule_id for rule in triage_case(path).triggered_rules})

    def test_explicit_fixture_boundary_declaration_and_unknown_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_thermomechanical_case(path, "fixture thermal contact conductance: 1000 W/m2K")
            self.assertNotIn("TRIAGE-THERMOMECH-005", {rule.rule_id for rule in triage_case(path).triggered_rules})
            (path / "03_architecture_genomes.yml").write_text("fixture thermal boundary: unknown", encoding="utf-8")
            self.assertIn("TRIAGE-THERMOMECH-005", {rule.rule_id for rule in triage_case(path).triggered_rules})

    def test_diamond_submount_and_generic_film_do_not_activate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_case(path, extra="diamond submount used below a bulk package")
            self.assertEqual(triage_case(path).thermomechanical_screening["status"], "not_applicable")
            (path / "03_architecture_genomes.yml").write_text("an ordinary thin film is deposited", encoding="utf-8")
            self.assertEqual(triage_case(path).thermomechanical_screening["status"], "not_applicable")

    def test_incomplete_example_remains_thermomechanically_not_applicable(self) -> None:
        result = triage_case(REPO_ROOT / "cases" / "example-incomplete-gan-rf-pa")
        self.assertEqual(result.thermomechanical_screening["status"], "not_applicable")

    def test_missing_cte_and_topic_mentions_do_not_count_as_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_thermomechanical_case(
                path,
                "CTE data are missing\nResidual stress must be investigated.\nBow is an important concern.",
            )
            ids = {rule.rule_id for rule in triage_case(path).triggered_rules}
            self.assertIn("TRIAGE-THERMOMECH-001", ids)
            self.assertIn("TRIAGE-THERMOMECH-003", ids)

    def test_positive_declarations_are_stated_context_not_reviewed_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_thermomechanical_case(
                path,
                "\n".join(
                    (
                        "CTE data documented.", "growth temperature: 800 C", "exposure: 2 hours", "cooling to room temperature.",
                        "stress acceptance documented.", "bow acceptance documented.", "initial and post-process curvature compared.",
                        "adhesion evidence documented.", "fixture thermal boundary defined.",
                    )
                ),
            )
            result = triage_case(path)
            self.assertIn("material-property basis is declared", " ".join(result.thermomechanical_screening["known_inputs"]))
            self.assertEqual(result.thermomechanical_screening["status"], "needs_evidence")
            self.assertNotEqual(result.thermomechanical_screening["status"], "reviewed_evidence_referenced")

    def test_stress_and_bow_acceptance_are_independent(self) -> None:
        cases = (
            ("stress acceptance documented.", ("case-specific bow/warpage/curvature acceptance criteria",)),
            ("bow acceptance documented.", ("case-specific residual-stress acceptance criteria",)),
            ("stress acceptance documented.\nbow acceptance documented.", ()),
            ("", ("case-specific residual-stress acceptance criteria", "case-specific bow/warpage/curvature acceptance criteria")),
        )
        for declarations, expected_missing in cases:
            with self.subTest(declarations=declarations), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "case"
                write_thermomechanical_case(path, declarations)
                rule = next(rule for rule in triage_case(path).triggered_rules if rule.rule_id == "TRIAGE-THERMOMECH-003")
                for criterion in ("case-specific residual-stress acceptance criteria", "case-specific bow/warpage/curvature acceptance criteria"):
                    if criterion in expected_missing:
                        self.assertIn(criterion, rule.missing_evidence)
                    else:
                        self.assertNotIn(criterion, rule.missing_evidence)

    def test_reviewed_measurement_does_not_replace_other_acceptance_basis(self) -> None:
        for quantity, declaration, absent in (
            ("residual stress", "stress acceptance documented.", "case-specific bow/warpage/curvature acceptance criteria"),
            ("membrane bow", "bow acceptance documented.", "case-specific residual-stress acceptance criteria"),
        ):
            with self.subTest(quantity=quantity), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "case"
                write_thermomechanical_case(path, declaration)
                write_evidence(
                    path,
                    "EVD-001",
                    "reviewed",
                    reviewed_by="reviewer",
                    measurement_reference_ids=["MSR-001"],
                )
                write_measurement(path, "MSR-001", "EVD-001", quantity, "reviewed", reviewed_by="reviewer")
                rule = next(rule for rule in triage_case(path).triggered_rules if rule.rule_id == "TRIAGE-THERMOMECH-003")
                self.assertIn(absent, rule.missing_evidence)

    def test_draft_parent_measurement_remains_pending_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_thermomechanical_case(path)
            write_evidence(path, "EVD-001", "draft")
            write_measurement(path, "MSR-001", "EVD-001", "residual stress")
            write_measurement(path, "MSR-002", "EVD-001", "membrane bow")
            result = triage_case(path)
            rule = next(rule for rule in result.triggered_rules if rule.rule_id == "TRIAGE-THERMOMECH-003")
            self.assertIn("stress evidence state: source_pending_review", rule.evidence)
            self.assertIn("pending linked human evidence review", " ".join(result.thermomechanical_screening["evidence_limitations"]))

    def test_reviewed_evidence_requires_reciprocal_case_and_reviewer_binding(self) -> None:
        scenarios = (
            ({"measurement_reference_ids": []}, {}),
            ({"measurement_reference_ids": ["MSR-001"]}, {"case_id": "other-case"}),
            ({"measurement_reference_ids": ["MSR-001"], "reviewed_by": ""}, {}),
        )
        for evidence_kwargs, measurement_kwargs in scenarios:
            with self.subTest(evidence_kwargs=evidence_kwargs, measurement_kwargs=measurement_kwargs), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "case"
                write_thermomechanical_case(path)
                evidence_options = {"reviewed_by": "reviewer", **evidence_kwargs}
                measurement_options = {"reviewed_by": "reviewer", **measurement_kwargs}
                write_evidence(path, "EVD-001", "reviewed", **evidence_options)
                write_measurement(path, "MSR-001", "EVD-001", "residual stress", "reviewed", **measurement_options)
                result = triage_case(path)
                rule = next(rule for rule in result.triggered_rules if rule.rule_id == "TRIAGE-THERMOMECH-003")
                self.assertNotIn("stress evidence state: reviewed", rule.evidence)
                self.assertTrue(result.thermomechanical_screening["evidence_limitations"])

    def test_rejected_parent_is_not_source_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_thermomechanical_case(path)
            write_evidence(path, "EVD-001", "rejected", measurement_reference_ids=["MSR-001"])
            write_measurement(path, "MSR-001", "EVD-001", "residual stress")
            result = triage_case(path)
            rule = next(rule for rule in result.triggered_rules if rule.rule_id == "TRIAGE-THERMOMECH-003")
            self.assertIn("stress evidence state: missing", rule.evidence)
            self.assertIn("rejected or deprecated parent", " ".join(result.thermomechanical_screening["evidence_limitations"]))

    def test_reviewed_parent_and_relevant_measurements_can_be_reviewed_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_thermomechanical_case(
                path,
                "\n".join((
                    "CTE data documented.", "growth temperature: 800 C", "exposure: 2 hours", "cooling to room temperature.",
                    "stress acceptance documented.", "bow acceptance documented.", "initial and post-process curvature compared.",
                    "adhesion evidence documented.", "fixture thermal boundary defined.",
                )),
            )
            write_evidence(
                path,
                "EVD-001",
                "reviewed",
                reviewed_by="reviewer",
                measurement_reference_ids=["MSR-001", "MSR-002"],
            )
            write_measurement(path, "MSR-001", "EVD-001", "residual stress", "reviewed", reviewed_by="reviewer")
            write_measurement(path, "MSR-002", "EVD-001", "membrane bow", "reviewed", reviewed_by="reviewer")
            result = triage_case(path)
            self.assertEqual(result.thermomechanical_screening["status"], "reviewed_evidence_referenced")
            self.assertFalse(any("THERMOMECH" in rule.rule_id for rule in result.triggered_rules))

    def test_unrelated_reviewed_evidence_does_not_promote_draft_measurement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_thermomechanical_case(path)
            write_evidence(path, "EVD-001", "reviewed")
            write_evidence(path, "EVD-002", "draft")
            write_measurement(path, "MSR-001", "EVD-002", "residual stress")
            result = triage_case(path)
            rule = next(rule for rule in result.triggered_rules if rule.rule_id == "TRIAGE-THERMOMECH-003")
            self.assertIn("stress evidence state: source_pending_review", rule.evidence)

    def test_missing_parent_and_malformed_sidecars_are_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_thermomechanical_case(path)
            write_measurement(path, "MSR-001", "EVD-999", "residual stress")
            (path / "evidence").mkdir(exist_ok=True)
            (path / "evidence" / "EVD-001.json").write_text("{not-json", encoding="utf-8")
            result = triage_case(path)
            limitations = result.thermomechanical_screening["evidence_limitations"]
            self.assertIn("MSR-001.json references missing parent Evidence Object EVD-999.", limitations)
            self.assertIn("EVD-001.json is not usable structured evidence.", limitations)

    def test_lateral_dimensions_are_not_thicknesses_and_comparison_can_be_declared(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_thermomechanical_case(path, "diamond thickness: 38 um\nsubstrate thickness: 75 um")
            self.assertNotIn("TRIAGE-THERMOMECH-006", {rule.rule_id for rule in triage_case(path).triggered_rules})
            (path / "03_architecture_genomes.yml").write_text("membrane diameter: 0.5 mm\nmembrane diameter: 2 mm", encoding="utf-8")
            self.assertIn("TRIAGE-THERMOMECH-006", {rule.rule_id for rule in triage_case(path).triggered_rules})
            (path / "03_architecture_genomes.yml").write_text("membrane diameter: 0.5 mm\nmembrane diameter: 2 mm\ndiameter data are available", encoding="utf-8")
            self.assertIn("TRIAGE-THERMOMECH-006", {rule.rule_id for rule in triage_case(path).triggered_rules})
            (path / "03_architecture_genomes.yml").write_text("membrane diameter: 0.5 mm\nmembrane diameter: 2 mm\ncurvature evaluated for each membrane diameter", encoding="utf-8")
            self.assertNotIn("TRIAGE-THERMOMECH-006", {rule.rule_id for rule in triage_case(path).triggered_rules})
            (path / "03_architecture_genomes.yml").write_text("membrane diameter: 0.5 mm\ndiameter data are documented", encoding="utf-8")
            self.assertNotIn("TRIAGE-THERMOMECH-006", {rule.rule_id for rule in triage_case(path).triggered_rules})

    def test_malformed_optional_thermomechanical_sidecar_is_reported_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case"
            write_thermomechanical_case(path)
            (path / "evidence").mkdir()
            (path / "evidence" / "EVD-001.json").write_text("{not-json", encoding="utf-8")
            result = triage_case(path)
            self.assertIn("EVD-001.json is not usable structured evidence.", result.thermomechanical_screening["evidence_limitations"])
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "triage", str(path), "--json"],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(completed.returncode, 0)
            self.assertNotIn("Traceback", completed.stderr)
            self.assertIn("EVD-001.json is not usable structured evidence.", json.loads(completed.stdout)["thermomechanical_screening"]["evidence_limitations"])

    def test_thermomechanical_json_is_deterministic(self) -> None:
        case_path = REPO_ROOT / "cases" / "literature-2021-diamond-on-gan-membrane-stress"
        first = subprocess.run([sys.executable, str(SCRIPT), "triage", str(case_path), "--json"], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, check=False)
        second = subprocess.run([sys.executable, str(SCRIPT), "triage", str(case_path), "--json"], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, check=False)
        self.assertEqual(first.returncode, 0)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(json.loads(first.stdout)["thermomechanical_screening"]["status"], "needs_evidence")

    def test_legacy_rule_dictionaries_omit_empty_thermomechanical_fields(self) -> None:
        result = triage_case(REPO_ROOT / "cases" / "example-incomplete-gan-rf-pa")
        legacy_rule = result.triggered_rules[0].to_dict()
        self.assertNotIn("title", legacy_rule)
        self.assertNotIn("missing_evidence", legacy_rule)


if __name__ == "__main__":
    unittest.main()
