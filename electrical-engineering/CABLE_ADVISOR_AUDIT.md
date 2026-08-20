# Cable Advisor Audit

**Repository:** [masarray/cable-advisor](https://github.com/masarray/cable-advisor)  
**Review date:** 2026-08-20  
**Reviewed branch:** `main`  
**Decision:** **Reject for engineering use and do not copy/fork yet**

## Executive conclusion

Cable Advisor has a clean, mobile-friendly interface and a reasonably readable separation between calculation code and cable data. It is useful as a demonstration of how a personal cable-checking application could look.

It is **not currently a reliable foundation for cable selection**. Its README accurately limits it to preliminary estimation, but the interface still presents a single “Recommended size” without capturing several inputs required to support that recommendation. The repository also has no declared license, so its code should not be copied or modified in this toolbox unless the author adds a suitable license or grants permission.

## Repository maturity

- Created 2026-05-04 and last pushed 2026-05-05 at the time of review.
- No published releases.
- No declared repository license and no root `LICENSE` file.
- No stars or forks at the time of review.
- No meaningful engineering test suite.
- The source link in the application points to generic `github.com`, not the project repository.

This does not prove the project is unsafe, but it means there is little evidence of independent review, continued maintenance, or validated calculations.

## Positive findings

- Calculation logic is separated into [`cable-calc.ts`](https://github.com/masarray/cable-advisor/blob/main/src/lib/cable-calc.ts).
- Cable properties and correction factors are separated into [`cable-data.ts`](https://github.com/masarray/cable-advisor/blob/main/src/lib/cable-data.ts).
- Basic balanced single-phase and three-phase voltage-drop equations are recognizable and readable.
- Conductor resistance is temperature-adjusted from 20°C.
- The adiabatic short-circuit expression follows the familiar `kS/√t` form.
- Ambient-temperature and grouping factors are shown transparently in results.
- Motor-start voltage drop is provided as a separate preliminary check.
- The README clearly states that final sizing requires qualified verification.

## Critical engineering findings

### 1. Installation method is not implemented

The data file declares installation methods `A1`, `B1`, `C`, `E`, and `F`, but the input model and calculation engine never accept or use an installation method.

All recommendations therefore rely on a single ampacity column regardless of whether the cable is:

- in conduit,
- clipped direct,
- on tray,
- free air,
- buried,
- thermally insulated, or
- arranged as single-core or multicore.

The comments are also internally inconsistent: one comment says values cover “air or conduit,” while another identifies them as Method C “in conduit on wall.”

### 2. Ampacity data is approximate and not traceable enough

The source itself states that the values are approximate and intended only for estimation. It gives no exact table number, conductor arrangement, cable construction, or reproducible mapping for each ampacity column.

A professional check needs the precise source and conditions behind every rating.

### 3. Some aluminium ratings are invented by multipliers

For missing aluminium data, the calculator estimates values using multipliers:

- aluminium from copper XLPE: `0.78 ×`
- aluminium PVC adjustment: another `0.82 ×`

That may produce plausible-looking numbers, but it is not an acceptable replacement for a verified rating table.

### 4. Breaker coordination is missing

The calculator checks only load current against derated ampacity: `Ib ≤ Iz`.

It has no protective-device rated current input and therefore cannot check the normal relationship:

`Ib ≤ In ≤ Iz`

It also does not evaluate overload protection characteristics, disconnection requirements, or device energy let-through.

### 5. Parallel cables are unsupported

There is no input for parallel runs. This is a major limitation for the larger feeders and board supplies that commonly require multiple cables per phase.

### 6. Cable construction and loaded conductors are oversimplified

The user selects only:

- copper or aluminium,
- PVC or XLPE,
- one or three phase.

The tool does not adequately distinguish:

- single-core versus multicore,
- number of loaded conductors,
- conductor arrangement and spacing,
- neutral loading and harmonics,
- armour,
- tray versus conduit versus buried installation,
- soil thermal resistivity and depth,
- manufacturer-specific construction.

### 7. Voltage-drop temperature is fixed

Resistance is always evaluated at 70°C, including XLPE selections labelled for 90°C. Actual design temperature assumptions should be explicit and consistent with the chosen calculation basis.

Reactance is represented by one typical value per conductor size and does not respond to cable construction or single-core arrangement.

### 8. Short-circuit check is only an adiabatic comparison

The user manually enters prospective short-circuit current and clearing time. The tool does not calculate fault current at the cable end or determine clearing time from the protective device.

The `k` factors are fixed solely by conductor and insulation, without documenting the assumed initial/final temperatures or other applicability constraints.

### 9. Input validation is insufficient

The form accepts values without robust engineering bounds. Potential examples include:

- power factor outside 0–1,
- negative length or current,
- zero or negative clearing time,
- non-integer grouped circuits,
- unrealistic voltage and temperature.

Invalid values could yield misleading results or mathematical errors.

### 10. There are no calculation tests

The only test is:

```ts
expect(true).toBe(true);
```

There are no tests for:

- ampacity selection,
- correction factors,
- voltage drop,
- short-circuit withstand,
- boundary values,
- invalid inputs,
- known IEC/CIGRE examples.

## Software and dependency observations

- React/TypeScript/Vite architecture is understandable and suitable for a small browser-based calculator.
- The project includes a large general-purpose UI dependency set relative to its limited functionality.
- Both `bun.lockb` and `package-lock.json` are present, which makes the intended package-management workflow less clear.
- No evidence was found that user calculation data is transmitted externally; the reviewed calculation is client-side.
- A full dependency vulnerability scan was not performed because no code was imported or installed.

## Reuse decision

### Do not

- Do not use its recommended cable size for design decisions.
- Do not copy or fork the code while no license is declared.
- Do not import its ampacity table or aluminium multipliers.
- Do not label it “IEC compliant” based only on the current implementation.

### Potentially reuse later

If licensing is resolved, the following design ideas may be worth studying:

- mobile-friendly input/results flow,
- separation of formulas from data,
- transparent display of correction factors,
- per-check PASS/CHECK/FAIL presentation,
- comparison table across standard sizes.

These ideas can also be implemented independently without copying source code.

## Recommended next direction

Do not adopt Cable Advisor. Use it only as a UI concept reference.

For a dependable personal cable-checking tool, the next candidate should provide at least one of:

1. traceable, testable IEC calculation logic with exact assumptions;
2. verified example cases suitable for automated tests;
3. a clear open-source license;
4. active engineering-focused maintenance.

The strongest next research candidate is **GElectrical** for its broader IEC-oriented network calculations. The CIGRE TB 880 notebooks may serve as a source of verification cases for thermal-rating logic.

## Files reviewed

- [README](https://github.com/masarray/cable-advisor/blob/main/README.md)
- [Calculation engine](https://github.com/masarray/cable-advisor/blob/main/src/lib/cable-calc.ts)
- [Cable data](https://github.com/masarray/cable-advisor/blob/main/src/lib/cable-data.ts)
- [Input form](https://github.com/masarray/cable-advisor/blob/main/src/components/cable/InputForm.tsx)
- [Results panel](https://github.com/masarray/cable-advisor/blob/main/src/components/cable/ResultsPanel.tsx)
- [Existing test](https://github.com/masarray/cable-advisor/blob/main/src/test/example.test.ts)
- [Package manifest](https://github.com/masarray/cable-advisor/blob/main/package.json)
