from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable


TREE_HASH_ALGORITHM = "labos-tree-sha256-v1"
_GIT_OBJECT_OID_RE = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")


@dataclass(frozen=True)
class NewlineMetadata:
    crlf_count: int
    lf_count: int
    bare_cr_count: int
    utf8_bom: bool
    final_newline: bool


@dataclass(frozen=True)
class FileDigest:
    path: str
    byte_length: int
    sha256: str
    newline: NewlineMetadata


@dataclass(frozen=True)
class GitBlobDigest:
    ref: str
    path: str
    git_blob_oid: str
    byte_length: int
    sha256: str
    newline: NewlineMetadata


@dataclass(frozen=True)
class TreeFileDigest:
    path: str
    byte_length: int
    sha256: str


@dataclass(frozen=True)
class TreeDigest:
    algorithm: str
    sha256: str
    files: tuple[TreeFileDigest, ...]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def analyze_newlines(data: bytes) -> NewlineMetadata:
    crlf_count = data.count(b"\r\n")
    lf_count = data.count(b"\n")
    bare_cr_count = 0
    index = 0
    while True:
        index = data.find(b"\r", index)
        if index == -1:
            break
        if index + 1 >= len(data) or data[index + 1 : index + 2] != b"\n":
            bare_cr_count += 1
        index += 1
    return NewlineMetadata(
        crlf_count=crlf_count,
        lf_count=lf_count,
        bare_cr_count=bare_cr_count,
        utf8_bom=data.startswith(b"\xef\xbb\xbf"),
        final_newline=data.endswith(b"\n") or data.endswith(b"\r"),
    )


def digest_file(path: Path, *, display_path: str | None = None) -> FileDigest:
    if path.is_symlink():
        raise ValueError(f"refusing to hash symlinked file: {path}")
    if not path.is_file():
        raise ValueError(f"not a regular file: {path}")
    data = path.read_bytes()
    return FileDigest(
        path=(display_path if display_path is not None else _posix_path(path)),
        byte_length=len(data),
        sha256=sha256_bytes(data),
        newline=analyze_newlines(data),
    )


def normalized_lf_bytes(data: bytes) -> bytes:
    text = data.decode("utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.encode("utf-8")


def normalized_lf_sha256(path: Path) -> str:
    if path.is_symlink():
        raise ValueError(f"refusing to hash symlinked file: {path}")
    return sha256_bytes(normalized_lf_bytes(path.read_bytes()))


def digest_git_blob(repo_root: Path, ref: str, repo_relative_path: str) -> GitBlobDigest:
    repo_root = repo_root.resolve()
    if not repo_root.is_dir():
        raise ValueError(f"repo_root is not a directory: {repo_root}")
    safe_path = _validate_relative_input(repo_relative_path)
    try:
        oid_result = subprocess.run(
            ["git", "rev-parse", f"{ref}:{safe_path}"],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        oid = oid_result.stdout.strip()
        if not _GIT_OBJECT_OID_RE.fullmatch(oid):
            raise ValueError(f"unexpected Git blob oid for {safe_path}: {oid}")
        blob_result = subprocess.run(
            ["git", "cat-file", "blob", oid],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr
        raise ValueError(f"could not read Git blob {ref}:{safe_path}: {detail}".strip()) from exc
    data = blob_result.stdout
    return GitBlobDigest(
        ref=ref,
        path=safe_path,
        git_blob_oid=oid,
        byte_length=len(data),
        sha256=sha256_bytes(data),
        newline=analyze_newlines(data),
    )


def digest_tree(
    root: Path,
    *,
    include_paths: Iterable[str] | None = None,
    exclude_paths: Iterable[str] = (),
    ignored_directory_names: Iterable[str] = (),
    ignored_file_suffixes: Iterable[str] = (),
) -> TreeDigest:
    root = root.resolve()
    if root.is_symlink():
        raise ValueError(f"refusing to hash symlinked root: {root}")
    if not root.is_dir():
        raise ValueError(f"tree root is not a directory: {root}")

    excludes = tuple(_validate_relative_input(path).rstrip("/") for path in exclude_paths)
    ignored_dirs = frozenset(ignored_directory_names)
    ignored_suffixes = tuple(ignored_file_suffixes)

    selected: dict[str, Path] = {}
    include_values = list(include_paths) if include_paths is not None else ["."]
    for include_value in include_values:
        include_path_text = "." if include_value == "." else _validate_relative_input(include_value)
        include_path = _resolve_inside(root, include_path_text)
        if include_path.is_symlink():
            raise ValueError(f"refusing to hash symlinked include: {include_value}")
        if not include_path.exists():
            raise ValueError(f"included path does not exist: {include_value}")
        if include_path.is_file():
            rel = _relative_posix(root, include_path)
            if not _is_excluded(rel, excludes) and not _is_ignored(rel, ignored_dirs, ignored_suffixes):
                selected[rel] = include_path
            continue
        if not include_path.is_dir():
            raise ValueError(f"included path is not a regular file or directory: {include_value}")
        for dirpath, dirnames, filenames in os.walk(include_path, topdown=True, followlinks=False):
            current_dir = Path(dirpath)
            rel_dir = _relative_posix(root, current_dir)
            if rel_dir != "." and _is_excluded(rel_dir, excludes):
                dirnames[:] = []
                continue
            for dirname in list(dirnames):
                child = current_dir / dirname
                child_rel = _relative_posix(root, child)
                if dirname in ignored_dirs or _is_excluded(child_rel, excludes):
                    dirnames.remove(dirname)
                    continue
                if child.is_symlink():
                    raise ValueError(f"refusing to hash symlinked directory: {child_rel}")
            for filename in filenames:
                child = current_dir / filename
                rel = _relative_posix(root, child)
                if _is_excluded(rel, excludes) or _is_ignored(rel, ignored_dirs, ignored_suffixes):
                    continue
                if child.is_symlink():
                    raise ValueError(f"refusing to hash symlinked file: {rel}")
                if not child.is_file():
                    continue
                selected.setdefault(rel, child)

    records: list[TreeFileDigest] = []
    tree_hash = hashlib.sha256()
    for rel in sorted(selected):
        data = selected[rel].read_bytes()
        rel_bytes = rel.encode("utf-8")
        tree_hash.update(len(rel_bytes).to_bytes(4, "big"))
        tree_hash.update(rel_bytes)
        tree_hash.update(len(data).to_bytes(8, "big"))
        tree_hash.update(data)
        records.append(TreeFileDigest(path=rel, byte_length=len(data), sha256=sha256_bytes(data)))
    return TreeDigest(algorithm=TREE_HASH_ALGORITHM, sha256=tree_hash.hexdigest(), files=tuple(records))


def _validate_relative_input(path_text: str) -> str:
    if not isinstance(path_text, str) or path_text == "":
        raise ValueError("path must be a non-empty repository-relative path")
    if "\\" in path_text:
        raise ValueError(f"path must use POSIX separators: {path_text}")
    if path_text.startswith("/"):
        raise ValueError(f"absolute paths are not allowed: {path_text}")
    if PureWindowsPath(path_text).drive:
        raise ValueError(f"drive-qualified paths are not allowed: {path_text}")
    if "//" in path_text:
        raise ValueError(f"empty path components are not allowed: {path_text}")
    parts = PurePosixPath(path_text).parts
    if any(part in ("..", "") for part in parts):
        raise ValueError(f"path traversal is not allowed: {path_text}")
    return PurePosixPath(path_text).as_posix()


def _resolve_inside(root: Path, path_text: str) -> Path:
    candidate = (root / Path(*PurePosixPath(path_text).parts)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes root: {path_text}") from exc
    return candidate


def _relative_posix(root: Path, path: Path) -> str:
    path = path.resolve()
    try:
        rel = path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes root: {path}") from exc
    return _posix_path(rel)


def _posix_path(path: Path) -> str:
    return PurePosixPath(*path.parts).as_posix()


def _is_excluded(rel: str, excludes: tuple[str, ...]) -> bool:
    return any(rel == exclude or rel.startswith(exclude + "/") for exclude in excludes)


def _is_ignored(rel: str, ignored_dirs: frozenset[str], ignored_suffixes: tuple[str, ...]) -> bool:
    parts = PurePosixPath(rel).parts
    if any(part in ignored_dirs for part in parts):
        return True
    return any(rel.endswith(suffix) for suffix in ignored_suffixes)
