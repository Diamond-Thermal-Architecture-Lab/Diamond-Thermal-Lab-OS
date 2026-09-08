# Task Brief: M16A-I1 Quantities, Units, and Canonical Decimal Serialization

## Document Control

- Layer: L1 implementation foundation / L4 runtime contract
- Status: Ready for implementation gate review
- Objective: M16A-I1 — Quantities, Units, and Canonical Decimal Serialization
- Implementation starting commit: `95c8dcf6135f1ecd7e0e23be5f16b2aeeb5fcd6f`
- Starting tree: `af9b4e795ccc3985cf3c7f35d032d800cf550b55`
- Architecture: `docs/M16A_ENGINEERING_PROBLEM_COMPILER.md`
- Architecture disposition: `FINAL M16A ARCHITECTURE REVIEW: APPROVE`
- Confidentiality: Public-safe; synthetic quantities only
- Deliverable for this preparation task: this task brief only

The starting commit is the current-main implementation starting state after merged PR #40. It is not an M15B baseline and creates no new historical authority.

## 1. Objective

Implement the smallest deterministic quantitative foundation needed by later M16A work:

- strict finite base-10 decimal parsing and normalization;
- a versioned, closed unit vocabulary for approved M16A quantity kinds;
- exact conversion to canonical units without binary-float mediation;
- separation of physical numeric identity from authoring lexical identity; and
- canonical JSON bytes and lowercase SHA256 for later content identities.

I1 does not compile an Engineering Problem Representation (EPR), execute thermal equations, create an Engineering Evaluation Result (EER), or approve engineering data.

## 2. Repository Findings

| Area | Current repository evidence | I1 disposition |
| --- | --- | --- |
| SHA256 | `labos.benchmarks.integrity.sha256_bytes` and feature-local review/proposal helpers return lowercase SHA256 over exact bytes. | Preserve the exact-byte/lowercase convention; canonical structured hashing remains owned by `engineering.serialization`. |
| Source hashes | `labos.review_package.manifest.source_hashes` hashes sorted numbered case files by relative filename. | Reuse later in I2; I1 reads no case files and defines no source-case map. |
| JSON output | Evidence templates and review-package reports use sorted keys, UTF-8, and final newline, generally as indented display JSON. | Do not treat display renderers as a hash contract; I1 needs compact, versioned canonical bytes. |
| Benchmark integrity | Exact-byte and normalized-LF hashing include symlink and relative-path checks. | Reuse safety principles; never normalize a persisted artifact before claiming exact-byte identity. |
| Models/reports | Triage, evidence, and review packages use focused dataclasses, `to_dict()`, stable rule IDs, and separate renderers. | Follow the focused package pattern; I1 needs no report/finding layer. |
| Evidence | Status, source hash/reference, applicability, uncertainty, review, and confidentiality are separate. | Do not import evidence authority into quantity parsing. |
| Measurements | Schema 1.0 persists value and uncertainty as JSON numbers/null plus quantity and unit strings. | Leave schema, artifacts, and validator unchanged. |
| Prediction–Reality | Schema 1.0 persists JSON numbers/null. Comparison uses `Decimal(str(value))` after exact quantity and unit string matches; no conversion occurs. | Preserve this historical behavior; do not route old records through I1. |
| Case CLI | `scripts/labos_case.py` is the single CLI for case and evidence operations. | No I1 command; I2/I3 may extend it after their contracts exist. |
| Safe paths | Sidecar writers constrain outputs; exporters protect cases, root, patterns, memory, and `.git`; unsafe references are rejected. | I1 is filesystem-free and rejects `Path` or host objects during serialization. |

The repository has no strict M16A decimal lexer, quantity-kind contract, unit registry, offset-aware temperature conversion, canonical physical-value identity, or canonical structured serializer. Existing evidence `decimal_value()` is not an I1 parser: it accepts decoded JSON numbers, loses lexical form, and does not provide units or finite canonical-string rules. It remains unchanged for Prediction–Reality compatibility.

## 3. I1 Ownership Boundary

### In scope

- Runtime `QuantityKind`, unit definitions, conversion records, and quantified values.
- Strict parsing from M16A decimal strings to `decimal.Decimal`.
- Exact normalization to the canonical units below.
- Explicit numeric, lexical, and full-record comparison semantics.
- Registry version `m16a-unit-registry-1.0`.
- Serialization policy version `m16a-canonical-json-1.0`.
- Canonical JSON bytes and SHA256 over those bytes.
- Public-safe unit/decimal/serialization tests and full regression execution.

### Provenance decision

Defer provenance structures and validation to M16A-I2. I1 conversion metadata contains only original lexical value/unit, canonical value/unit, conversion rule ID, and unit-registry version. It states no source, evidence, uncertainty, confidence, review, or approval.

The approved quantity envelope places value beside provenance, but the authorities differ. A partial I1 provenance model would duplicate existing evidence contracts or prematurely define the EPR schema; I2 should own the complete envelope and reuse `EVD-*`/`MSR-*` conventions.

### Authority rules

- Parsing makes a quantity structurally usable, not technically valid.
- Conversion does not validate a source; a hash proves identity, not engineering truth.
- A material name never supplies a property; there are no property defaults or hidden lookups.
- Field-specific sign, range, evidence, and applicability rules belong to I2 or later validation.

## 4. Decimal Contract

### Accepted external input

M16A physical values enter I1 as Python `str`, not JSON numbers, `int`, `float`, `bool`, or locale-formatted text. Internal helpers may accept `Decimal` only where documented and must reject non-finite values.

```text
^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$
```

Accepted examples: `"0"`, `"-0"`, `"12"`, `"12.0"`, `"0.001"`, `"1e-3"`, `"1E+6"`.

Reject empty/whitespace text, leading `+`, leading zeros such as `01`, `.5`, `1.`, underscores, commas, locale separators, hexadecimal, `NaN`, `sNaN`, and signed/unsigned `Infinity`. Safety limits—not engineering limits—are 128 lexical characters, 64 coefficient digits, and adjusted exponent -128 through +128. Exceeding them fails; no rounding or clamping occurs.

### Execution and normalization

- Construct decimals and conversion constants only from exact strings; never from float.
- Use a private `decimal.Context`, not process-global state, sized for exact approved conversions.
- Trap `FloatOperation`, `InvalidOperation`, `Inexact`, `Rounded`, overflow, and underflow.
- Apply no significant-digit rounding in I1; conversion failure never falls back to approximation.
- Canonical text is locale-independent plain base-10 notation with no exponent.
- All signed zeros become `"0"`; insignificant fractional trailing zeros and a redundant decimal point are removed.
- Magnitudes below one keep a leading zero; exponent forms expand without losing significant digits.

Thus `"1.500"`, `"1.5"`, and `"15e-1"` share canonical numeric text `"1.5"`, while original lexical values remain distinct in conversion metadata.

### Equality and comparison

- Numeric identity is `(quantity_kind, canonical Decimal value)`; approved equivalent units compare after normalization.
- Different kinds never compare equal; ordering across kinds raises a typed mismatch error.
- Lexical identity compares original value/unit tokens exactly; audit identity compares the full serialized record.
- APIs name these operations explicitly rather than overload one ambiguous identity.

## 5. Quantity and Unit Contract

### Runtime representation

Use immutable feature-local types in `quantities.py`:

- `QuantityKind`: closed string enumeration.
- `UnitDefinition`: accepted token, owning kind, canonical token, exact scale/offset, stable rule ID.
- `ConversionRecord`: original and canonical values/units, rule ID, and registry version.
- `QuantifiedValue`: kind, canonical `Decimal`, canonical unit, and conversion record.

`QuantifiedValue.to_dict()` emits decimals as strings and contains no provenance, uncertainty, status, reviewer, material identity, path, or timestamp.

### Registry vocabulary

Tokens are exact and case-sensitive. Do not trim, case-fold, infer, pluralize, or compose unregistered units. Canonical tokens are shown in the final column.

| Quantity kind | Accepted tokens | Canonical conversion |
| --- | --- | --- |
| `power` | `W`, `mW` | `W`; identity or × `1e-3` |
| `heat_flux` | `W/m^2`, `W/mm^2` | `W/m^2`; identity or × `1e6` |
| `length` | `m`, `mm`, `um`, `µm` | `m`; identity, × `1e-3`, or × `1e-6` |
| `area` | `m^2`, `mm^2` | `m^2`; identity or × `1e-6` |
| `thermal_conductivity` | `W/(m*K)` | `W/(m*K)`; identity |
| `area_thermal_resistance` | `m^2*K/W`, `mm^2*K/W` | `m^2*K/W`; identity or × `1e-6` |
| `absolute_thermal_resistance` | `K/W` | `K/W`; identity |
| `area_thermal_conductance` | `W/(m^2*K)` | `W/(m^2*K)`; identity |
| `absolute_temperature` | `K`, `degC`, `°C` | `K`; identity or + `273.15` |
| `temperature_difference` | `K`, `degC`, `°C` | `K`; identity magnitude, no offset |
| `physical_dimensionless` | `1` | `1`; identity |

`µm` is MICRO SIGN U+00B5; ASCII `um` is preferred. Greek mu `μm` U+03BC is rejected in registry 1.0 as a confusable. `degC` is preferred; `°C` is an accepted UTF-8 alias. Display preservation resides in conversion metadata, while canonical temperature uses `K`.

`mW` supports exact low-power/subcomponent authoring without enabling general SI-prefix parsing; the explicit square-millimeter heat-flux and TBR tokens support the approved millimeter-scale fixture and remain closed aliases.

### Temperature and non-framework rules

- Absolute: `K = degC + 273.15`; therefore `50 degC = 323.15 K` and `0 degC = 273.15 K`.
- Difference: `delta K = delta degC`; therefore `25 degC` difference is `25 K`, not `298.15 K`.
- Unit token alone never chooses offset behavior; kind is mandatory.
- Absolute temperature and temperature difference are never comparable kinds.

The registry is a closed `(quantity_kind, exact token)` map, not a scientific-units framework. I1 does not parse arbitrary prefixes, simplify algebra, or derive area. A later caller may explicitly derive `2 mm × 2 mm = 4e-6 m^2`; I1 tests that invariant without adding an equation engine.

## 6. Canonical Serialization Contract

`canonical_json_bytes(value)` must:

- accept JSON-domain mappings with string keys, lists/tuples, strings, integers, booleans, null, finite `Decimal`, and explicit I1 `to_dict()` values;
- reject float, `Path`, datetime, set, bytes, arbitrary objects, non-string keys, and non-finite Decimal;
- convert Decimal to canonical decimal strings before encoding;
- encode UTF-8 without BOM using `ensure_ascii=False`;
- sort keys by deterministic Unicode code-point order, preserve arrays, and use compact `,`/`:` separators;
- use LF only and exactly one terminal LF.

`canonical_sha256(value)` hashes exactly those bytes and returns lowercase SHA256. It never hashes pretty JSON or platform text.

The serializer silently excludes nothing. I2/I3 artifact owners must build explicit allowlisted reproducibility payloads omitting timestamps, usernames, hostnames, absolute paths, display metadata, and self-hash fields. This satisfies the architecture rule without prematurely defining EPR/EER hashes. A synthetic test proves metadata excluded by that explicit projection cannot alter bytes/hash. Arbitrary strings receive no Unicode normalization; only approved unit aliases normalize through the registry.

## 7. Prediction–Reality Compatibility Decision

Historical version 1.0 remains authoritative for its records: values/bounds stay JSON numbers/null; quantity and unit strings must match exactly; comparison performs no unit conversion; and decoded values retain existing `Decimal(str(value))`, result, review, and learning behavior.

| Example | Lexical identity | M16A numeric identity | Existing v1.0 storage |
| --- | --- | --- | --- |
| M16A `"1.500"` | distinct string | canonical `"1.5"` | string is invalid for numeric field |
| M16A `"1.5"` | distinct string | canonical `"1.5"` | string is invalid for numeric field |
| Legacy JSON `1.5` | numeric token; spelling is not engineering identity | may project to Decimal `1.5` | valid JSON number |

Do not rewrite history, reinterpret historical numbers as M16A envelopes, or use raw JSON token spelling as physical identity.

Adapter implementation belongs to M16A-I3 because I3 owns EER outputs, result identity, and later Prediction–Reality binding:

```text
M16A QuantifiedValue
  -> explicit result-field selection
  -> typed projection with declared quantity label and exact target unit
  -> representability/round-trip check under v1.0 JSON-number semantics
  -> existing Prediction–Reality record/comparator
```

The adapter converts to the measurement's exact unit before projection, never changes the comparator, and refuses values that do not round-trip through the legacy JSON-number loader without numeric change. It never uses float for unit conversion or claims M16A lexical preservation.

I1 owns only fixtures proving `"1.500" == "1.5"` numerically while remaining lexically distinct. I3 owns adapter tests. Unchanged `tests/test_evidence_reality.py` is the I1 regression boundary.

## 8. Schema-First Decision

Choose option A: runtime primitives and inline test fixtures, with no persisted quantity schema.

“Schema-first” means approved EPR/EER artifact contracts precede their compilers, writers, and evaluators; it does not make every runtime type a standalone schema. I2 owns `labos/schemas/engineering_problem.schema.json`; I3 owns `labos/schemas/engineering_evaluation_result.schema.json`. I2 may define quantity `$defs` inside the EPR schema. A separate quantity schema is architecture-adjacent and requires review before implementation.

## 9. Minimum Future Implementation Files

```text
labos/engineering/__init__.py
labos/engineering/quantities.py
labos/engineering/serialization.py
tests/test_m16a_quantities.py
tests/test_m16a_serialization.py
```

- `__init__.py` exports the small public surface and version constants.
- `quantities.py` owns decimal policy, kinds, closed registry, conversions, and records.
- `serialization.py` owns canonical primitive conversion, bytes, and canonical SHA256.
- Tests use inline synthetic fixtures; no persisted artifact fixture is needed.

Do not add `physics/`, generic models, dependencies, provenance, schemas, reports, CLI commands, material data, solver adapters, or equations.

## 10. Acceptance Test Matrix

| ID | Topic/input | Required result |
| --- | --- | --- |
| DEC-01 | `0`, `12`, `12.0`, `0.001` | Exact Decimal; canonical `0`, `12`, `12`, `0.001` |
| DEC-02 | `1e-3`, `15E-1`, `1E+6` | Canonical `0.001`, `1.5`, `1000000` |
| DEC-03 | whitespace, `+1`, `01`, `.5`, `1.`, comma, underscore | Typed parse failure |
| DEC-04 | NaN/Infinity forms and non-finite Decimal | Rejected |
| DEC-05 | `-0`, `-0.000`, `-0e4` | Canonical `0`; original lexical retained |
| DEC-06 | `1.500`, `1.5` | Same numeric identity; different lexical identity |
| DEC-07 | float/int/bool external input | Rejected; no coercion |
| UNIT-01 | `1000 mW` | Exact `1 W`; rule/version recorded |
| UNIT-02 | `1 mm`; `100 um`; `100 µm` | `0.001 m`; micrometer forms `0.0001 m` |
| UNIT-03 | U+03BC `100 μm` | Unknown-unit failure in registry 1.0 |
| UNIT-04 | `4 mm^2`; `2.5 W/mm^2` | `0.000004 m^2`; `2500000 W/m^2` |
| UNIT-05 | `0.005 mm^2*K/W` | `0.000000005 m^2*K/W` |
| UNIT-06 | unknown/misspelled/wrong-case unit | Explicit failure; no guessing |
| UNIT-07 | `K/W` vs `m^2*K/W` | Kind mismatch; never interchangeable |
| UNIT-08 | conductance coefficient vs conductivity/resistance | Distinct kinds; never interchangeable |
| UNIT-09 | serialize/reconstruct canonical value/unit/kind | Same numeric identity; explicit audit-history behavior |
| TEMP-01 | absolute `50 degC`; `0 °C` | `323.15 K`; `273.15 K` |
| TEMP-02 | difference `25 K`; `25 degC`; `25 °C` | All `25 K`; no offset |
| TEMP-03 | absolute `25 K` vs delta `25 K` | Kind mismatch, not equality |
| INV-01 | `1 mm`; `100 um` | Exactly `1e-3 m`; `1e-4 m` |
| INV-02 | explicit test helper multiplies canonical `2 mm × 2 mm` | Exactly `4e-6 m^2`; no algebra API |
| SER-01 | mappings with different insertion order | Byte-identical compact UTF-8 |
| SER-02 | equivalent Decimal exponents/trailing zeros | Same canonical strings |
| SER-03 | repeated output under available locales | LF-only final newline, no BOM, identical bytes/hash |
| SER-04 | float, Path, datetime, set, non-string key | Explicit failure; no string fallback |
| SER-05 | payloads differ only in excluded synthetic host/user/path/time | Explicit allowlisted projections hash identically |
| SAFE-01 | missing kind/unit, ambiguous alias, material-like label | Failure; no property/default/guessing API |
| SAFE-02 | inspect and exercise scale/offset conversions | Decimal/string constants only; exact traps active |
| COMP-01 | existing Prediction–Reality tests unchanged | Pass without schema, artifact, helper, or comparator edits |
| COMP-02 | hash tracked evidence/measurement/Prediction–Reality artifacts and schemas | Byte-identical before/after |
| SCOPE-01 | inspect implementation diff | Only the five authorized I1 files |

## 11. Future I1 Exit Criteria

- Quantity primitives and the focused public API exist in the exact file set.
- External physical values follow the strict finite-string contract.
- Conversion and serialization never pass through float or silently round.
- The versioned closed registry implements every approved token and no implicit unit.
- Temperature offset/increment tests pass; physical, lexical, and audit identities stay distinct.
- Canonical bytes and SHA256 repeat identically; exclusions remain explicit caller projections.
- No property default, provenance authority, solver, model, compiler, or hidden lookup exists.
- New acceptance tests and all existing tests pass; test-count growth alone is insufficient.
- Existing schemas and historical artifacts are byte-untouched.
- Diff review confirms only the approved file set.

## 12. Explicitly Out of Scope

- EPR compiler or complete EPR schema; EER schema or Evaluation Plan execution.
- Reproducibility-identity contract beyond I1 serialization primitives.
- Prediction–Reality schema migration or adapter implementation.
- Model registry, 1D equations, TBR/boundary calculations, ranking, sweeps, or sensitivity.
- Material database/property lookup, CAD, FEA, CFD, UI, agents, or MPCVD.
- Provenance/approval implementation, Decision Board change, canonical approval, or memory update.
- ROADMAP, approved architecture, benchmarks, frozen protocols, or historical records.

## 13. Historical Boundary and Later Sequence

I1 must not modify or reinterpret the M15B execution baseline, frozen protocols, historical assessment, historical P3 = `PARTIAL`, scientific disposition `in_scope_generalization_supported`, governance disposition `governance_pass`, Phase 0.5C, or any historical benchmark artifact.

Later increments are M16A-I2: EPR Schema + Model-Independent Compiler Contract; M16A-I3: Evaluation Plan + EER + Reproducibility Identity, including the typed Prediction–Reality adapter; and M16A-I4: Strict 1D Thermal Kernel. This brief does not design them further.

## 14. Resolved Design Questions and Review Gate

| Question | Decision |
| --- | --- |
| Provenance types in I1? | No; I2 owns the complete envelope. |
| Shared quantity schema? | No; not an approved persisted artifact. |
| Change historical decimal helper? | No; preserve Prediction–Reality semantics. |
| Compatibility adapter in I1? | No; I3 owns result-to-record projection. |
| Arbitrary units/dependencies? | No; closed registry and standard library only. |
| Automatic metadata removal? | No; artifact owner supplies an allowlisted identity payload. |
| Normalize persisted files before hashing? | No; persisted hashes remain exact-byte identities. |
| CLI in I1? | No. |
| Hash-helper ownership blocking? | No; engineering serialization owns canonical structured hashing; current raw-byte helpers remain unchanged. |

No unresolved question blocks the implementation gate. Adding a unit, standalone schema, broader hash abstraction, or extra file requires explicit scope review.

Authorize only the five files in Section 9, require the matrix in Section 10, and require exact diff-scope and historical-byte audits. Any schema, adapter, CLI, provenance module, solver code, or extra unit must stop for review.
