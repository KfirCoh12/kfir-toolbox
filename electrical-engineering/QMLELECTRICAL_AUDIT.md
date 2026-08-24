# qmlElectrical Audit

**Reviewed:** 2026-08-20  
**Repository:** [haydenburrows30/qmlElectrical](https://github.com/haydenburrows30/qmlElectrical)  
**License:** MIT  
**Decision:** **Reject for cable sizing and engineering verification.** Retain only as a UI-learning reference.

## Summary

qmlElectrical is an ambitious desktop application containing many electrical calculators and visualisations. Its repository is substantial and its documentation openly says that learning Python, QML, and SQL is one of the project's goals.

The cable modules are not suitable for design decisions. They contain hard-coded ampacity arrays without a clear source in the inspected code, broad installation multipliers, assumed power factors, approximate impedances, and incomplete design checks. Multiple cable/voltage-drop implementations also use inconsistent approaches.

## Positive findings

- Large, readable desktop application with a clear QML/Python separation
- MIT license
- Cable ampacity and voltage-drop formulas are documented
- Copper/aluminium and PVC/XLPE choices exist
- Ambient and grouping factors are visible
- Windows build scripts are provided
- Useful examples of charts, forms, exports, and calculator UI design

## Critical findings

### 1. Ampacity data is not traceable

The main ampacity module embeds copper and aluminium ratings for PVC and XLPE cables but does not identify the exact standard, table, edition, cable construction, loaded-conductor count, or reference installation condition.

A value cannot be treated as authoritative merely because it resembles a familiar standards table.

### 2. Installation methods are generic multipliers

The model starts with a conduit rating table and applies simplified factors:

- conduit: 1.00
- tray: 1.00
- direct buried: 0.95
- free air: 1.15
- wall surface: 0.95

Actual installation methods require distinct rating tables and condition-specific correction factors. A generic multiplier does not establish equivalence between conduit, tray, burial, wall, and free-air arrangements.

### 3. The recommended-size calculation is not driven by a load

The ampacity calculator evaluates a user-selected cable and calculates its derated capacity. It then searches for a cable whose capacity meets that already calculated capacity. It does not accept the required load current as the sizing criterion in that workflow.

The “economic recommendation” similarly derives a size from the selected cable's derated ampacity and fixed economic current-density constants, not from a documented lifecycle-cost calculation.

### 4. Voltage drop fixes hidden assumptions

The direct voltage-drop module assumes:

- power factor 0.9
- room-temperature resistivity
- fixed reactance
- no explicit conductor operating-temperature correction
- no cable construction or arrangement effect

A second ampacity view assumes power factor 0.85 and different approximate resistance/reactance values. The application therefore contains inconsistent calculation paths for similar results.

### 5. One database-driven path applies correction factors incorrectly

The inspected voltage-drop service multiplies the mV/A/m voltage drop by temperature, installation, and grouping factors. Ampacity correction factors do not normally scale voltage drop in that manner.

It also infers insulation as XLPE when the conductor material is aluminium and PVC otherwise. Conductor material does not determine insulation type.

### 6. Standards compliance is incomplete

The inspected cable workflow does not establish:

- protective-device rating and characteristics
- overload coordination
- breaking capacity
- fault-loop impedance and disconnection
- phase and CPC adiabatic withstand using actual clearing time
- neutral and harmonic loading
- soil thermal resistivity and burial depth
- thermal insulation and detailed grouping arrangement
- local/national requirements
- manufacturer data

### 7. Testing is not engineering validation

The visible testing documentation focuses mainly on export functions. No clear automated benchmark suite for the ampacity and voltage-drop modules was established during this review.

### 8. Multiple overlapping calculators raise consistency risk

The repository includes more than one voltage-drop implementation and both direct hard-coded and database-driven cable logic. Their assumptions and formulas differ. Without a single verified calculation engine, identical inputs may not have a dependable interpretation.

## Suitability

| Use | Assessment |
|---|---|
| QML/Python interface examples | Useful |
| Charts and export examples | Useful |
| Educational formula exploration | Limited |
| Cable ampacity lookup | No |
| Cable-size selection | No |
| Voltage-drop verification | No |
| Standards compliance | No |
| Installation for engineering work | Not recommended |

## Recommendation

Do not install it for design work and do not copy its ampacity tables or cable-selection logic. If we build a desktop calculator later, the UI structure may provide ideas, but all engineering inputs, tables, formulas, and tests should be created from independently verified sources.

## Status

**Rejected for engineering use.** No installation performed.
