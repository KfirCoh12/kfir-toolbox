# Electrical and Revit Candidate Radar

**Reviewed:** 2026-08-20  
**Purpose:** Rank open-source projects for deeper inspection before anything is installed, copied, or used for engineering decisions.

## Priority order

| Priority | Project | Main relevance | Initial decision |
|---:|---|---|---|
| 1 | [OpenMEP Suite](https://github.com/kakarot-oncloud/openmep-suite) | Cable sizing, voltage drop, short circuit, generator, UPS, lighting, schedules | **Audited; reject for direct use** |
| 2 | [qmlElectrical](https://github.com/haydenburrows30/qmlElectrical) | Desktop cable sizing and voltage-drop calculator | **Audited; reject for engineering use** |
| 3 | [pyRevitMEP](https://github.com/CyrilWaechter/pyRevitMEP) | Revit MEP utilities | **Inventoried; selected commands retained** |
| 4 | [ElectricPy](https://github.com/engineerjoe440/ElectricPy) | Reusable electrical formulas and plots | **Reviewed; retain narrow function candidates** |
| 5 | [pandapower](https://github.com/e2nIEE/pandapower) | Power flow, network analysis, and short-circuit foundations | **Keep as a backend candidate** |
| 6 | [VeraGrid](https://github.com/SanPen/VeraGrid) | Advanced grid planning and simulation | **Defer; too broad for current needs** |
| 7 | [QElectroTech](https://github.com/qelectrotech/qelectrotech-source-mirror) | Electrical schematics and documentation | **Defer; drawing tool, not calculation authority** |

## 1. OpenMEP Suite

### Why it is the strongest next candidate

It claims the closest match to recurring practical work:

- cable sizing under BS 7671 / IEC 60364 and other regional systems
- IEC 60364-5-52 voltage drop
- IEC 60909 short-circuit calculations
- generator and UPS sizing
- lighting calculations
- panel schedules and batch cable schedules
- cited clauses and tables in reports
- a web interface, API, Excel/PDF output, and MIT licensing
- an advertised automated test suite

### Why it still needs a strict audit

The scope and compliance claims are unusually broad. Before trusting it, we need to verify:

- whether embedded tables reproduce controlled standards content legally and accurately
- standard editions, national variations, and missing Israeli requirements
- installation methods and correction-factor logic
- neutral sizing, harmonics, protective conductors, fault withstand, and disconnection
- separation of cable ampacity, voltage drop, protection, and fault-duty decisions
- test quality rather than only the claimed test count
- whether reports expose every input and calculation step
- project maturity, contributors, releases, and maintenance history
- security and privacy implications if deployed as a web application

**Current status:** Full first-pass audit completed. Reject for direct engineering use; retain only interface and reporting ideas. See [OpenMEP Suite Audit](OPENMEP_AUDIT.md).

## 2. qmlElectrical

This is a large cross-platform desktop application with cable selection, voltage drop, visualisations, and other electrical calculations. Its README openly describes the project partly as a learning exercise, which is useful honesty but also a warning.

Questions for a targeted review:

- Which national standard and edition supply its cable tables?
- Are installation method, ambient temperature, grouping, soil conditions, and harmonics handled?
- Does cable selection cover fault withstand and protection coordination?
- Are data sources and calculation tests visible?
- Does the Windows build have a maintained release and safe installation route?

**Current status:** Targeted audit completed. Reject for engineering use; retain only UI-learning ideas. See [qmlElectrical Audit](QMLELECTRICAL_AUDIT.md).

## 3. pyRevitMEP

This is a GPL-3.0 pyRevit extension designed for MEP workflows and listed in the pyRevit extension ecosystem. It is potentially relevant to future Revit work, but only individual commands that solve real repeated problems should be considered.

Audit focus:

- create an inventory of commands, especially electrical and cable-tray tools
- check supported Revit and pyRevit versions
- identify scripts that modify many model elements
- inspect transactions, selection filters, units, error handling, and worksharing behaviour
- trial only on detached or disposable models
- confirm employer approval before installation on a managed computer

**Current status:** Inventory and first-pass risk review completed. No dedicated electrical toolset was found. Retain selected general QA/workflow commands, especially Room-versus-Space checking, but delay installation. See [pyRevitMEP review](../revit/PYREVITMEP_REVIEW.md).

## 4. ElectricPy

ElectricPy is an MIT-licensed Python formula library with documentation, package distribution, plotting helpers, and continuous-integration workflows. It may save time when building transparent calculators or teaching notebooks.

Its own README says testing is limited and asks for more verification. It is therefore more suitable as a source of reusable mathematical functions and comparisons than as a standards-compliance engine.

**Current status:** Function-level review completed. Retain only narrow generic-math candidates for independent validation; it is not a cable or standards engine. See [ElectricPy review](ELECTRICPY_REVIEW.md).

## 5. pandapower

pandapower is a mature BSD-licensed network-analysis library developed with academic and research-institute involvement. It supports power-system modelling and multiple solvers. GElectrical already uses it as a backend.

It is valuable for:

- load flow and voltage profiles
- short-circuit and network studies
- programmatic benchmark cases
- a future custom network-checking tool

It does not independently solve the standards-data problem for LV cable selection. Cable ratings and design constraints still require verified inputs.

**Current status:** Strong technical foundation for network studies; not the next user-facing tool to pursue.

## 6. VeraGrid

VeraGrid is a substantial GUI and library for advanced power-system planning: load flow, short circuit, optimal power flow, contingency, stochastic, RMS, EMT, investment analysis, and data exchange.

This is credible and interesting, but far beyond common feeder and cable questions. Evaluating it now would add complexity without solving the immediate workflow.

**Current status:** Keep on the long-term list for advanced grid studies; no action now.

## 7. QElectroTech

QElectroTech is useful for creating electrical schematics and managing symbol libraries. Its calculation-rule discussions correctly recognize that standards-based cable sizing requires many installation and protection inputs.

It is not presently the best route for automating engineering calculations, especially when Revit remains the primary design environment.

**Current status:** Skip for now.

## Projects to reject quickly

Most newly published single-purpose cable calculators should be rejected at screening unless they show all of the following:

- a clear license
- exact standards and editions
- traceable data sources
- full handling of installation and correction factors
- separate ampacity, voltage-drop, fault-withstand, and protection checks
- automated benchmark tests
- maintained releases or a reproducible installation
- formulas and intermediate results visible to the user

A polished interface, an “IEC compliant” label, or a cable-size output is not enough.

## Recommended sequence

1. OpenMEP Suite audit — completed; rejected for direct engineering use.
2. qmlElectrical audit — completed; rejected for engineering use.
3. pyRevitMEP inventory — completed; selected general commands retained for future trials.
4. Audit ElectricPy only at the function level to identify reusable, testable formulas.
5. Search for narrower Revit QA scripts after real repeated tasks are known.
6. Build or adapt only the smallest transparent workflow that survives benchmark testing.
