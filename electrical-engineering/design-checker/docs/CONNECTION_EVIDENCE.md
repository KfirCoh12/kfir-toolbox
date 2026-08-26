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
