# V0 reliability rules

The checker must fail loudly or return `NOT VERIFIED` rather than silently repairing ambiguous engineering input.

Current regression guards include:

- exact cable construction is the source of phase-conductor cross-section for manufacturer datasets;
- reduced neutral/PE conductor sizes must never be concatenated into the phase section (`3x95+50` means 95 mm² phase conductors, not 9550 mm²);
- grouped-circuit and parallel-run counts must be positive integers;
- unsupported manufacturer correction conditions remain `NOT VERIFIED`;
- manufacturer ampacity provenance remains separate from IEC 60364 table data;
- voltage-drop calculations are regression-tested against the 95-vs-9550 mm² failure mode.

These guards are intended to grow whenever a real defect or ambiguous input path is found.
