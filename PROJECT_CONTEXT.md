# Kfir Toolbox — Project Context

This repository is a practical engineering toolbox. The current active product area is the electrical design checker, which is both a useful standalone calculator and the circuit-intelligence foundation for a future distribution-board planning tool.

## Working principles

- GitHub is the source of truth for code, tests, and engineering behavior.
- Calculation logic must remain separate from UI logic.
- Do not invent standards data, correction factors, product ratings, or compliance claims.
- Unsupported conditions must remain explicit as `NOT_VERIFIED` / partial scope rather than being silently approximated.
- Prefer backend-owned structured statuses, issue codes, and discrete catalogs over UI-owned engineering interpretation.
- UI should stay compact, dark-mode oriented, progressive, and low-text; technical explanation belongs in hover help or collapsed detail where possible.
- A conventional candidate is not the same thing as a standards-verified design. Wording must preserve that distinction.

## Current architecture

### Circuit calculation layer

The electrical checker currently supports two standalone workflows:

1. **Design a supply** — load → design current → conventional breaker candidate → supported cable candidate → connection suggestion, with optional voltage-drop checking.
2. **Existing supply capacity** — known breaker/cable/connection constraints → lowest supported current ceiling → maximum kW/kVA.

Important backend modules live under `electrical-engineering/design-checker/src/`.

- `current.py` — design-current calculations.
- `cable.py`, `ampacity_data.py`, `ampacity_router.py`, `manufacturer_ampacity.py` — supported ampacity routes and evidence-limited cable calculations.
- `voltage_drop.py` — voltage-drop calculations and guarded limit checking.
- `connection.py` — mapped connection options.
- `circuit_selector.py` — conservative forward circuit selection.
- `max_load.py` — reverse capacity calculation.
- `verification.py` — structured result scope/status/issues.
- `catalogs.py` — shared discrete engineering choices such as the declared breaker-rating series.
- `circuit_engine.py` — reusable named-circuit facade for higher-level tools.

### Board planning layer

`board_planner.py` is the first higher-level consumer of the circuit engine. It currently provides:

- multiple named circuits in one board request;
- board supply voltage contract (line-line and line-neutral);
- automatic circuit calculation through the shared circuit engine;
- schedule-row output;
- deterministic single-phase phase allocation;
- optional locked L1/L2/L3 preferences;
- three-phase loads applied equally to all phases;
- L1/L2/L3 planned current totals and absolute phase-current spread;
- a provisional incomer breaker candidate from the highest planned phase current and the shared breaker catalog.

The phase allocator is a planning heuristic: unlocked single-phase circuits are sorted largest-first and assigned to the currently least-loaded phase. It does **not** imply a standards-defined acceptable imbalance threshold.

The incomer is also only a planning candidate. Circuit demand factors are already included in circuit design current, but there is currently **no additional board-level diversity rule and no board incomer protection verification**.

## Current engineering scope / limitations

Automatic cable sizing remains deliberately narrow. Current verified automatic ampacity coverage is centered on the explicit Method E / in-air / XLPE-EPR / three-loaded-conductor dataset and supported grouping/ambient cases. Single-phase design current, breaker candidate, and connection rating can be calculated, but automatic single-phase cable sizing is not verified because a verified two-loaded-conductor dataset has not yet been added.

Parallel cable sizing is guarded by explicit acceptable-current-sharing confirmation and grouping inputs that include the parallel runs. Unequal sharing and dissimilar parallel runs are outside the model.

The breaker series is a declared conventional candidate catalog. Full IEC 60364-4-43 protection verification is not yet implemented.

Board-level features **not yet implemented** include:

- board-level diversity / maximum-demand methodology beyond each circuit's own demand factor;
- final incomer protection verification;
- busbar / board rating selection;
- pole and way allocation;
- spare-way policy;
- neutral loading / harmonics at board level;
- selectivity / discrimination;
- short-circuit level and breaking-capacity checks;
- protective-conductor sizing;
- fault-loop / disconnection checks;
- board thermal constraints.

These should only be added with explicit, reviewable engineering rules and verified evidence where required.

## UI direction

The current Streamlit application uses a dark, compact, progressive workflow:

- show minimum inputs first;
- advanced installation conditions remain collapsed until needed;
- optional voltage-drop checks remain hidden until enabled;
- results remain hidden until calculation;
- changing inputs invalidates stale results;
- detailed reasoning is collapsed below the primary result;
- fields with discrete valid values use backend-owned selections instead of arbitrary free entry when practical.

Figma was used to establish this interaction direction before implementation. GitHub remains the implementation source of truth.

## Near-term roadmap

1. Expose the first Board Planner UI using the existing board backend.
2. Validate the board workflow through real use before adding more board-level intelligence.
3. Decide and document a defensible board-level diversity / maximum-demand model before implementing it.
4. Add board rating / incomer intelligence only after the diversity model and protection scope are clear.
5. Add ways/poles/spares as a separate board-layout concern rather than mixing it into circuit arithmetic.
6. Expand standards/data coverage only from verified sources.
7. Longer term, allow schedules, Excel/Revit workflows, or other project tools to feed the same reusable circuit/board engines.

## Testing / CI

Electrical checker changes are covered by unit and regression tests under `electrical-engineering/design-checker/tests/` and GitHub Actions currently runs the suite on Python 3.12 and 3.13.

When changing engineering behavior, add tests for the rule itself and for unsupported/edge cases. When changing UI routing, add regression guards so the UI continues to call backend-owned engineering logic rather than duplicating it.
