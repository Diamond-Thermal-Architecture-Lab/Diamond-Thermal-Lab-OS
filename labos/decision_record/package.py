from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import ReviewPackageContext


REQUIRED_REVIEW_PACKAGE_FILES = (
    "review_manifest.json",
    "decision_board_preview.json",
    "decision_board_preview.md",
    "human_review_checklist.md",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON: {path.name}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"JSON document must be an object: {path.name}")
    return data


def load_verified_review_package(review_package_dir: Path) -> ReviewPackageContext:
    package_path = review_package_dir.resolve(strict=True)
    if not package_path.is_dir():
        raise ValueError(f"Review package path is not a directory: {review_package_dir}")
    missing = [name for name in REQUIRED_REVIEW_PACKAGE_FILES if not (package_path / name).is_file()]
    if missing:
        raise ValueError(f"Review package is incomplete: {', '.join(missing)}")

    manifest_path = package_path / "review_manifest.json"
    manifest = load_json(manifest_path)
    artifact_hashes = manifest.get("generated_artifact_sha256")
    if not isinstance(artifact_hashes, dict):
        raise ValueError("Review manifest is missing generated_artifact_sha256.")
    if "review_manifest.json" in artifact_hashes:
        raise ValueError("Review manifest must not include its own hash.")
    for name in ("decision_board_preview.md", "decision_board_preview.json", "human_review_checklist.md"):
        expected = artifact_hashes.get(name)
        if not isinstance(expected, str):
            raise ValueError(f"Review manifest is missing artifact hash: {name}")
        actual = sha256_file(package_path / name)
        if actual != expected:
            raise ValueError(f"Review package artifact hash mismatch: {name}")

    decision_board = load_json(package_path / "decision_board_preview.json")
    return ReviewPackageContext(
        path=package_path,
        manifest=manifest,
        manifest_sha256=sha256_file(manifest_path),
        decision_board=decision_board,
    )
