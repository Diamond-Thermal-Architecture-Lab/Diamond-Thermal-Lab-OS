from __future__ import annotations

import re


ID_PATTERNS = {
    "evidence": re.compile(r"^EVD-[0-9]{3}$"),
    "measurement": re.compile(r"^MSR-[0-9]{3}$"),
    "prediction_reality": re.compile(r"^PRL-[0-9]{3}$"),
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def valid_id(kind: str, value: object) -> bool:
    return isinstance(value, str) and bool(ID_PATTERNS[kind].fullmatch(value))


def valid_sha256(value: object) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))
