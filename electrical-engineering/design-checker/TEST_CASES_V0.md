# Electrical Design Checker — V0 Anonymized Reference Cases

## Purpose and privacy

These cases are sanitized engineering examples derived from a private real-world project workbook. They exist to validate the V0 calculation engine against realistic feeder patterns.

The source workbook is **not** part of this repository and must remain private. Project, company, client, location, panel and system identifiers have been removed or replaced with generic case names. Only technical values needed for validation are retained.

These are **reference cases, not authoritative IEC examples**. Values shown under `Source-workbook result` record the private workbook's existing calculation approach and must not be treated as proof of IEC compliance.

## Important source-workbook conventions to investigate

Across the six selected cases, the displayed source current is consistently:

- `Current (A) = load (kW) × 1.6`

At 400 V, three-phase and PF = 0.9, the independent standard power equation produces a result within about 0.24% of that shortcut. This is a useful comparison, but the workbook rows do not explicitly document that 400 V / PF 0.9 is the source of the factor, so V0 must not silently assume it.

The next displayed current column is labelled `Inc=0.8`, but the six reference values do **not** all correspond to division by 0.8:

- Cases 01, 02, 03 and 06 correspond to `Current / 0.8`.
- Cases 04 and 05 correspond to `Current / 0.9`.

This is exactly why V0 treats any design/loading margin as an explicit project input rather than deriving a rule from a spreadsheet label.

V0 must **not** reproduce these factors blindly. The independent engine should calculate current from explicit electrical inputs (voltage, phase, power factor and other supported parameters), then compare its result with the source-workbook result.

---

## Case 01 — Medium fire-rated copper feeder

| Field | Sanitized value |
|---|---:|
| Load | 97 kW |
| Source-workbook current | 155.2 A |
| Source-workbook adjusted current | 194 A |
| Inferred source margin | 0.8 |
| Breaker | 200 A |
| Feeder cable | 3×95 + 50 mm² NHXH FE180-E90 |
| Conductor basis | Copper / fire-rated cable family |
| Approx. length | 100 m |
| Parallel cable runs | 1 |

## Case 02 — Large aluminium HVAC feeder

| Field | Sanitized value |
|---|---:|
| Load | 282 kW |
| Source-workbook current | 451.2 A |
| Source-workbook adjusted current | 564 A |
| Inferred source margin | 0.8 |
| Breaker | 630 A |
| Feeder cable | 3 × (3×185 + 95 mm² NA2XY) |
| Conductor basis | Aluminium |
| Approx. length | 100 m |
| Parallel cable runs | 3 |

## Case 03 — Long parallel aluminium feeder

| Field | Sanitized value |
|---|---:|
| Load | 390 kW |
| Source-workbook current | 624 A |
| Source-workbook adjusted current | 780 A |
| Inferred source margin | 0.8 |
| Breaker | 800 A |
| Feeder cable | 3 × (3×240 + 120 mm² NA2XY) |
| Conductor basis | Aluminium |
| Approx. length | 200 m |
| Parallel cable runs | 3 |

## Case 04 — Large fire-rated parallel feeder

| Field | Sanitized value |
|---|---:|
| Load | 748 kW |
| Source-workbook current | 1196.8 A |
| Source-workbook adjusted current | 1329.78 A |
| Inferred source margin | 0.9 |
| Breaker | 1600 A |
| Feeder cable | 6 × (3×120 + 70 mm² NHXH FE180-E90) |
| Conductor basis | Copper / fire-rated cable family |
| Approx. length | 60 m |
| Parallel cable runs | 6 |

## Case 05 — Medium fire-rated feeder with long run

| Field | Sanitized value |
|---|---:|
| Load | 22 kW |
| Source-workbook current | 35.2 A |
| Source-workbook adjusted current | 39.11 A |
| Inferred source margin | 0.9 |
| Breaker | 63 A |
| Feeder cable | 5×25 mm² NHXH FE180-E90 |
| Conductor basis | Copper / fire-rated cable family |
| Approx. length | 150 m |
| Parallel cable runs | 1 |

## Case 06 — Small simple feeder

| Field | Sanitized value |
|---|---:|
| Load | 11 kW |
| Source-workbook current | 17.6 A |
| Source-workbook adjusted current | 22 A |
| Inferred source margin | 0.8 |
| Breaker | 25 A |
| Feeder cable | 5×10 mm² NHXH FE180-E90 |
| Conductor basis | Copper / fire-rated cable family |
| Approx. length | 100 m |
| Parallel cable runs | 1 |

---

## Validation workflow for every case

Each case should eventually record three distinct layers:

1. **Source-workbook result** — retained only as a comparison point.
2. **Independent calculation result** — produced from explicit inputs and transparent formulas.
3. **IEC-backed engineering verdict** — produced only where the relevant rule, edition, clause/table, applicability and engineering data source have been verified.

A numerical match with the source workbook does **not** prove correctness. A difference does **not** automatically mean the source workbook is wrong; it triggers investigation of assumptions such as voltage, PF, efficiency, demand factors, installation method, cable data and project-specific criteria.

## Missing information deliberately not guessed

The source rows do not, by themselves, provide every parameter needed for a standards-backed calculation. V0 must obtain or explicitly request as applicable:

- nominal system voltage
- single-/three-phase basis
- power factor
- efficiency where relevant
- installation method
- ambient temperature
- grouping conditions
- cable manufacturer/technical ampacity data where required
- conductor operating temperature / R and X source for voltage drop
- applicable voltage-drop criterion
- applicable IEC edition and verified clause/table references

Until those inputs are available, affected checks must return `NOT VERIFIED` or `CALCULATED — NOT IEC VERIFIED`, in accordance with `SPEC_V0.md`.
