# pyRevitMEP Inventory and Risk Review

**Reviewed:** 2026-08-20  
**Repository:** [CyrilWaechter/pyRevitMEP](https://github.com/CyrilWaechter/pyRevitMEP)  
**License:** GPL-3.0  
**Decision:** Keep selected commands on the future Revit trial list; **do not install the full extension yet**.

## Summary

pyRevitMEP is a real pyRevit extension containing dozens of MEP and general Revit utilities. Despite the name, the inspected command inventory does not contain a focused electrical-design, circuit, cable-sizing, cable-tray-routing, or electrical-QA package.

A few general tools could be genuinely useful to an electrical designer. The safest and strongest candidate is the read-only Room-versus-Space check. Other commands create views or dimensions, copy settings, write parameters, move elements, delete elements, or change reference levels and therefore require controlled testing.

The correct approach is to identify an actual repeated task first, then inspect and trial only the relevant command on a detached model.

## Command inventory

The repository exposes roughly seventy push-button commands across Check, Create, Data, Export, Lab, Manage, Modify, Samples, and test panels.

Main groups include:

- Room/Space checks and transfer tools
- section, dimension, workset, system, and dependent-view creation
- level and elevation parameter tools
- material, parameter, view-type, view-range, and project-unit management
- connection, rotation, parallel-alignment, and flex-element tools
- family, type, parameter, and system deletion
- IFC and spreadsheet-related tools
- many experimental commands under a Lab panel

No dedicated electrical or cable-tray tool group was found in the current tree.

## Best candidates for the user's future workflow

| Command | Potential value | Mutation risk | Initial verdict |
|---|---|---:|---|
| SpaceVsRoom | Finds rooms without spaces, spaces without rooms, and name mismatches | Read-only | **Strong QA candidate** |
| CopyViewRange | Copies plan view ranges between views | Medium | Useful if repeated |
| QuickDimension | Dimensions selected parallel/linear elements | Medium | Trial for trays/conduits |
| CreateSection | Creates sections along selected line-based elements | Medium | Potentially useful |
| ElevationUnder | Writes distance to the nearest floor/roof above into a named parameter | High | Useful only with agreed parameter/workflow |
| ElementChangeLevel | Changes reference levels while attempting to preserve location | High | Do not use without rigorous test |
| MakeParallel | Rotates a target element parallel to a reference in plan | Medium | Situational |
| BatchWorksetCreation | Creates multiple worksets | High/project-wide | Only under BIM standards |
| CopyViewType | Copies view types between documents and assigns templates | High | Governance required |
| BatchObjectParameterSetter | Bulk parameter modification | High | Avoid until a specific need exists |
| Delete tools | Deletes families, types, parameters, or systems | Very high | Do not trial casually |

## Most promising command: SpaceVsRoom

The script:

- asks the user to select an open document containing rooms
- collects Rooms from that document and MEP Spaces from the active model
- compares them by Room/Space Number
- reports missing counterparts
- reports matching numbers with different names
- creates clickable element links in the pyRevit output
- does not open a Revit transaction or modify the model

This directly addresses a common linked-architecture coordination problem. Limitations:

- matching is by Number, so duplicates overwrite each other in the script's dictionaries
- it does not verify geometric containment or linked transformation
- it compares names as exact strings
- unplaced elements are reported but not deeply classified
- it assumes the room document is already open and selectable

**Verdict:** Worth recreating or adapting later as a small controlled QA tool, potentially with duplicate-number and geometric checks. It is safer than enabling an entire third-party extension.

## Other useful commands

### CopyViewRange

Copies a ViewPlan's view range to one or more target plan views. This could save time when standardizing working views. It is simple but modifies view settings and does not visibly screen out templates, dependent-view constraints, or incompatible targets.

### QuickDimension

Attempts to dimension selected elements based on line directions, family references, geometry edges, or origins. Cable trays and conduits may work because they are line-based, but reference stability and behaviour across plan/section views require testing.

### CreateSection

Creates section views around selected line-based elements using offsets and a chosen section type. It may be useful for service routes, but its default prefix and assumptions are generic and some fallback logic appears oriented toward walls/doors.

### ElevationUnder

Casts upward in a selected 3D view, including linked models, finds the nearest floor or roof, and writes a negative distance to a user-named parameter. This could support clearance/elevation workflows, but it:

- writes to every selected element inside a transaction
- assumes the parameter exists and is writable
- considers floors and roofs only
- depends on 3D-view visibility and reference-intersector behaviour
- needs agreed sign, units, and parameter naming

### ElementChangeLevel

Supports MEP curves, fittings, accessories, spaces, and other families. For Spaces, it creates a new Space, copies writable parameters, and deletes the old Space. That can affect identity, tags, references, systems, schedules, and worksharing.

**Verdict:** High-risk; do not use on a live model without a detailed version-specific test plan.

## Compatibility concerns

- The README still contains manual examples centered on Revit 2019.
- Some scripts include version-specific branches beginning with Revit 2020.
- The extension uses pyRevit, RevitPythonWrapper, WPF, and its own library code.
- Python engine and API compatibility must be checked against the exact pyRevit and Revit versions in use.
- Several commands are under a Lab panel and should be treated as experimental.
- Repository-wide automated Revit model tests were not established in this review.
- GPL-3.0 matters if code is copied and distributed; merely using the extension is different from incorporating its code.

## Installation recommendation

Do not install the full extension on either the personal or work computer yet.

When a real repeated task is identified:

1. verify the exact Revit and pyRevit versions
2. inspect only the relevant command and its dependencies
3. obtain employer approval for installation or custom scripting
4. use a detached or disposable model with representative links and worksharing conditions
5. record element counts and key parameters before the run
6. test undo, failure handling, duplicate data, groups, design options, phases, and linked models
7. compare the result manually
8. decide whether to use the original command or create a smaller reviewed version

## Recommended future shortlist

1. Room-versus-Space QA, with duplicate and geometry improvements
2. Copy view range, if view setup proves repetitive
3. Quick dimensions for selected cable trays/conduits
4. Section creation along selected routes
5. Elevation/clearance reporting without initially writing parameters

## Status

**Retain as a source of selected workflow ideas. Do not enable the full extension or deploy it to a work model.**
