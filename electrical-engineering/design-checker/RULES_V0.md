# Electrical Design Checker — V0 Rules

This file defines the first engineering rules to implement. Exact standards references are intentionally conservative until independently verified.

## Rule 1 — Design current versus protective-device rating

### Intent

The protective device must not be selected below the circuit design current for the supported normal-load case.

### Variables

- `Ib` — design current of the circuit
- `In` — rated current or current setting of the protective device, as applicable

### Initial check

`Ib <= In`

### Result logic

- `PASS` only when the applicable standards basis has been verified and `Ib <= In`.
- `FAIL` only when the applicable standards basis has been verified and `Ib > In`.
- `CALCULATED — NOT IEC VERIFIED` when the numerical comparison is available but the exact standards reference has not yet been verified.
- `NOT VERIFIED` when either `Ib` or the relevant protective-device rating/setting cannot be established reliably.

### Reference metadata

- Standard family: IEC 60364 (exact part/clause: `TBD — verification required`)
- Edition: `TBD — verification required`
- Applicability: LV circuit protection under supported normal operating conditions
- Notes: device-specific settings and special loads may require additional rules not included in V0.

## Rule 2 — Protective-device rating versus cable capacity

### Intent

The protective device must not permit a normal-load current rating above the supported current-carrying capacity of the selected cable after applicable installation/correction factors are accounted for.

### Variables

- `In` — rated current or current setting of the protective device
- `Iz` — supported current-carrying capacity of the cable after applicable factors

### Initial check

`In <= Iz`

### Result logic

- `PASS` only when the `Iz` value is traceable to an approved data source, required correction factors are accounted for, the applicable standards basis is verified, and `In <= Iz`.
- `FAIL` only when those same prerequisites are satisfied and `In > Iz`.
- `NOT VERIFIED` when ampacity data, installation method, correction factors, or applicability are incomplete.
- `CALCULATED — NOT IEC VERIFIED` when a numerical comparison is possible but the exact IEC basis has not yet been validated.

### Reference metadata

- Standard family: IEC 60364-5-52 / related applicable IEC conductor-selection provisions (exact clause/table: `TBD — verification required`)
- Edition: `TBD — verification required`
- Cable-data source: mandatory, exact source/table required
- Applicability: only the installation method, conductor type, insulation, ambient condition, grouping and other conditions covered by the selected data source

## Rule 3 — Combined V0 coordination check

### Initial relationship

`Ib <= In <= Iz`

This is evaluated as two explicit checks, not as an opaque single formula.

### Overall result

- `PASS` only if both Rule 1 and Rule 2 are PASS.
- `FAIL` if either referenced rule is FAIL.
- `NOT VERIFIED` if a required engineering input/data source is unavailable.
- `CALCULATED — NOT IEC VERIFIED` if the numerical relationship can be checked but the required IEC reference has not yet been validated.

## Traceability requirements

For every execution of these rules, the engine should retain:

- input values and units
- calculation method for `Ib`
- selected `In`
- source and derivation of `Iz`
- correction factors applied
- standard name
- edition
- clause/table reference
- applicability statement
- result and reason

No silent assumptions are permitted for installation method, correction factors, cable construction, or standards edition.

## Next rules to define

After these rules are validated, the next V0 rule set should cover voltage drop, including its calculation method, source data for resistance/reactance, permitted limits, and the distinction between IEC guidance and project/local requirements.
