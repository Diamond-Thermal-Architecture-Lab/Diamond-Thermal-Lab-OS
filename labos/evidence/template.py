from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .ids import valid_id
from .loader import read_case_id, require_case, safe_sidecar_output


def _write_json_atomically(path: Path, data: dict[str, Any], force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"Output already exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    fd, temporary_name = tempfile.mkstemp(prefix=".labos-", suffix=".json", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def create_evidence_template(case_path: Path, evidence_id: str, evidence_type: str, output: Path, force: bool = False) -> dict[str, Any]:
    case_path = require_case(case_path)
    if not valid_id("evidence", evidence_id):
        raise ValueError("evidence_id must use the format EVD-001.")
    if evidence_type not in {"measurement", "simulation", "literature", "supplier_claim", "expert_judgment", "production_data", "field_data"}:
        raise ValueError("evidence type must be an allowed Evidence Object type.")
    target = safe_sidecar_output(case_path, output, "evidence")
    data: dict[str, Any] = {
        "applicability": "TODO: define applicable configuration and limits.",
        "case_id": read_case_id(case_path),
        "confidentiality_level": "internal",
        "contradicts_claim_ids": [],
        "evidence_format_version": "1.0",
        "evidence_id": evidence_id,
        "evidence_level": "unverified",
        "evidence_type": evidence_type,
        "measurement_reference_ids": [],
        "method_summary": "TODO: document method, input basis, and limitations without raw data.",
        "public_summary": "TODO: add a public-safe summary after review.",
        "review_notes": "",
        "reviewed_by": "",
        "source": {"reference": "TODO: controlled source reference", "sha256": None},
        "status": "draft",
        "supports_claim_ids": [],
        "title": "TODO: concise evidence title",
        "uncertainty_summary": "TODO: state uncertainty, limitations, and applicability bounds.",
    }
    _write_json_atomically(target, data, force)
    return data


def create_measurement_template(case_path: Path, measurement_id: str, evidence_id: str, output: Path, force: bool = False) -> dict[str, Any]:
    case_path = require_case(case_path)
    if not valid_id("measurement", measurement_id):
        raise ValueError("measurement_id must use the format MSR-001.")
    target = safe_sidecar_output(case_path, output, "measurements")
    data: dict[str, Any] = {
        "case_id": read_case_id(case_path),
        "confidentiality_level": "internal",
        "evidence_id": evidence_id,
        "measurement_format_version": "1.0",
        "measurement_id": measurement_id,
        "method": "TODO: identify measurement or data-collection method.",
        "operating_conditions": "TODO: record bounded operating conditions.",
        "quantity": "TODO",
        "raw_data_reference": "TODO: controlled opaque reference; do not copy raw data.",
        "raw_data_sha256": None,
        "review_notes": "",
        "reviewed_by": "",
        "sample_id": "ANON-TODO",
        "status": "planned",
        "uncertainty": {"basis": "TODO: state uncertainty basis and limitations.", "numeric_value": None, "unit": None},
        "unit": None,
        "value": None,
    }
    _write_json_atomically(target, data, force)
    return data


def create_prediction_reality_template(case_path: Path, record_id: str, measurement_id: str, output: Path, force: bool = False) -> dict[str, Any]:
    case_path = require_case(case_path)
    if not valid_id("prediction_reality", record_id):
        raise ValueError("record_id must use the format PRL-001.")
    target = safe_sidecar_output(case_path, output, "prediction_reality")
    data: dict[str, Any] = {
        "candidate_error_sources": ["unknown"],
        "case_id": read_case_id(case_path),
        "comparison_context": "TODO: define comparable configuration and operating conditions.",
        "confidentiality_level": "internal",
        "decision_impact": "TODO: describe decision impact without changing a decision automatically.",
        "learning_disposition": "pending_review",
        "prediction": {
            "input_reference": "TODO: controlled input reference",
            "input_sha256": None,
            "lower_bound": None,
            "model_name": "TODO",
            "model_version": "TODO",
            "unit": None,
            "upper_bound": None,
            "value": None,
        },
        "prediction_evidence_ids": [],
        "prediction_reality_format_version": "1.0",
        "quantity": "TODO",
        "reality_measurement_id": measurement_id,
        "record_id": record_id,
        "review_notes": "",
        "reviewed_by": "",
        "status": "draft",
    }
    _write_json_atomically(target, data, force)
    return data
