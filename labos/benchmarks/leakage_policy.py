from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from labos.benchmarks.integrity import sha256_bytes


PRIVATE_LEAKAGE_POLICY_FILENAME = "PRIVATE_LEAKAGE_POLICY.json"

LEAKAGE_CATEGORIES = (
    "expected_rule",
    "expected_score",
    "expected_status",
    "known_error_label",
    "outcome",
    "result_explanation",
    "rule_fix",
    "source_identity",
    "trigger_rewrite",
)

LEAKAGE_MATCH_MODES = (
    "literal",
    "nfkc_casefold",
)

_TOP_LEVEL_KEYS = frozenset({"policy_version", "tokens"})
_TOKEN_KEYS = frozenset({"token_id", "category", "match_mode", "value"})
_TOKEN_ID_RE = re.compile(r"^LKG-[0-9]{4,8}$")


@dataclass(frozen=True, repr=False)
class LeakageToken:
    token_id: str
    category: str
    match_mode: str
    value: str
    match_value: str


@dataclass(frozen=True, repr=False)
class PrivateLeakagePolicy:
    policy_version: str
    tokens: tuple[LeakageToken, ...]


@dataclass(frozen=True, repr=False)
class LoadedPrivateLeakagePolicy:
    policy: PrivateLeakagePolicy
    byte_length: int
    sha256: str


@dataclass(frozen=True)
class PrivateLeakagePolicySummary:
    valid: bool
    policy_version: str
    token_count: int
    byte_length: int
    sha256: str


def parse_private_leakage_policy_bytes(data: bytes) -> PrivateLeakagePolicy:
    try:
        decoded = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("private leakage policy must be valid UTF-8") from exc
    try:
        payload = json.loads(decoded, object_pairs_hook=_reject_duplicate_object_keys)
    except json.JSONDecodeError as exc:
        raise ValueError("private leakage policy JSON is malformed") from exc
    except ValueError as exc:
        raise ValueError("private leakage policy JSON contains a duplicate key") from exc
    return _policy_from_payload(payload)


def load_private_leakage_policy(
    *,
    repo_root: Path,
    policy_root: Path,
    additional_forbidden_roots: Iterable[Path] = (),
) -> LoadedPrivateLeakagePolicy:
    resolved_policy_root = _validate_external_policy_storage(
        repo_root=repo_root,
        policy_root=policy_root,
        additional_forbidden_roots=additional_forbidden_roots,
    )
    policy_path = resolved_policy_root / PRIVATE_LEAKAGE_POLICY_FILENAME
    data = _read_policy_bytes(policy_path)
    policy = parse_private_leakage_policy_bytes(data)
    return LoadedPrivateLeakagePolicy(
        policy=policy,
        byte_length=len(data),
        sha256=sha256_bytes(data),
    )


def summarize_private_leakage_policy(
    loaded: LoadedPrivateLeakagePolicy,
) -> PrivateLeakagePolicySummary:
    if not isinstance(loaded, LoadedPrivateLeakagePolicy):
        raise ValueError("loaded private leakage policy has invalid type")
    return PrivateLeakagePolicySummary(
        valid=True,
        policy_version=loaded.policy.policy_version,
        token_count=len(loaded.policy.tokens),
        byte_length=loaded.byte_length,
        sha256=loaded.sha256,
    )


def _policy_from_payload(payload: object) -> PrivateLeakagePolicy:
    if not isinstance(payload, dict) or set(payload) != _TOP_LEVEL_KEYS:
        raise ValueError("private leakage policy has unknown, missing, or invalid top-level keys")
    if payload["policy_version"] != "1.0":
        raise ValueError("private leakage policy_version must equal 1.0")
    token_payloads = payload["tokens"]
    if not isinstance(token_payloads, list) or not token_payloads:
        raise ValueError("private leakage policy tokens must be a non-empty list")

    tokens: list[LeakageToken] = []
    seen_ids: set[str] = set()
    seen_signatures: dict[tuple[str, str], str] = {}
    previous_id = ""
    for index, token_payload in enumerate(token_payloads):
        token = _token_from_payload(token_payload, index)
        if token.token_id <= previous_id:
            raise ValueError(f"token record {index} is not sorted by opaque token ID")
        previous_id = token.token_id
        if token.token_id in seen_ids:
            raise ValueError(f"opaque token ID {token.token_id} is duplicated")
        seen_ids.add(token.token_id)
        signature = (token.match_mode, token.match_value)
        prior_id = seen_signatures.get(signature)
        if prior_id is not None:
            raise ValueError(f"opaque token ID {token.token_id} has a duplicate matching signature")
        seen_signatures[signature] = token.token_id
        tokens.append(token)

    return PrivateLeakagePolicy(policy_version="1.0", tokens=tuple(tokens))


def _token_from_payload(payload: object, index: int) -> LeakageToken:
    if not isinstance(payload, dict) or set(payload) != _TOKEN_KEYS:
        raise ValueError(f"token record {index} has unknown, missing, or invalid keys")
    token_id = payload["token_id"]
    if not isinstance(token_id, str) or not _TOKEN_ID_RE.fullmatch(token_id):
        raise ValueError(f"token record {index} has an invalid opaque token ID")
    category = payload["category"]
    if category not in LEAKAGE_CATEGORIES:
        raise ValueError(f"token record {index} has an invalid category")
    match_mode = payload["match_mode"]
    if match_mode not in LEAKAGE_MATCH_MODES:
        raise ValueError(f"token record {index} has an invalid match mode")
    value = payload["value"]
    if not isinstance(value, str):
        raise ValueError(f"token record {index} has a non-string value")
    _validate_token_value(value, index)
    match_value = value if match_mode == "literal" else _nfkc_casefold(value)
    if match_mode == "nfkc_casefold" and not match_value:
        raise ValueError(f"token record {index} has an empty normalized value")
    return LeakageToken(
        token_id=token_id,
        category=category,
        match_mode=match_mode,
        value=value,
        match_value=match_value,
    )


def _validate_token_value(value: str, index: int) -> None:
    length = len(value)
    if length < 3:
        raise ValueError(f"token record {index} value is shorter than 3 code points")
    if length > 1024:
        raise ValueError(f"token record {index} value is longer than 1024 code points")
    if value[0].isspace() or value[-1].isspace():
        raise ValueError(f"token record {index} value has leading or trailing whitespace")
    if "\n" in value:
        raise ValueError(f"token record {index} value contains LF")
    if "\r" in value:
        raise ValueError(f"token record {index} value contains CR")
    if "\x00" in value:
        raise ValueError(f"token record {index} value contains NUL")


def _nfkc_casefold(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def _reject_duplicate_object_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _validate_external_policy_storage(
    *,
    repo_root: Path,
    policy_root: Path,
    additional_forbidden_roots: Iterable[Path],
) -> Path:
    resolved_repo_root = _resolve_existing_directory(repo_root, "repository root")
    resolved_policy_root = _resolve_existing_directory(policy_root, "private leakage policy storage")
    forbidden_roots = [resolved_repo_root]
    for root in additional_forbidden_roots:
        forbidden_roots.append(_resolve_existing_directory(root, "forbidden root"))
    for forbidden_root in forbidden_roots:
        if _paths_overlap(resolved_policy_root, forbidden_root):
            raise ValueError("private leakage policy storage overlaps a forbidden root")
    return resolved_policy_root


def _resolve_existing_directory(path: Path, label: str) -> Path:
    if path.is_symlink():
        raise ValueError(f"{label} must be a non-symlink directory")
    if not path.exists() or not path.is_dir():
        raise ValueError(f"{label} must be an existing directory")
    return path.resolve()


def _read_policy_bytes(path: Path) -> bytes:
    if path.is_symlink():
        raise ValueError("private leakage policy file is not a regular non-symlink file")
    if not path.exists():
        raise ValueError("private leakage policy file is missing")
    if not path.is_file():
        raise ValueError("private leakage policy file is not a regular non-symlink file")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise ValueError("private leakage policy file could not be read") from exc
    if not data:
        raise ValueError("private leakage policy file is empty")
    return data


def _paths_overlap(first: Path, second: Path) -> bool:
    try:
        first.relative_to(second)
        return True
    except ValueError:
        try:
            second.relative_to(first)
            return True
        except ValueError:
            return False
