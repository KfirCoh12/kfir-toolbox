"""Narrow verified IEC 60364-5-52 ampacity dataset.

This is intentionally NOT a reproduction of IEC 60364-5-52 Annex B. It stores
only the Method E / multi-core / XLPE-EPR slices used by the design-checker.
Unsupported installation conditions remain outside the automatic model.

Source basis:
- IEC 60364-5-52:2009 Ed. 3.0
- B.52.12: XLPE/EPR copper, Method E, multi-core, 2 and selected 3 loaded conductors
- B.52.13: XLPE/EPR aluminium, Method E, multi-core, 2 and selected 3 loaded conductors
- B.52.14: ambient-air correction for XLPE/EPR
- B.52.17: selected grouping arrangements used with Method E

Current-edition status: base edition checked; AMD1:2024 not yet reviewed.
"""

# Full Method E multi-core two-loaded-conductor column used to introduce a
# source-backed single-phase path. Values are kept separate from the established
# three-loaded-conductor selector slice so this increment does not silently change
# existing three-phase cable suggestions.
BASE_IZ_METHOD_E_2_LOADED = {
    "copper": {
        1.5: 26.0,
        2.5: 36.0,
        4.0: 49.0,
        6.0: 63.0,
        10.0: 86.0,
        16.0: 115.0,
        25.0: 149.0,
        35.0: 185.0,
        50.0: 225.0,
        70.0: 289.0,
        95.0: 352.0,
        120.0: 410.0,
        150.0: 473.0,
        185.0: 542.0,
        240.0: 641.0,
        300.0: 741.0,
    },
    "aluminium": {
        2.5: 28.0,
        4.0: 38.0,
        6.0: 49.0,
        10.0: 67.0,
        16.0: 91.0,
        25.0: 108.0,
        35.0: 135.0,
        50.0: 164.0,
        70.0: 211.0,
        95.0: 257.0,
        120.0: 300.0,
        150.0: 346.0,
        185.0: 397.0,
        240.0: 470.0,
        300.0: 543.0,
    },
}

# Existing V0 three-loaded-conductor slice retained unchanged for backwards-stable
# three-phase selector behavior. Expanding this column is a separate engineering change.
BASE_IZ_METHOD_E_3_LOADED = {
    "copper": {10.0: 75.0, 25.0: 127.0, 95.0: 298.0, 120.0: 346.0, 185.0: 456.0, 240.0: 538.0},
    "aluminium": {10.0: 58.0, 25.0: 97.0, 95.0: 227.0, 120.0: 263.0, 185.0: 347.0, 240.0: 409.0},
}

BASE_IZ_METHOD_E_BY_LOADED_CONDUCTORS = {
    2: BASE_IZ_METHOD_E_2_LOADED,
    3: BASE_IZ_METHOD_E_3_LOADED,
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
    "base_ampacity_columns": {
        2: "Method E multi-core — two loaded conductors",
        3: "Method E multi-core — three loaded conductors",
    },
    "ambient_air_table": "B.52.14",
    "grouping_table": "B.52.17",
    "parallel_rule": "523.7",
    "applicability": "XLPE/EPR; Method E; multi-core cable; two or three loaded conductors; air; explicitly supported grouping arrangements",
    "current_edition_status": "BASE EDITION VERIFIED — AMD1:2024 NOT YET REVIEWED",
}
