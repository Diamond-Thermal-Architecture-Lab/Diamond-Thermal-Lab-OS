from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


CANONICAL_CASE_FILE = "00_problem_intake.yml"
SIDE_CAR_DIRECTORIES = ("evidence", "measurements", "prediction_reality")
CLAIM_ID_RE = re.compile(r"^\s*-?\s*claim_id:\s*([^\s#]+)", re.MULTILINE)
ABSOLUTE_REFERENCE_RE = re.compile(r"(?:^[A-Za-z]:[\\/]|^/|^\\\\)")
CREDENTIAL_RE = re.compile(r"(?:api[_-]?key|token|password|secret)\s*[:=]", re.IGNORECASE)


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON: {path.name}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"JSON object required: {path.name}")
    return data


def require_case(case_path: Path) -> Path:
    resolved = case_path.resolve(strict=True)
    if not resolved.is_dir() or not (resolved / CANONICAL_CASE_FILE).is_file():
        raise ValueError("Case path must be a readable canonical case folder.")
    return resolved


def read_case_id(case_path: Path) -> str:
    text = (case_path / CANONICAL_CASE_FILE).read_text(encoding="utf-8")
    match = re.search(r"^case_id:\s*[\"']?([^\s\"'#]+)", text, re.MULTILINE)
    return match.group(1) if match else case_path.name


def claim_ids(case_path: Path) -> set[str]:
    path = case_path / "10_claim_ledger.yml"
    if not path.is_file():
        return set()
    return set(CLAIM_ID_RE.findall(path.read_text(encoding="utf-8")))


def sidecar_path(case_path: Path, folder: str, object_id: str) -> Path:
    return case_path / folder / f"{object_id}.json"


def safe_sidecar_output(case_path: Path, output: Path, folder: str) -> Path:
    case_path = require_case(case_path)
    candidate = output if output.is_absolute() else Path.cwd() / output
    resolved_parent = candidate.parent.resolve(strict=False)
    target = (resolved_parent / candidate.name).resolve(strict=False)
    allowed = (case_path / folder).resolve(strict=False)
    if target.parent != allowed or target.suffix.lower() != ".json":
        raise ValueError(f"Output must be a JSON file directly under {folder}/ for this case.")
    return target


def iter_sidecar_json(case_path: Path, folder: str) -> list[Path]:
    directory = case_path / folder
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".json")


def unsafe_reference(value: object) -> bool:
    if not isinstance(value, str):
        return False
    return bool(ABSOLUTE_REFERENCE_RE.search(value) or CREDENTIAL_RE.search(value))


def scalar_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""
