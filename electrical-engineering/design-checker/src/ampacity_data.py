"""Narrow V0 ampacity dataset.

This is intentionally NOT a reproduction of IEC 60364-5-52 Annex B. It stores
only a small supported slice needed to exercise the V0 engine.

Source basis:
- IEC 60364-5-52:2009 Ed. 3.0
- Table B.52.12: XLPE/EPR copper, Method E, multi-core, 3 loaded conductors
- Table B.52.13: XLPE/EPR aluminium, Method E, multi-core, 3 loaded conductors
- Table B.52.14: ambient-air correction for XLPE/EPR

Current-edition status: base edition checked; AMD1:2024 not yet reviewed.
"""

BASE_IZ_METHOD_E_3_LOADED = {
    "copper": {
        10.0: 75.0,
        25.0: 127.0,
        95.0: 298.0,
        120.0: 346.0,
        185.0: 456.0,
        240.0: 538.0,
    },
    "aluminium": {
        10.0: 58.0,
        25.0: 97.0,
        95.0: 227.0,
        120.0: 263.0,
        185.0: 347.0,
        240.0: 409.0,
    },
}

# Small practical subset of B.52.14 for XLPE/EPR in air.
AMBIENT_AIR_FACTOR_XLPE_EPR = {
    20.0: 1.08,
    25.0: 1.04,
    30.0: 1.00,
    35.0: 0.96,
    40.0: 0.91,
    45.0: 0.87,
    50.0: 0.82,
}

DATASET_METADATA = {
    "standard": "IEC 60364-5-52:2009",
    "edition": "3.0",
    "base_ampacity_tables": {
        "copper": "B.52.12",
        "aluminium": "B.52.13",
    },
    "ambient_air_table": "B.52.14",
    "applicability": "XLPE/EPR; Method E; multi-core cable; three loaded conductors; air; single circuit/run in this V0 slice",
    "current_edition_status": "BASE EDITION VERIFIED — AMD1:2024 NOT YET REVIEWED",
}
