from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from labos.checkers.case_file_checker import REQUIRED_CASE_FILES
from labos_check_case import run_case_check


SAFE_CASE_ID_RE = re.compile(r"^[a-z0-9_-]+$")


def _yaml_scalar(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def validate_case_id(case_id: str) -> None:
    if not SAFE_CASE_ID_RE.fullmatch(case_id):
        raise ValueError("case_id must contain only lowercase letters, numbers, hyphen, and underscore.")
    if Path(case_id).is_absolute() or "/" in case_id or "\\" in case_id or ".." in case_id:
        raise ValueError("case_id must be a safe folder name, not a path.")


def case_path_for(cases_root: Path, case_id: str) -> Path:
    validate_case_id(case_id)
    return cases_root / case_id


def _content_by_name(case_id: str, title: str, application: str, device_type: str, confidentiality_level: str, owner: str) -> dict[str, str]:
    title_yml = _yaml_scalar(title)
    application_yml = _yaml_scalar(application)
    device_type_yml = _yaml_scalar(device_type)
    owner_yml = _yaml_scalar(owner)
    confidentiality_yml = _yaml_scalar(confidentiality_level)

    draft_note = "Validated results are not yet available; no measured result has been generated."

    return {
        "00_problem_intake.yml": f"""case_id: {case_id}
title: {title_yml}
status: draft
owner: {owner_yml}
application: {application_yml}
device_type: {device_type_yml}
customer_question: TODO: summarize the thermal architecture question.
heat_source_geometry: TODO: define heat source size, location, duty cycle, and uncertainty.
power_or_power_density: TODO: provide bounded power or power density assumptions.
current_material_stack: TODO: describe the known package, substrate, die attach, and heat path.
cooling_boundary: TODO: define heat sink, coolant, ambient, boundary condition, and uncertainty.
target_temperature_or_margin: TODO: define target junction temperature or thermal margin.
known_data:
  - TODO: list known inputs and source artifacts.
missing_data:
  - TODO: list missing geometry, power, interface, boundary, and validation data.
assumptions:
  - TODO: document screening assumptions before comparing architectures.
validation_placeholders:
  - TODO: define what must be measured or bounded before stronger claims.
note: {draft_note}
confidentiality_level: {confidentiality_yml}
""",
        "01_thermal_design_passport.yml": f"""case_id: {case_id}
title: {title_yml}
status: draft
confidentiality_level: {confidentiality_yml}
likely_bottleneck: TODO: identify likely thermal bottleneck after intake review.
bottleneck_classification: TODO: conduction, interface, spreading, package, cooling boundary, or unknown.
architecture_candidates:
  - TODO: include diamond and non-diamond candidates neutrally when relevant.
constraints:
  - TODO: list cost, schedule, manufacturability, reliability, and integration constraints.
assumptions:
  - TODO: keep assumptions separate from measured facts.
confidence_level: low
recommended_near_term_route: TODO: do not select until assumptions are bounded.
recommended_long_term_route: TODO: do not select until validation evidence exists.
next_best_action: TODO: collect missing inputs before expensive simulation or supplier commitment.
note: {draft_note}
""",
        "02_decision_board.md": f"""# Decision Board

case_id: {case_id}
title: {title}
status: draft
confidentiality_level: {confidentiality_level}

## Decision Needed

TODO: state the thermal architecture decision to be made.

## Options Under Review

- TODO: conventional package improvement.
- TODO: interface or die attach improvement.
- TODO: heat spreader or submount route.
- TODO: advanced cooling route if justified.

## Assumptions

- TODO: list assumptions separately from known facts.

## Validation Placeholders

- TODO: define validation needed before selecting an architecture.

## Draft Safety Note

{draft_note}
""",
        "03_architecture_genomes.yml": f"""case_id: {case_id}
title: {title_yml}
status: draft
confidentiality_level: {confidentiality_yml}
architectures:
  - route_id: route-001
    route_name: TODO: candidate route name
    heat_source: TODO
    substrate: TODO
    bonding_interface: TODO
    heat_spreader: TODO
    package_path: TODO
    cooling_boundary: TODO
    manufacturing_route: TODO
    validation_method: TODO
    risk_profile: TODO
    maturity_level: TODO
    when_to_use: TODO
    when_not_to_use: TODO
note: {draft_note}
""",
        "04_design_space_scorecard.md": f"""# Design Space Scorecard

case_id: {case_id}
title: {title}
status: draft
confidentiality_level: {confidentiality_level}

## Scorecard

| Criterion | Draft score | Basis | Validation needed |
| --- | --- | --- | --- |
| thermal_potential | TODO | TODO | TODO |
| manufacturability | TODO | TODO | TODO |
| integration_risk | TODO | TODO | TODO |
| validation_difficulty | TODO | TODO | TODO |
| cost_pressure | TODO | TODO | TODO |
| supply_chain_readiness | TODO | TODO | TODO |
| time_to_demonstration | TODO | TODO | TODO |
| customer_fit | TODO | TODO | TODO |

## Draft Safety Note

{draft_note}
""",
        "05_red_flags.md": f"""# Red Flags

case_id: {case_id}
title: {title}
status: draft
confidentiality_level: {confidentiality_level}

## Thermal Red Flags

- TODO: heat source geometry incomplete.
- TODO: power or power density assumptions need bounds.
- TODO: cooling boundary needs definition.
- TODO: interface thermal resistance must be considered before material-only claims.

## Claim Safety Red Flags

- TODO: avoid customer-facing performance claims until validation required items are closed.

## Draft Safety Note

{draft_note}
""",
        "06_next_best_action.md": f"""# Next Best Action

case_id: {case_id}
title: {title}
status: draft
confidentiality_level: {confidentiality_level}

## Recommended Next Action

TODO: define the smallest action that reduces decision uncertainty.

## Required Inputs

- TODO: geometry.
- TODO: power or power density.
- TODO: material stack.
- TODO: interface thermal resistance assumptions.
- TODO: cooling boundary.

## Expected Output

TODO: state the decision this action will enable.

## Draft Safety Note

{draft_note}
""",
        "07_validation_plan.md": f"""# Validation Plan

case_id: {case_id}
title: {title}
status: draft
confidentiality_level: {confidentiality_level}

## Validation Questions

- TODO: what thermal parameter must be measured or bounded?
- TODO: what assumption could be falsified?

## Methods

- TODO: measurement, coupon, fixture, simulation calibration, or supplier data review.

## Success Criteria

- TODO: define before running the validation.

## Draft Safety Note

{draft_note}
""",
        "08_supplier_specification.md": f"""# Supplier Specification

case_id: {case_id}
title: {title}
status: draft
confidentiality_level: {confidentiality_level}

## Item Or Service

TODO: describe requested material, process, coupon, package, or data.

## Required Data

- TODO: dimensions, tolerances, interfaces, thermal data, reliability data, and inspection method.

## Acceptance Criteria

- TODO: define review criteria before requesting quotes or samples.

## Supplier Claim Caution

TODO: require basis and validation path for any performance statement.

## Draft Safety Note

{draft_note}
""",
        "09_customer_memo.md": f"""# Customer Memo

case_id: {case_id}
title: {title}
status: draft
confidentiality_level: {confidentiality_level}

## Summary

TODO: provide conservative, preliminary framing after engineering review.

## What Is Known

- TODO: list known customer-safe facts.

## What Is Unknown

- TODO: list unknowns and assumptions that control the decision.

## Recommended Next Step

TODO: recommend bounded intake, validation, or comparison work before conclusions.

## Claims Not Allowed

This is a draft case memo. No performance improvement is claimed until assumptions are validated.

## Draft Safety Note

Validated results are not yet available; no measured result has been generated.
""",
        "10_claim_ledger.yml": f"""case_id: {case_id}
title: {title_yml}
status: draft
confidentiality_level: {confidentiality_yml}
claims:
  - claim_id: CLM-001
    claim: This case folder has been opened for preliminary thermal architecture review.
    claim_type: process
    basis: Generated local no-API case scaffold.
    assumptions:
      - Technical inputs are incomplete and require engineering review.
      - No performance improvement is claimed by this scaffold.
    confidence: low
    validation_required: true
    status: draft
    public_release: not_allowed_until_review
    confidentiality_level: {confidentiality_yml}
    reviewer: TODO
note: {draft_note}
""",
        "11_engineering_memory_entry.md": f"""# Engineering Memory Entry

case_id: {case_id}
title: {title}
status: draft
confidentiality_level: {confidentiality_level}

## Lesson

TODO: add only reviewed and reusable lessons after the case is complete.

## Source Artifact

TODO: link to the reviewed case artifact.

## Reusable Pattern

TODO: describe reusable decision pattern after validation or review.

## Failed Assumption

TODO: record any assumption that did not survive review.

## Validated Assumption

TODO: record only assumptions supported by validation or accepted evidence.

## Future Use

TODO: explain where this memory may be reused.

## Draft Safety Note

{draft_note}
""",
    }


def create_case(
    cases_root: Path,
    case_id: str,
    title: str,
    application: str = "TODO",
    device_type: str = "TODO",
    confidentiality_level: str = "internal",
    owner: str = "TODO",
    force: bool = False,
) -> Path:
    case_path = case_path_for(cases_root, case_id)
    if case_path.exists() and not force:
        raise FileExistsError(f"Case already exists: {case_path}")
    if case_path.exists() and not case_path.is_dir():
        raise FileExistsError(f"Case path exists and is not a directory: {case_path}")

    case_path.mkdir(parents=True, exist_ok=True)
    content = _content_by_name(case_id, title, application, device_type, confidentiality_level, owner)
    for filename in REQUIRED_CASE_FILES:
        (case_path / filename).write_text(content[filename], encoding="utf-8")
    return case_path


def list_cases(cases_root: Path) -> list[tuple[str, str]]:
    if not cases_root.exists():
        return []
    rows: list[tuple[str, str]] = []
    for path in sorted(item for item in cases_root.iterdir() if item.is_dir()):
        missing = [filename for filename in REQUIRED_CASE_FILES if not (path / filename).is_file()]
        rows.append((path.name, "canonical" if not missing else f"incomplete ({len(missing)} missing)"))
    return rows


def _add_common_parser_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cases-root", type=Path, default=REPO_ROOT / "cases", help=argparse.SUPPRESS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create, list, and check Diamond Thermal Lab OS cases without API calls.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser("new", help="Create a canonical draft case folder.")
    _add_common_parser_options(new_parser)
    new_parser.add_argument("--case-id", required=True, help="Safe case folder id.")
    new_parser.add_argument("--title", required=True, help="Human-readable case title.")
    new_parser.add_argument("--application", default="TODO", help="Application context.")
    new_parser.add_argument("--device-type", default="TODO", help="Device or package type.")
    new_parser.add_argument("--confidentiality-level", default="internal", help="Confidentiality level.")
    new_parser.add_argument("--owner", default="TODO", help="Owner role or reviewer.")
    new_parser.add_argument("--force", action="store_true", help="Overwrite canonical files in an existing case folder.")

    check_parser = subparsers.add_parser("check", help="Run the local case checker.")
    check_parser.add_argument("case_path", type=Path, help="Path to a case folder.")
    check_parser.add_argument("--strict", action="store_true", help="Return exit code 1 for WARN.")

    list_parser = subparsers.add_parser("list", help="List case folders and canonical file status.")
    _add_common_parser_options(list_parser)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "new":
        try:
            case_path = create_case(
                cases_root=args.cases_root,
                case_id=args.case_id,
                title=args.title,
                application=args.application,
                device_type=args.device_type,
                confidentiality_level=args.confidentiality_level,
                owner=args.owner,
                force=args.force,
            )
        except (ValueError, FileExistsError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
        print(f"Created case: {case_path}")
        return 0

    if args.command == "check":
        report = run_case_check(args.case_path, strict=args.strict)
        print(report.render())
        return report.exit_code(strict=args.strict)

    if args.command == "list":
        rows = list_cases(args.cases_root)
        if not rows:
            print(f"No cases found under {args.cases_root}")
            return 0
        for case_id, status in rows:
            print(f"{case_id}\t{status}")
        return 0

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
