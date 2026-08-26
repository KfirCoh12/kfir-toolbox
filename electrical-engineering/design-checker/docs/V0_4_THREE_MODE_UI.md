# V0.4 three-mode workflow

The app now exposes the project around three user problems rather than one generic calculator screen:

1. **Design a supply** — load and installation information in; supported breaker/cable suggestion out.
2. **Check an existing supply** — selected load, breaker and cable in; engineering checks and verification status out.
3. **Find maximum load** — known existing constraints in; limiting factor and maximum current/kW/kVA out.

The UI is intentionally progressive. It asks for mode-relevant inputs and keeps detailed evidence, limitations and calculation traces behind expandable sections. The backend remains authoritative for calculations; the UI only collects inputs and renders results.

Current limitations remain explicit: automatic forward cable selection is limited to the supported IEC Method E dataset, and breaker sizing is not yet IEC 60364-4-43 verified.
