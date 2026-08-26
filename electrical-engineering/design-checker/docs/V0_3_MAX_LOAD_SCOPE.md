# V0.3 reverse / maximum-load solver

This mode answers the reverse question: **given an existing circuit, what is the maximum load supported by the constraints we can actually verify or explicitly accept?**

The engine takes the minimum current ceiling among supported inputs such as breaker rating, cable ampacity, connection/outlet rating, and voltage-drop limit, then converts that current to kVA and kW at the stated voltage/phase/power factor.

## Important limitations

- Breaker In is currently a numerical ceiling, not a full IEC 60364-4-43 protection verdict.
- Outlet/connection rating is user-supplied in V0.3; product-specific and standard-specific suitability is not yet independently sourced.
- Cable ampacity is only used when the existing ampacity router can verify the selected conditions.
- Voltage-drop limiting current is derived only when length, conductor geometry/material, permitted percentage and source are all supplied.
- Unsupported or missing constraints are never replaced with guessed limits.

`RESULT` means a maximum load was calculated from the supported constraints supplied. It does **not** mean every applicable installation/protection requirement has been standards-verified.
