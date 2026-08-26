# Connection evidence layer — V0.6

## Industrial plug/socket classes

The automatic industrial connection catalogue uses the IEC 60309 Series I nominal classes 16 A, 32 A, 63 A and 125 A.

Evidence metadata is tied to:

- IEC 60309-1:2021, edition 5.0, with COR1:2023 — general requirements.
- IEC 60309-2:2021, edition 5.0, with COR1:2026 — dimensional compatibility requirements.

The official IEC publication pages establish the current editions and scope. Public preview material for IEC 60309-2:2021 identifies the 16/20 A, 32/30 A, 63/60 A and 125/100 A Series I/II classes; V0.6 uses the Series I values 16, 32, 63 and 125 A.

## What this does verify

- The recommendation belongs to the IEC 60309 industrial plug/socket family.
- The nominal current class is part of the IEC 60309 rating series used by the current edition.
- The tool records the exact standard editions used as evidence.

## What it does NOT verify yet

- exact pin/contact count or neutral arrangement
- clock position and voltage/frequency coding
- IP degree
- pilot contact or interlocking requirements
- a specific manufacturer's product compliance
- installation/project-specific requirements
- national requirements for general-purpose sockets

Therefore the tool may use an IEC 60309 nominal rating as a numerical connection constraint while still reporting the exact configuration/product verification as incomplete.

## Source links

- https://webstore.iec.ch/en/publication/59916
- https://webstore.iec.ch/en/publication/59919

## V0.7 — common 380/415 V three-phase configuration mapping

For the common IEC 60309 380/415 V AC, 50/60 Hz family, V0.7 can now distinguish two three-phase conductor arrangements when the neutral requirement is known:

- `3P+E` (4 poles) — no neutral required.
- `3P+N+E` (5 poles) — neutral required.

Both are represented as red, 6 h, 50/60 Hz configurations. This mapping is cross-checked against current Legrand IEC 60309 product data for 380/415 V accessories. The manufacturer's pages explicitly identify red 6 h 400 V / 50+60 Hz products in both 3P+E and 3P+N+E arrangements.

This still does **not** choose IP44 vs IP67, switched/interlocked construction, mounting style, terminal type, or an exact catalogue number. Those remain product/project choices.

Manufacturer evidence used for this configuration mapping:

- Legrand Hypra 380/415 V 16 A 3P+E product page: https://www.legrand.com/ecatalogue/en/catalog/products/panel-appliance-inlet-hypra-ip-44-380415-v-16-a-3pe-metal-052163
- Legrand P17 380/415 V 16 A 3P+N+E product page: https://www.legrand.com/ecatalogue/en/catalog/products/panel-mounting-socket-p17-ip6667-380415-v-16-3pne-555389
