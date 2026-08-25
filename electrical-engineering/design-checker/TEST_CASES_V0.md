# Electrical Design Checker — V0 Anonymized Reference Cases

## Purpose and privacy

These cases are sanitized engineering examples derived from a private real-world project workbook. They exist to validate the V0 calculation engine against realistic feeder patterns.

The source workbook is **not** part of this repository and must remain private. Project, company, client, location, panel and system identifiers have been removed or replaced with generic case names. Only technical values needed for validation are retained.

These are **reference cases, not authoritative IEC examples**. Values shown under `Source-workbook result` record the private workbook's existing calculation approach and must not be treated as proof of IEC compliance.

## Important source-workbook convention to investigate

For many rows in the source workbook:

- `Current (A) = load (kW) × 1.6`
- `Inc=0.8 = Current / 0.8`

V0 must **not** reproduce these factors blindly. The independent engine should calculate current from explicit electrical inputs (voltage, phase, power factor and other supported parameters), then compare its result with the source-workbook result.

The workbook does not expose all inputs required to reconstruct the electrical basis of the `×1.6` convention from these rows alone. Missing inputs must remain explicit rather than inferred.

---

## Case 01 — Medium fire-rated copper feeder

**Purpose:** medium-size emergency/fire-rated feeder with a single cable run.

| Field | Sanitized value |
|---|---:|
| Load | 97 kW |
| Source-workbook current | 155.2 A |
| Source-workbook `Inc=0.8` | 194 A |
| Breaker | 200 A |
| Feeder cable | 3×95 + 50 mm² NHXH FE180-E90 |
| Conductor basis | Copper / fire-rated cable family |
| Approx. length | 100 m |
| Parallel cable runs | 1 |

**V0 questions:** Can independent `Ib` be reconstructed once voltage/PF assumptions are explicitly supplied? Is `In >= Ib`? Is `In <= Iz` under a verified installation method and cable dataset? What is the voltage drop?

---

## Case 02 — Large aluminium HVAC feeder

**Purpose:** large routine HVAC load using multiple parallel aluminium feeder cables.

| Field | Sanitized value |
|---|---:|
| Load | 282 kW |
| Source-workbook current | 451.2 A |
| Source-workbook `Inc=0.8` | 564 A |
| Breaker | 630 A |
| Feeder cable | 3 × (3×185 + 95 mm² NA2XY) |
| Conductor basis | Aluminium |
| Approx. length | 100 m |
| Parallel cable runs | 3 |

**V0 questions:** How is `Iz` determined per run and for the parallel arrangement? Which grouping/installation correction factors apply? Does the selected breaker coordinate with the corrected aggregate capacity?

---

## Case 03 — Long parallel aluminium feeder

**Purpose:** test a long feeder where voltage drop should become significant to the validation process.

| Field | Sanitized value |
|---|---:|
| Load | 390 kW |
| Source-workbook current | 624 A |
| Source-workbook `Inc=0.8` | 780 A |
| Breaker | 800 A |
| Feeder cable | 3 × (3×240 + 120 mm² NA2XY) |
| Conductor basis | Aluminium |
| Approx. length | 200 m |
| Parallel cable runs | 3 |

**V0 questions:** Calculate voltage drop from traceable R/X data. Verify parallel-cable handling. Determine whether the breaker/cable relationship passes only after installation and correction-factor data are known.

---

## Case 04 — Large fire-rated parallel feeder

**Purpose:** high-current emergency/fire-rated circuit with multiple parallel copper cables.

| Field | Sanitized value |
|---|---:|
| Load | 748 kW |
| Source-workbook current | 1196.8 A |
| Source-workbook `Inc=0.8` | 1329.78 A |
| Breaker | 1600 A |
| Feeder cable | 6 × (3×120 + 70 mm² NHXH FE180-E90) |
| Conductor basis | Copper / fire-rated cable family |
| Approx. length | 60 m |
| Parallel cable runs | 6 |

**V0 questions:** Verify how current is shared between parallel conductors and whether equal-current assumptions are permitted under the supported rule set. Confirm `Iz` from an appropriate fire-rated cable source rather than substituting ordinary-cable ampacity data.

---

## Case 05 — Medium fire-rated feeder with long run

**Purpose:** relatively modest load but long cable length, useful for separating ampacity and voltage-drop checks.

| Field | Sanitized value |
|---|---:|
| Load | 22 kW |
| Source-workbook current | 35.2 A |
| Source-workbook `Inc=0.8` | 39.11 A |
| Breaker | 63 A |
| Feeder cable | 5×25 mm² NHXH FE180-E90 |
| Conductor basis | Copper / fire-rated cable family |
| Approx. length | 150 m |
| Parallel cable runs | 1 |

**V0 questions:** Does voltage drop become the governing constraint even where the breaker/current comparison appears comfortable? Which conductor arrangement and voltage assumptions are required before calculating it?

---

## Case 06 — Small simple feeder

**Purpose:** provide a relatively simple baseline before testing large and parallel arrangements.

| Field | Sanitized value |
|---|---:|
| Load | 11 kW |
| Source-workbook current | 17.6 A |
| Source-workbook `Inc=0.8` | 22 A |
| Breaker | 25 A |
| Feeder cable | 5×10 mm² NHXH FE180-E90 |
| Conductor basis | Copper / fire-rated cable family |
| Approx. length | 100 m |
| Parallel cable runs | 1 |

**V0 questions:** Use this as an early baseline for design-current calculation, breaker comparison and later ampacity/voltage-drop checks.

---

## Validation workflow for every case

Each case should eventually record three distinct layers:

1. **Source-workbook result** — retained only as a comparison point.
2. **Independent calculation result** — produced from explicit inputs and transparent formulas.
3. **IEC-backed engineering verdict** — produced only where the relevant rule, edition, clause/table, applicability and engineering data source have been verified.

A numerical match with the source workbook does **not** prove correctness. A difference does **not** automatically mean the source workbook is wrong; it triggers investigation of assumptions such as voltage, PF, efficiency, demand factors, installation method, cable data and project-specific criteria.

## Missing information deliberately not guessed

The source rows do not, by themselves, provide every parameter needed for a standards-backed calculation. In particular, V0 must obtain or explicitly request as applicable:

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
