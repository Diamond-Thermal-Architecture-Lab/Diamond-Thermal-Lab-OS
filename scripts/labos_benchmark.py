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
from labos.benchmarks.sealed_manifest import (  # noqa: E402
    build_sealed_manifest,
    find_sealed_presence,
    load_sealed_manifest,
    verify_sealed_manifest,
    write_new_sealed_manifest,
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
    display_path = path.as_posix()
    if args.normalized_lf:
        if path.is_symlink():
            raise ValueError(f"refusing to hash symlinked file: {path}")
        if not path.is_file():
            raise ValueError(f"not a regular file: {path}")
        raw = path.read_bytes()
        data = normalized_lf_bytes(raw)
        result = _digest_to_json("normalized_lf_diagnostic", display_path, data)
    else:
        digest = digest_file(path, display_path=display_path)
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
        "root": Path(args.root).as_posix(),
        "sha256": digest.sha256,
    }
    if args.json:
        _print_json(result)
    else:
        print(f"{digest.algorithm} {digest.sha256} files={len(digest.files)}")
    return 0


def cmd_build_sealed_manifest(args: argparse.Namespace) -> int:
    manifest = build_sealed_manifest(
        repo_root=Path(args.repo_root),
        sealed_root=Path(args.sealed_root),
        artifact_filenames=args.artifact_filename,
        protocol_version=args.protocol_version,
        registered_at_utc=args.registered_at,
        additional_forbidden_roots=[Path(path) for path in args.forbidden_root],
    )
    output = Path(args.output)
    write_new_sealed_manifest(output, manifest, sealed_root=Path(args.sealed_root))
    _print_json(
        {
            "artifact_count": len(manifest.sealed_artifacts),
            "filenames": [record.filename for record in manifest.sealed_artifacts],
            "manifest_version": manifest.manifest_version,
            "output": output.as_posix(),
            "protocol_version": manifest.protocol_version,
            "registered_at_utc": manifest.registered_at_utc,
        }
    )
    return 0


def cmd_validate_sealed_manifest(args: argparse.Namespace) -> int:
    expected = args.expected_filename if args.expected_filename else None
    manifest = load_sealed_manifest(Path(args.manifest), expected_filenames=expected)
    result = {
        "artifact_count": len(manifest.sealed_artifacts),
        "filenames": [record.filename for record in manifest.sealed_artifacts],
        "manifest_version": manifest.manifest_version,
        "protocol_version": manifest.protocol_version,
        "registered_at_utc": manifest.registered_at_utc,
        "valid": True,
    }
    if args.json:
        _print_json(result)
    else:
        print(f"valid sealed manifest: {len(manifest.sealed_artifacts)} artifacts")
    return 0


def cmd_verify_sealed_manifest(args: argparse.Namespace) -> int:
    expected = args.expected_filename if args.expected_filename else None
    manifest = load_sealed_manifest(Path(args.manifest), expected_filenames=expected)
    findings = verify_sealed_manifest(
        manifest,
        repo_root=Path(args.repo_root),
        sealed_root=Path(args.sealed_root),
        additional_forbidden_roots=[Path(path) for path in args.forbidden_root],
    )
    result = {
        "finding_count": len(findings),
        "findings": [asdict(finding) for finding in findings],
        "valid": not findings,
    }
    if args.json:
        _print_json(result)
    else:
        print("sealed manifest verification passed" if not findings else f"sealed manifest verification found {len(findings)} issue(s)")
    return 0 if not findings else 1


def cmd_check_sealed_absence(args: argparse.Namespace) -> int:
    findings = find_sealed_presence(
        roots=[Path(path) for path in args.root],
        forbidden_filenames=args.filename,
        ignored_directory_names=args.ignore_directory,
    )
    result = {
        "clean": not findings,
        "finding_count": len(findings),
        "findings": [asdict(finding) for finding in findings],
    }
    if args.json:
        _print_json(result)
    else:
        print("sealed filename absence check passed" if not findings else f"sealed filename absence check found {len(findings)} issue(s)")
    return 0 if not findings else 1


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

    build_manifest = subparsers.add_parser("build-sealed-manifest")
    build_manifest.add_argument("--repo-root", required=True)
    build_manifest.add_argument("--sealed-root", required=True)
    build_manifest.add_argument("--protocol-version", required=True)
    build_manifest.add_argument("--registered-at", required=True)
    build_manifest.add_argument("--artifact-filename", action="append", required=True)
    build_manifest.add_argument("--output", required=True)
    build_manifest.add_argument("--forbidden-root", action="append", default=[])
    build_manifest.set_defaults(func=cmd_build_sealed_manifest)

    validate_manifest = subparsers.add_parser("validate-sealed-manifest")
    validate_manifest.add_argument("manifest")
    validate_manifest.add_argument("--expected-filename", action="append", default=[])
    validate_manifest.add_argument("--json", action="store_true")
    validate_manifest.set_defaults(func=cmd_validate_sealed_manifest)

    verify_manifest = subparsers.add_parser("verify-sealed-manifest")
    verify_manifest.add_argument("manifest")
    verify_manifest.add_argument("--repo-root", required=True)
    verify_manifest.add_argument("--sealed-root", required=True)
    verify_manifest.add_argument("--forbidden-root", action="append", default=[])
    verify_manifest.add_argument("--expected-filename", action="append", default=[])
    verify_manifest.add_argument("--json", action="store_true")
    verify_manifest.set_defaults(func=cmd_verify_sealed_manifest)

    check_absence = subparsers.add_parser("check-sealed-absence")
    check_absence.add_argument("--root", action="append", required=True)
    check_absence.add_argument("--filename", action="append", required=True)
    check_absence.add_argument("--ignore-directory", action="append", default=[".git", "__pycache__"])
    check_absence.add_argument("--json", action="store_true")
    check_absence.set_defaults(func=cmd_check_sealed_absence)

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
