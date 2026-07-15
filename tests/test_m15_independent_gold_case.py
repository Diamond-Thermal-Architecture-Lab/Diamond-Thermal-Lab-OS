from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "literature-arxiv-2305-thermal-sio2-released-membrane"
CASE = REPO_ROOT / "cases" / CASE_ID
BASELINE = REPO_ROOT / "exports" / f"{CASE_ID}-baseline"
SCRIPT = REPO_ROOT / "scripts" / "labos_case.py"

EXPECTED_BASELINE_HASHES = {
    "decision_board_preview.json": "6a18fadcbdef0295a0cfd9ddbe43f4e99e11ea9bb6a4e9112e9f610ff718bc2e",
    "decision_board_preview.md": "80912cdd40b32c5a8d2f8159c9d9c1c55cd7719c15e6c38c4c6625f766c9f488",
    "human_review_checklist.md": "6ee1ac064f30208361f5d445581b853515505f7d46fb9e230d04137815a2d58c",
    "review_manifest.json": "f00ce5370270c0984bd0023acb886014ccb72ce89028b61c9315b2069cbcdcfb",
    "triage_report.md": "a8f35bc5765f03807da8f0074e533086f034edf407861fd60f8f6db7cc53f248",
    "triage_result.json": "d99a8d6490d64c37736aae8426adeb72b896a009b9f65cc4b6444d3c5dca2b64",
}


class M15BlindBaselineTests(unittest.TestCase):
    def test_blind_case_contains_the_twelve_canonical_files(self) -> None:
        numbered = sorted(path.name for path in CASE.iterdir() if path.is_file() and path.name[:2].isdigit())
        self.assertEqual(numbered, [
            "00_problem_intake.yml",
            "01_thermal_design_passport.yml",
            "02_decision_board.md",
            "03_architecture_genomes.yml",
            "04_design_space_scorecard.md",
            "05_red_flags.md",
            "06_next_best_action.md",
            "07_validation_plan.md",
            "08_supplier_specification.md",
            "09_customer_memo.md",
            "10_claim_ledger.yml",
            "11_engineering_memory_entry.md",
        ])

    def test_frozen_baseline_hashes_match_the_manifest(self) -> None:
        manifest = json.loads((BASELINE / "baseline_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["frozen_artifact_sha256"], EXPECTED_BASELINE_HASHES)
        actual = {
            name: hashlib.sha256((BASELINE / name).read_bytes()).hexdigest()
            for name in manifest["frozen_artifacts"]
        }
        self.assertEqual(actual, EXPECTED_BASELINE_HASHES)
        self.assertNotIn("baseline_manifest.json", manifest["frozen_artifacts"])

    def test_blind_triage_is_deterministic_and_outcome_free(self) -> None:
        command = [sys.executable, str(SCRIPT), "triage", str(CASE), "--json"]
        first = subprocess.run(command, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        second = subprocess.run(command, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        result = json.loads(first.stdout)
        self.assertEqual(result["thermomechanical_screening"]["status"], "not_applicable")
        canonical_text = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in CASE.iterdir()
            if path.is_file() and path.name[:2].isdigit()
        )
        for restricted_term in ("arxiv:2305.15794", "-11.3", "-14.2", "-20.9", "-319 mpa", "-320 mpa", "-323 mpa"):
            self.assertNotIn(restricted_term, canonical_text)


if __name__ == "__main__":
    unittest.main()
