from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATTERN_INDEX = REPO_ROOT / "patterns" / "pattern_index.yml"
PATTERN_START_RE = re.compile(r"^\s*-\s*pattern_id:\s*['\"]?([^'\"\s]+)")
FIELD_RE = re.compile(r"^\s{4}([A-Za-z_][A-Za-z0-9_]*):\s*(.*?)\s*$")
ALIAS_RE = re.compile(r"^\s{6}-\s*([^\s]+)\s*$")


@dataclass(frozen=True)
class PatternIndexEntry:
    pattern_id: str
    aliases: tuple[str, ...] = ()
    file: str = ""
    route_type: str = ""
    maturity_level: str = ""
    typical_use_case: str = ""


def _scalar(value: str) -> str:
    return value.strip().strip("'\"")


def load_pattern_index(index_path: Path = DEFAULT_PATTERN_INDEX) -> list[PatternIndexEntry]:
    """Load the small public pattern index without a YAML dependency."""
    if not index_path.is_file():
        return []

    entries: list[PatternIndexEntry] = []
    current: dict[str, str] | None = None
    aliases: list[str] = []
    in_aliases = False

    def finish_entry() -> None:
        if current is not None and current.get("pattern_id"):
            entries.append(
                PatternIndexEntry(
                    pattern_id=current["pattern_id"],
                    aliases=tuple(aliases),
                    file=current.get("file", ""),
                    route_type=current.get("route_type", ""),
                    maturity_level=current.get("maturity_level", ""),
                    typical_use_case=current.get("typical_use_case", ""),
                )
            )

    for line in index_path.read_text(encoding="utf-8").splitlines():
        start = PATTERN_START_RE.match(line)
        if start:
            finish_entry()
            current = {"pattern_id": _scalar(start.group(1))}
            aliases = []
            in_aliases = False
            continue
        if current is None:
            continue
        if in_aliases:
            alias = ALIAS_RE.match(line)
            if alias:
                aliases.append(_scalar(alias.group(1)))
                continue
            in_aliases = False
        field = FIELD_RE.match(line)
        if field:
            name, value = field.group(1), _scalar(field.group(2))
            if name == "aliases":
                in_aliases = True
            else:
                current[name] = value

    finish_entry()
    return entries


def get_known_pattern_ids(index_path: Path = DEFAULT_PATTERN_INDEX) -> set[str]:
    return {entry.pattern_id for entry in load_pattern_index(index_path)}


def get_known_aliases(index_path: Path = DEFAULT_PATTERN_INDEX) -> set[str]:
    return {alias for entry in load_pattern_index(index_path) for alias in entry.aliases}


def load_known_pattern_ids(index_path: Path = DEFAULT_PATTERN_INDEX) -> set[str]:
    """Backward-compatible canonical pattern ID lookup."""
    return get_known_pattern_ids(index_path)


def patterns_by_id(index_path: Path = DEFAULT_PATTERN_INDEX) -> dict[str, PatternIndexEntry]:
    return {entry.pattern_id: entry for entry in load_pattern_index(index_path)}


def resolve_pattern_id(value: str, index_path: Path = DEFAULT_PATTERN_INDEX) -> str | None:
    for entry in load_pattern_index(index_path):
        if value == entry.pattern_id or value in entry.aliases:
            return entry.pattern_id
    return None


def resolve_pattern_record(value: str, index_path: Path = DEFAULT_PATTERN_INDEX) -> PatternIndexEntry | None:
    canonical_id = resolve_pattern_id(value, index_path)
    return patterns_by_id(index_path).get(canonical_id) if canonical_id else None
