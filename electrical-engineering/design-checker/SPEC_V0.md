# Electrical Design Checker — V0 Specification

## Purpose

V0 is a narrow, traceable checker for a single LV circuit or feeder. It verifies a user-supplied design; it does not automatically design a complete installation.

The core principle is simple: **the tool may return `NOT VERIFIED`, but it must never invent an engineering answer.**

## V0 scope

V0 will support these checks:

1. Design current (`Ib`)
2. Protective-device rating (`In`)
3. Cable current-carrying capacity (`Iz`)
4. Basic cable/protective-device coordination
5. Voltage drop
6. Overall PASS / FAIL / WARNING / NOT VERIFIED result

V0 will initially handle one circuit or feeder at a time. UI, Revit integration, batch schedules, Excel import/export, automatic cable selection, and automatic breaker selection are outside V0.

## Required inputs

- Circuit or feeder name
- Supply type: single-phase or three-phase
- Nominal voltage
- Load input type: kW, kVA, or A
- Load value
- Power factor where applicable
- Demand/diversity factor where applicable
- Breaker rating
- Cable conductor material
- Cable cross-sectional area
- Number of parallel conductors/cables where supported
- Cable length
- Installation method or explicit `UNSPECIFIED`
- Ambient/grouping/other correction-factor inputs where required by the selected rule/data source
- Voltage-drop limit or applicable project/standard criterion

Unsupported or missing engineering data must not be silently defaulted.

## Calculation layer

### Design current

For three-phase active power:

`Ib = P / (sqrt(3) × V × PF)`

For single-phase active power:

`Ib = P / (V × PF)`

Where the user supplies current directly, that current is treated as the design-current input unless another explicit transformation is configured.

Demand/diversity must be applied explicitly and shown in the calculation trail; it must not be hidden inside an unexplained formula.

### Breaker and cable coordination

The initial relationship to evaluate is:

`Ib <= In <= Iz`

The checker must not report this relationship as standards-verified unless the applicable rule reference and the basis for `Iz` are both traceable.

### Voltage drop

For three-phase circuits, the detailed method may use:

`ΔV = sqrt(3) × I × L × (R cosφ + X sinφ)`

For single-phase circuits, the corresponding two-conductor expression will be used.

If a simplified method is used, the output must explicitly identify it as simplified and cite the source or project rule that permits it.

## Standards and references

Standards compliance is a first-class part of the checker.

Every rule-based engineering verdict must carry, where applicable:

- `rule_source`
- `standard`
- `edition`
- `clause_or_table_reference`
- `applicability`
- `notes`

IEC references are required whenever a PASS/FAIL/WARNING result depends on an IEC rule, limit, installation condition, correction factor, or selection criterion.

**Hard rule:** no standards-based PASS/FAIL result may be produced without a traceable source reference.

If the mathematics can be evaluated but the standards basis has not been verified, the result must be reported as:

`CALCULATED — NOT IEC VERIFIED`

Exact IEC clause/table identifiers must be independently verified before being encoded as authoritative references. Until then, they remain `TBD — verification required`.

Copyrighted standards text or substantial copyrighted tables must not be copied into this public repository. Derived rules may be encoded where lawful and appropriate, with citation metadata pointing to the licensed source.

## Result states

- `PASS` — the supported calculation and applicable referenced rule are satisfied.
- `FAIL` — a supported referenced rule is violated.
- `WARNING` — the calculation can be performed, but a condition requires attention.
- `NOT VERIFIED` — authoritative data or rule support is incomplete.
- `CALCULATED — NOT IEC VERIFIED` — mathematical result exists, but the required IEC basis has not yet been validated.

## Transparency requirement

Every calculated result must be reproducible from its inputs. The engine must be able to expose:

- formula used
- substituted values
- units
- intermediate values where relevant
- final value
- engineering data source
- rule/standard source used for the verdict

A future UI may hide this detail by default, but the engine must retain it.

## Engineering-data separation

Engineering data must be separate from calculation code. Planned structure:

```text
data/
  cable_ampacity/
  cable_resistance/
  cable_reactance/
  correction_factors/
  breaker_ratings/
```

Each dataset should record source, edition/version, table/reference, units, applicability, and notes.

## Validation before release

V0 is not considered usable until it has a set of manually verified reference cases, including at minimum:

1. Normal three-phase feeder — expected PASS
2. Breaker below design current — expected FAIL
3. Cable capacity below protective-device rating — expected FAIL
4. Excessive voltage drop — expected FAIL
5. Missing authoritative cable data — expected NOT VERIFIED
6. One supported parallel-cable case — expected known result
7. A mathematically calculable case with unverified standards basis — expected CALCULATED — NOT IEC VERIFIED

## Explicit V0 exclusions

V0 does not include:

- short-circuit calculations
- breaker trip-curve coordination
- selectivity/discrimination
- earth-fault protection
- loop impedance
- transformer sizing
- generator sizing
- UPS sizing
- harmonics
- motor starting
- capacitor-bank sizing
- busbar sizing
- automatic cable selection
- automatic breaker selection
- Revit integration
- Excel import/export
- production GUI

These may be added only after the V0 calculation and rules architecture is validated.
