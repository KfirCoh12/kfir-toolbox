# GElectrical Assessment

**Reviewed:** 2026-08-20  
**Repository:** [manuvarkey/GElectrical](https://github.com/manuvarkey/GElectrical)  
**License:** GPL-3.0  
**Decision:** Trial candidate as a standalone network-analysis tool; **not approved as an authoritative cable-sizing source**.

## Executive summary

GElectrical is a substantial open-source electrical-network design application. It is much more mature and capable than a small cable calculator: it includes schematic capture, power flow, voltage drop, short-circuit analysis, protection coordination, cable damage curves, earthing-system options, rule checks, reports, samples, and manufacturer protection-device data.

It may be useful for learning, modelling a small network, and independently checking calculations. It should not yet be used to answer a simple question such as “is this cable size adequate?” without a separate, traceable calculation based on the applicable standard, installation method, environmental conditions, manufacturer data, and project requirements.

## What was inspected

This was a first-pass repository and code assessment, not a validation of numerical results.

- Project README, installation instructions, releases, license, activity, and repository structure
- Cable model in `gelectrical/elementmodel/line.py`
- Rule-check definitions in `gelectrical/model/rulescheck.py`
- Network-analysis architecture and declared dependencies
- Visible sample, documentation, and manufacturer-database structure

## Positive findings

- The project is active, non-archived, and has a meaningful development history.
- The repository contains substantial implementation code rather than a thin interface or placeholder.
- Network calculations use the established open-source `pandapower` backend.
- The cable model includes:
  - copper, aluminium, and steel conductor options
  - PVC and XLPE/EPR insulation options
  - working and final temperatures
  - current rating and a user-entered derating factor
  - parallel cable runs
  - positive- and zero-sequence electrical parameters
  - phase and protective-conductor short-circuit ratings
  - thermal cable damage curves
- Rule checks include cable loading, cable/protection coordination, automatic disconnection time, fault-level checks, and voltage-drop limits.
- The broader application supports three-phase and single-line-to-ground fault studies, several earthing arrangements, protection curves, reports, and sample projects.
- Windows binaries are published, so evaluation does not require building the source code.

## Main concerns

### 1. It is not a focused cable-sizing calculator

The application is primarily a schematic and network-analysis environment. It can evaluate a cable after its parameters and ratings are entered, but this is not the same as reliably selecting a cable from a complete, locally applicable ampacity table.

### 2. Standard traceability is mixed

The cable source contains comments referencing IEC standards, but also Indian standards such as IS 732 and IS 3043. Some Indian tables may reproduce or align with IEC material, but equivalence cannot be assumed. The exact edition, national adoption, and suitability for the intended jurisdiction must be checked before relying on a result.

### 3. Derating is an input, not a complete design workflow

The model exposes a general derating factor. A trustworthy sizing workflow still needs the designer to determine the combined correction factors for installation method, ambient or soil temperature, grouping, thermal resistivity, harmonics, buried depth, and other relevant conditions.

### 4. Manufacturer and regional coverage may not match the project

The included protection-device database and defaults may not contain the exact products, cable constructions, or local practices required. Manufacturer curves and ratings must be verified against current technical data.

### 5. The project warns users to cross-check results

Its own README describes active development, says bugs should be expected, and advises independent verification of calculations. That is appropriate, but it prevents treating the software as an authority.

### 6. Source installation is heavy on Windows

Building from source requires Python and a GTK-related toolchain with several native dependencies. The published Windows binary is the sensible route for a controlled evaluation.

### 7. Licensing affects reuse

GPL-3.0 permits inspection, use, and modification, but distributing a derivative that incorporates its code creates GPL obligations. We should not copy modules into this toolbox casually. Reimplementing a small, independently specified workflow with traceable sources may be cleaner.

### 8. Automated verification was not established

No obvious root-level automated test suite was confirmed during this first pass. That does not prove tests are absent, but numerical functions should be treated as unverified until repeatable benchmark cases are located or created.

## Practical value for this toolbox

| Possible use | Assessment |
|---|---|
| Learn how network studies fit together | Good |
| Draw and analyse a small LV network | Promising; trial first |
| Voltage-drop cross-check | Promising with verified inputs |
| Fault-current and protection study | Promising, but benchmark results |
| Automatically choose a compliant cable size | Not established |
| Source of ideas and data-field structure | Useful |
| Copy code directly into our tools | Avoid until GPL implications and need are clear |
| Final engineering authority | No |

## Recommended controlled trial

Do not integrate or fork the code yet. If we evaluate the application, use the official Windows binary on a non-restricted computer and run one deliberately simple benchmark:

1. Create a known source, feeder, cable, and load.
2. Enter an independently calculated current, cable impedance, rating, derating factor, and fault data.
3. Compare voltage drop, loading, fault current, disconnection, and damage-curve behaviour.
4. Record every assumed standard, table, edition, and manufacturer source.
5. Repeat with one adverse case designed to fail.
6. Only proceed if the results are reproducible and the inputs remain traceable.

Installation on a work-managed computer should wait for the employer's software and security approval.

## Better near-term direction

For frequent cable questions, a smaller transparent tool is likely more useful than adopting the full application. It should:

- ask for system, load, length, phase arrangement, conductor, insulation, installation method, ambient conditions, grouping, and protective device
- keep current-carrying capacity, voltage drop, fault withstand, and disconnection checks separate
- show formulas, assumptions, correction factors, and cited table references
- distinguish user-entered manufacturer data from built-in reference data
- never return a bare cable size without the calculation trail
- label the applicable standard and edition
- support benchmark tests with known expected results

GElectrical can inform that design and serve as one comparison engine, but it should not be the sole source of formulas or data.

## Status

**Keep on the candidate list. Do not adopt or install automatically.** The next meaningful step is a controlled binary trial against hand-checked benchmark cases, followed by a deeper audit of the exact cable tables and equations used.
