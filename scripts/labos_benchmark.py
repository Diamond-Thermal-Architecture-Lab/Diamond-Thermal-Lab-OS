from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from labos.benchmarks.integrity import (  # noqa: E402
    analyze_newlines,
    digest_file,
    digest_git_blob,
    digest_tree,
    normalized_lf_bytes,
    sha256_bytes,
)


def _print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def _newline_fields(data: bytes) -> dict[str, object]:
    newline = analyze_newlines(data)
    return {
        "bare_cr_count": newline.bare_cr_count,
        "crlf_count": newline.crlf_count,
        "final_newline": newline.final_newline,
        "lf_count": newline.lf_count,
        "utf8_bom": newline.utf8_bom,
    }


def _digest_to_json(mode: str, path: str, data: bytes) -> dict[str, object]:
    return {
        "byte_length": len(data),
        "mode": mode,
        "path": path,
        "sha256": sha256_bytes(data),
        **_newline_fields(data),
    }


def cmd_hash_file(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if args.normalized_lf:
        raw = path.read_bytes()
        data = normalized_lf_bytes(raw)
        result = _digest_to_json("normalized_lf_diagnostic", args.path, data)
    else:
        digest = digest_file(path, display_path=args.path)
        result = {
            "byte_length": digest.byte_length,
            "mode": "exact_bytes",
            "path": digest.path,
            "sha256": digest.sha256,
            **asdict(digest.newline),
        }
    if args.json:
        _print_json(result)
    else:
        print(f"{result['mode']} {result['sha256']} {result['path']}")
    return 0


def cmd_hash_git_object(args: argparse.Namespace) -> int:
    digest = digest_git_blob(Path(args.repo_root), args.ref, args.path)
    result = {
        "byte_length": digest.byte_length,
        "git_blob_oid": digest.git_blob_oid,
        "mode": "committed_git_object",
        "path": digest.path,
        "ref": digest.ref,
        "sha256": digest.sha256,
        **asdict(digest.newline),
    }
    if args.json:
        _print_json(result)
    else:
        print(f"{digest.git_blob_oid} {digest.sha256} {digest.path}")
    return 0


def cmd_hash_tree(args: argparse.Namespace) -> int:
    digest = digest_tree(
        Path(args.root),
        include_paths=args.include,
        exclude_paths=args.exclude,
        ignored_directory_names=args.ignore_directory,
        ignored_file_suffixes=args.ignore_suffix,
    )
    result = {
        "algorithm": digest.algorithm,
        "file_count": len(digest.files),
        "files": [asdict(record) for record in digest.files],
        "root": args.root,
        "sha256": digest.sha256,
    }
    if args.json:
        _print_json(result)
    else:
        print(f"{digest.algorithm} {digest.sha256} files={len(digest.files)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lab OS benchmark integrity helpers.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    hash_file = subparsers.add_parser("hash-file")
    hash_file.add_argument("path")
    hash_file.add_argument("--normalized-lf", action="store_true")
    hash_file.add_argument("--json", action="store_true")
    hash_file.set_defaults(func=cmd_hash_file)

    hash_git_object = subparsers.add_parser("hash-git-object")
    hash_git_object.add_argument("--repo-root", required=True)
    hash_git_object.add_argument("--ref", required=True)
    hash_git_object.add_argument("--path", required=True)
    hash_git_object.add_argument("--json", action="store_true")
    hash_git_object.set_defaults(func=cmd_hash_git_object)

    hash_tree = subparsers.add_parser("hash-tree")
    hash_tree.add_argument("root")
    hash_tree.add_argument("--include", action="append")
    hash_tree.add_argument("--exclude", action="append", default=[])
    hash_tree.add_argument("--ignore-directory", action="append", default=["__pycache__"])
    hash_tree.add_argument("--ignore-suffix", action="append", default=[".pyc", ".pyo"])
    hash_tree.add_argument("--json", action="store_true")
    hash_tree.set_defaults(func=cmd_hash_tree)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
