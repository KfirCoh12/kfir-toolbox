# Reliability rules — V0

The checker is intentionally conservative. A numerical result is not enough to claim verification.

## Guardrails

- Cable geometry has one authoritative representation in the manufacturer dataset; UI code must consume that representation rather than re-parsing cable names.
- Manufacturer ampacity and generic IEC ampacity remain separate evidence routes.
- Unsupported grouping, parallel-run, installation, or ambient corrections must return **NOT VERIFIED** instead of borrowing an unrelated factor.
- A source/data route must retain provenance in the result metadata.
- Voltage-drop geometry must use the phase conductor area, not concatenated cable-name digits or protective/neutral conductor sizes.
- Invalid counts such as zero grouped circuits or zero parallel runs are rejected.
- Missing standards coverage must remain visible in the combined feeder result and cannot silently become PASS.

## Automated checks

The repository runs the complete checker test suite automatically on GitHub for Python 3.12 and 3.13 whenever checker code changes. CI also compiles the Python sources before running tests, catching syntax/import failures before a local user pulls the change.

Cross-module regression tests additionally verify that manufacturer cable geometry reaches the voltage-drop calculation correctly and that manufacturer provenance cannot be relabelled as generic IEC data.
