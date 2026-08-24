# ElectricPy Function-Level Review

**Reviewed:** 2026-08-20  
**Repository:** [engineerjoe440/ElectricPy](https://github.com/engineerjoe440/ElectricPy)  
**License:** MIT  
**Decision:** Retain as a reference and comparison library for generic mathematics; **not a cable-sizing or standards-compliance engine**.

## Summary

ElectricPy is a broad Python library of electrical and electronics formulas, plots, and educational helpers. It is packaged, documented, MIT-licensed, and has automated tests for a number of functions.

It contains no cable ampacity tables or complete cable-selection workflow. Its fault module implements textbook symmetrical-component relationships, not the full data preparation and correction framework required for an IEC 60909 study.

The library may save time when building prototypes, but every adopted function should be independently verified and wrapped with explicit units, assumptions, input validation, and benchmark tests.

## Potentially useful function groups

| Group | Possible toolbox use | Decision |
|---|---|---|
| Phasor creation and conversion | Display and calculate AC quantities | Candidate |
| Power-set / power-triangle helpers | Convert between P, Q, S, and PF | Candidate |
| Delta-wye impedance conversion | General calculation helper | Candidate |
| Symmetrical-component conversion | Educational and fault-analysis support | Candidate with benchmarks |
| Textbook fault-current functions | Compare sequence-network hand calculations | Reference only |
| Transformer/current-transformer helpers | Future targeted calculations | Inspect individually |
| Plotting helpers | Calculation-report visuals | Optional |
| Thermal/electronics functions | Outside current workflow | Ignore |

## Strengths

- MIT license permits selective reuse of original code
- Published Python package and documentation
- NumPy/SciPy-based numerical implementation
- Tests cover many basic formula helpers
- Fault module uses zero-, positive-, and negative-sequence impedances rather than a single scalar approximation
- Functions are generally small enough to validate independently

## Limitations

### No cable-design workflow

The library does not provide:

- current-carrying-capacity tables
- installation methods and correction factors
- voltage-drop cable selection
- protective-device coordination
- CPC/PE sizing
- disconnection verification
- standards editions or national adaptations

### Fault functions are textbook building blocks

The fault module includes single-line-to-ground, line-to-line, double-line-to-ground, three-phase, bus-voltage, and short-circuit-MVA helpers. These take prepared Thevenin or sequence impedances as inputs.

They do not establish an IEC 60909 study by themselves. A complete implementation still needs network modelling, equipment correction factors, voltage factors, min/max cases, temperatures, motor/generator contribution, topology, and traceable equipment data.

### Input conventions need careful wrapping

Some functions convert real sequence “impedances” into purely imaginary values automatically. That convenience can hide whether a caller supplied resistance, reactance, or a full complex impedance. Unit and per-unit conventions also vary by function and must not be inferred silently.

### Verification is incomplete

The project README explicitly asks contributors to expand tests and says full function verification is lacking. Existing unit tests support software stability but are not equivalent to independent engineering validation.

## Reuse policy

Before using an ElectricPy function in this toolbox:

1. define the exact engineering question and supported units
2. inspect the implementation and documentation
3. reproduce the formula independently
4. create at least one published textbook or hand-calculated benchmark
5. test nominal, boundary, and invalid inputs
6. expose assumptions and intermediate values
7. copy only the required small function or depend on a pinned package version
8. preserve license notices when required
9. never add a compliance label unless the surrounding workflow has been validated

## Recommended whitelist for future inspection

- phasor and angle conversion
- P/Q/S/power-factor relationships
- delta-wye conversion
- sequence-to-phase and phase-to-sequence conversion
- simple textbook fault-current comparisons
- plotting utilities that do not affect engineering results

## Status

**Keep as a reference library. No installation is necessary now, and no function is approved for project calculations without separate validation.**
