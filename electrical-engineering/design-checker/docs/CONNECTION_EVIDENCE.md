# Connection evidence scope — lean calculation model

The connection layer is intentionally limited to information that can affect the tool's kW/A/cable calculations.

## Used by the calculation

- supply phase
- nominal connection current rating
- whether the result is a rated plug/socket connection or a fixed connection with no generic current ceiling

IEC 60309-1 and IEC 60309-2 publication metadata is kept in the backend only as provenance for the industrial 16 A, 32 A, 63 A and 125 A rating series.

## Deliberately outside the main tool scope

Clock position, colour, IP degree, mounting style, interlocking, exact product, and similar specification details are not inputs to the sizing workflow because they do not change the implemented kW/current/cable relationship. They can be added later only if a future calculation actually depends on them.

The general-purpose 16 A socket remains separate because its national/product evidence has not yet been mapped.
