# M14 Thermomechanical Triage Design

## Scope

M14 extends the existing read-only deterministic triage engine. It adds qualitative screening guardrails; it does not calculate stress, curvature, bow, cracking, delamination, or a route ranking.

## Available Inputs

The existing canonical intake and optional sidecars already provide reusable text-level signals: layer stack, membrane or substrate geometry, stated layer thicknesses, process or growth temperature, thermal boundary descriptions, missing-data lists, validation plans, pattern references, and evidence/measurement status. These inputs can identify that an elevated-temperature deposited-layer integration route needs thermomechanical evidence without changing the 12-file case contract.

## Important Missing Inputs

The current case format does not require temperature-dependent properties, stress-free reference temperature, residual-stress acceptance criteria, curvature acceptance criteria, adhesion/fracture evidence, fixture contact conductance, downstream flatness criteria, or scale-up evidence. M14 treats their absence as an evidence gap, never as a predicted failure.

## Data Model Decision

No Canonical Case schema change is needed. The triage result receives an additive `thermomechanical_screening` object and expanded optional rule-trace fields. Existing cases remain valid, and unrelated cases do not need to author new fields. Case authors may use existing public-safe intake, missing-data, validation-plan, and optional evidence-sidecar text to make the evidence basis clearer.

## Evidence Boundary

Each thermomechanical rule records a stable ID, title, triggering inputs, missing evidence, engineering rationale, enabled action, and evidence boundary. The rules distinguish:

- stated case text as known context;
- explicit `TODO`, `unknown`, `missing`, or `unmeasured` text as missing evidence;
- optional literature or measurement sidecars as source-documented context whose draft/unreviewed status remains a limitation; and
- rule output as an unvalidated screening inference.

The rules never convert a literature measurement, a pattern, or a validator result into a validated design conclusion.

## Reusable Relationships

The rule family activates only when a membrane or thin-layer context is combined with deposited-layer integration and elevated-temperature process context. It then looks for missing evidence about thermal expansion/property basis, process history, residual stress, bow/warpage acceptance, adhesion/delamination, fixture or reactor boundary, downstream compatibility, and geometry scale-up. These are general missing-evidence relationships, not paper-specific phrases or numerical limits.

## Compatibility

The existing incomplete GaN RF PA example lacks the combined membrane, deposited-layer, and elevated-temperature process context, so it remains free of detailed thermomechanical findings. Existing primary classifications and status values remain unchanged; M14 may add an additive secondary screening classification and prioritize a conservative evidence-gathering action when the context is present.

## Deferred Capability

Numerical stress/warpage calculations, material-property databases, coupled thermal-structural solvers, validated numerical thresholds, and automated learning remain outside M14. A second independent Gold Case is required before treating this rule family as generalized beyond screening.
