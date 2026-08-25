# Electrical Design Checker — UX Backlog

This file tracks workflow/usability decisions separately from visual styling. The goal is to reduce repetitive engineering input while keeping assumptions explicit and auditable.

## UX principles

1. **Do not hide engineering assumptions.** Defaults may be offered, but the result must show which values were assumed versus supplied.
2. **FAIL and NOT VERIFIED are different.** A failed calculation is different from a result that cannot be verified because a required input/source is missing.
3. **Guide the next action.** When a check fails or is blocked, say what the engineer can change or provide next.
4. **Progressive disclosure.** Common inputs stay visible; specialist inputs appear only when relevant.
5. **Project defaults should remove repetition.** Voltage, earthing/project criteria, ambient assumptions and common installation settings should eventually be reusable across many feeders.
6. **Source trace should be available, not dominant.** The main result should be readable quickly; clauses/tables/calculation traces belong in expandable detail.

## V0 usability issues observed

- Current screen exposes most technical fields at once in a long sidebar.
- The overall `NOT VERIFIED` message dominates even when the numerical design is otherwise coherent.
- Verification text is developer-oriented (`BASE-EDITION VERIFIED`, internal status strings).
- User manually enters values that may be derivable from a project/cable selection later.
- Cable family and installation-method vocabulary needs more engineer-friendly labels.
- Unsupported conditions need actionable explanations rather than generic warnings.

## Near-term UX changes (after current engineering coverage stabilizes)

### Result hierarchy

Target presentation:

- **Calculation status:** OK / problem found
- **Standards status:** Verified / verification incomplete
- Short cause, e.g. `Protection rule awaits current IEC 60364-4-43 basis`
- Four compact cards: `Ib`, breaker, `Iz`, voltage drop
- `Standards & calculation details` expander for exact references/traces

### Input workflow

Organize inputs into:

1. **Load** — load type/value, voltage, phase, PF, demand
2. **Protection** — selected breaker or later `Suggest breaker`
3. **Cable** — conductor/cable family, size, installation method
4. **Installation conditions** — ambient, grouping, parallel runs, harmonics
5. **Route** — length and voltage-drop criterion

Move uncommon fields into an **Advanced** section where possible.

### Actionable feedback

Instead of only `Iz < Ib`, eventually show:

- required current
- selected cable corrected capacity
- governing correction factor(s)
- nearest supported next size when defensible
- exact reason when no suggestion can be made

Example:

`Cable capacity insufficient: Ib 214 A > corrected Iz 185 A. Next supported size should be evaluated; current dataset cannot safely recommend one for this installation.`

### Smart defaults / remembered project settings

Future project-level defaults may include:

- nominal voltage and phase convention
- voltage-drop criteria by circuit type
- ambient temperature
- common installation methods
- approved cable families/manufacturers
- project-specific loading margin (kept separate from IEC rules)

Every reused default must remain visible in the result trace.

## Later workflow features

- multi-circuit table
- duplicate feeder / copy previous row
- Excel import/export
- saved project profiles
- automatic standard breaker-size suggestions
- cable-size suggestion loop
- manufacturer cable datasets
- batch validation report
- Revit import/integration

## Non-goals for early V0

- hiding missing standards behind reassuring UI
- auto-selecting a cable from incomplete installation data
- presenting project conventions as IEC requirements
- reproducing the private reference workbook interface
