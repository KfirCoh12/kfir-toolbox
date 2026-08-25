"""Narrow V0 ampacity dataset.

This is intentionally NOT a reproduction of IEC 60364-5-52 Annex B. It stores
only a small supported slice needed to exercise the V0 engine.

Source basis:
- IEC 60364-5-52:2009 Ed. 3.0
- B.52.12: XLPE/EPR copper, Method E, multi-core, 3 loaded conductors
- B.52.13: XLPE/EPR aluminium, Method E, multi-core, 3 loaded conductors
- B.52.14: ambient-air correction for XLPE/EPR
- B.52.17: selected grouping arrangements used with Method E

Current-edition status: base edition checked; AMD1:2024 not yet reviewed.
"""

BASE_IZ_METHOD_E_3_LOADED = {
    "copper": {10.0: 75.0, 25.0: 127.0, 95.0: 298.0, 120.0: 346.0, 185.0: 456.0, 240.0: 538.0},
    "aluminium": {10.0: 58.0, 25.0: 97.0, 95.0: 227.0, 120.0: 263.0, 185.0: 347.0, 240.0: 409.0},
}

AMBIENT_AIR_FACTOR_XLPE_EPR = {
    20.0: 1.08,
    25.0: 1.04,
    30.0: 1.00,
    35.0: 0.96,
    40.0: 0.91,
    45.0: 0.87,
    50.0: 0.82,
}

# Selected rows from B.52.17. Keys are the number of relevant circuits or
# multi-core cables. Values beyond this explicit subset are not interpolated.
GROUPING_FACTOR_B5217 = {
    "bunched": {1: 1.00, 2: 0.80, 3: 0.70, 4: 0.65, 5: 0.60, 6: 0.57, 7: 0.54, 8: 0.52, 9: 0.50},
    "perforated_tray_single_layer": {1: 1.00, 2: 0.88, 3: 0.82, 4: 0.77, 5: 0.75, 6: 0.73, 7: 0.73, 8: 0.72, 9: 0.72},
    "ladder_single_layer": {1: 1.00, 2: 0.87, 3: 0.82, 4: 0.80, 5: 0.80, 6: 0.79, 7: 0.79, 8: 0.78, 9: 0.78},
}

DATASET_METADATA = {
    "standard": "IEC 60364-5-52:2009",
    "edition": "3.0",
    "base_ampacity_tables": {"copper": "B.52.12", "aluminium": "B.52.13"},
    "ambient_air_table": "B.52.14",
    "grouping_table": "B.52.17",
    "parallel_rule": "523.7",
    "applicability": "XLPE/EPR; Method E; multi-core cable; three loaded conductors; air; explicitly supported grouping arrangements",
    "current_edition_status": "BASE EDITION VERIFIED — AMD1:2024 NOT YET REVIEWED",
}
