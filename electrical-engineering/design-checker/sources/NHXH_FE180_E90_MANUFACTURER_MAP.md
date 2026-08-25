# NHXH FE180/E90 — manufacturer data map (V0)

## Purpose

This source map keeps manufacturer cable data separate from IEC 60364 table data. A manufacturer's published current capacity is not relabelled as an IEC ampacity value.

## V0 reference family

- Cable family: `(N)HXH / NHXH FE180/E90`, Cu, 0.6/1 kV
- Fire/cable standards commonly declared for the family include IEC 60331, IEC 60332, IEC 60754 and IEC 61034.
- E90 system circuit integrity is associated with DIN 4102-12 and depends on the tested installation/support system; selecting an E90-marked cable alone does not prove an E90 installation.
- Primary V0 ampacity basis: manufacturer-published current capacity in air at 30 °C, stated against DIN VDE 0298-4 where available.

## Supported narrow slice

Only exact constructions needed by the anonymized regression cases are represented initially:

| Construction | V0 reference current capacity in air at 30 °C |
|---|---:|
| 3x95+50 | 305 A |
| 3x120+70 | 355 A |
| 5x25 | 130 A |
| 5x10 | 73 A |

No interpolation is permitted. Other core arrangements or sizes remain unsupported until explicitly sourced.

## Provenance rules

1. `IEC 60364` data and manufacturer data remain separate source classes.
2. The checker must display the cable manufacturer/reference source when this dataset is used.
3. A manufacturer ampacity result can support a numerical `Iz` check only under its stated installation conditions.
4. Ambient/grouping/installation corrections must have their own applicable source; the manufacturer base rating must not silently inherit unrelated IEC table assumptions.
5. E90 is not inferred from cable selection alone; system installation/support evidence remains a separate requirement.

## V0 status

This map is suitable for building the manufacturer-data path and regression tests. It does not make the protection-device layer IEC 60364-4-43 verified, and therefore cannot by itself turn a feeder into an overall IEC-verified PASS.
