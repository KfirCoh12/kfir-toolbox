# OpenMEP Suite Audit

**Reviewed:** 2026-08-20  
**Repository:** [kakarot-oncloud/openmep-suite](https://github.com/kakarot-oncloud/openmep-suite)  
**License:** MIT  
**Decision:** **Reject for direct engineering use in its current form.** Retain only as a source of interface and reporting ideas.

## Executive summary

OpenMEP Suite presents a polished, broad MEP platform and claims standards-cited cable sizing, voltage drop, short-circuit, generator, UPS, lighting, and other calculations. The repository is structured, readable, and includes automated tests.

The detailed electrical review found that the confidence implied by labels such as “IEC 60909,” “compliant,” and “audit-ready” is not supported by the calculation depth inspected. The cable workflow omits important design conditions and protection checks. The short-circuit routine is a simplified impedance estimate, not a sufficiently complete IEC 60909 implementation. Some standard and table references are also inconsistent with the code and tests.

This is more dangerous than an obviously simple calculator because the polished reports may make incomplete results appear authoritative.

## Scope inspected

- project README and standards-reference document
- `backend/engines/electrical/cable_sizing.py`
- European electrical adapter and embedded rating arrays
- `backend/tests/test_cable_sizing.py`
- `backend/engines/electrical/short_circuit.py`
- repository structure for regional adapters, standards data, tests, reports, and interfaces

This was a code review, not an independent reproduction of every proprietary standards table.

## Positive findings

- Clear separation between calculation engines, regional adapters, interface, and reports
- Readable Python data classes and intermediate outputs
- Ambient-temperature and grouping factors are exposed
- Cable selection checks ampacity and voltage drop
- Parallel-run input, CPC output, and optional adiabatic calculation exist
- Several regional adapters and test cases are present
- Automated tests include formula, factor, and behavioural checks
- MIT licensing is straightforward for original code
- The interface/report architecture could inspire a transparent internal tool

## Critical engineering findings

### 1. Breaker-to-cable coordination is not enforced

The engine chooses the next standard protective-device rating above the total design current. It does not verify the essential relationship between design current, protective-device rating, and the cable's derated current-carrying capacity.

The overall compliance result checks cable current capacity and voltage drop, plus the optional CPC result. It does **not** include a check that the selected protective device adequately protects the cable.

A report can therefore display an overall compliant result without establishing complete overload protection coordination.

### 2. The short-circuit engine is not a complete IEC 60909 implementation

The routine labelled as an IEC 60909 impedance method:

- treats transformer impedance as a single scalar
- adds source and transformer impedance without a complex R/X network model
- omits IEC voltage factors and transformer correction factors
- does not model positive-, negative-, and zero-sequence networks
- omits cable reactance in the feeder calculation
- does not handle conductor operating temperatures for maximum and minimum cases rigorously
- does not model motor contribution
- estimates terminal single-phase fault current as `0.87 ×` the three-phase value
- assumes a CPC of roughly 50% of phase cross-section for earth-fault estimation

These can be useful teaching approximations in a clearly labelled preliminary calculator. They should not be presented as a general IEC 60909 compliance calculation.

### 3. Fault protection uses fixed and inferred assumptions

The cable engine uses a user-entered fault level and a default fixed clearance time of 0.4 seconds. It does not derive clearing time from the actual protective-device curve at the calculated fault current.

The short-circuit module also uses a fixed 0.4-second duration for the minimum CPC calculation. Correct protection verification needs the actual device, fault current, disconnection requirement, earthing arrangement, and time-current behaviour.

### 4. Cable-table references are inconsistent

The European adapter describes XLPE/SWA/PVC thermosetting cable ratings while identifying the source as BS 7671 Table 4D5A. The tests also label that table as XLPE/Cu multicore. That reference appears inconsistent with BS 7671 table families and the described cable construction.

The standards document, adapter properties, test comments, and calculation comments also vary in how they describe voltage-drop clauses and regional application. Exact table identity must be verified before trusting any embedded value.

### 5. “Europe” is treated primarily as UK wiring practice

The Europe adapter declares BS 7671 as the main standard and accepts a country label without implementing distinct national wiring rules. IEC 60364 is not a complete plug-in replacement for each European country's national adoption.

The project has no Israel region, and neither UK nor GCC defaults should be silently treated as Israeli requirements.

### 6. Installation and derating inputs are incomplete

The inspected cable input covers a method code, ambient temperature, a grouped-circuit count, and touching/spaced selection. It does not establish a complete workflow for:

- soil thermal resistivity and ground temperature
- burial depth
- thermal insulation
- detailed tray or grouping geometry
- number of loaded conductors and cable construction
- harmonic currents and neutral loading
- additional correction factors required by the applicable method
- manufacturer-specific current ratings
- local environmental and project conditions

### 7. Voltage-drop calculation is simplified

The engine uses tabulated scalar mV/A/m values and load current. It does not visibly separate resistance and reactance or calculate the power-factor-dependent vector drop. Whether a scalar table value is acceptable depends on the exact table, conductor size, cable arrangement, and intended accuracy.

The implementation may be adequate for a constrained preliminary case, but the report does not communicate that limitation.

### 8. CPC selection and fault withstand are oversimplified

The adapter returns a CPC size from a general phase-to-CPC lookup. The optional adiabatic calculation uses broad material/insulation detection and a supplied fault current and time. It does not demonstrate the full earthing, mechanical-minimum, protective-device, and disconnection workflow.

### 9. The automated tests do not prove compliance

The tests are better than having no tests, but many compare code values with constants repeated in test comments or accept ranges of cable sizes. Several comments contain arithmetic, voltage, or reference inconsistencies. Passing tests show that the program behaves as coded; they do not independently validate the standards interpretation.

### 10. Embedded standards data needs legal and technical review

The repository states that full numerical standards tables are embedded. The MIT license covers the project's original code but does not automatically grant rights to third-party standards content. Technical provenance, transcription accuracy, and redistribution rights require separate confirmation.

## Risk examples

| Output shown by the tool | Missing assurance |
|---|---|
| “Overall compliant” | Complete protective-device/cable coordination |
| “IEC 60909” short-circuit result | Full IEC method, sequence networks, correction factors, and min/max cases |
| Automatically selected breaker | Verification that breaker rating and characteristics protect the selected cable |
| Earth conductor size | Full earthing arrangement, mechanical minimums, device curve, and disconnection check |
| Regional compliance statement | National adoption, local rules, exact standard edition, and project requirements |
| Clause-cited report | Verified table identity and correct application of the cited clause |

## Suitability

| Possible use | Assessment |
|---|---|
| Interface and report design inspiration | Good |
| Data-entry checklist inspiration | Useful but incomplete |
| Educational preliminary calculations | Only with strong limitation labels |
| Cable-size answer for a real design | No |
| Protective-device selection | No |
| IEC 60909 fault study | No |
| Direct code reuse | Only isolated non-engineering components after review |
| Embedded standards tables | Do not copy without technical and rights verification |

## Recommendation

Do not install, deploy, or use OpenMEP Suite for project calculations. Do not copy its standards tables or compliance language into this toolbox.

Useful ideas worth retaining:

- regional adapter architecture
- visible intermediate calculation values
- batch schedules
- report generation
- explicit warnings
- benchmark-case testing
- separation between calculation engine and interface

If we build a cable-checking tool, define a narrow supported scope first and validate each formula and data table independently. A good initial version should check a user-selected cable rather than automatically declare a cable and breaker combination compliant.

## Status

**Rejected for direct engineering use.** No installation performed.
