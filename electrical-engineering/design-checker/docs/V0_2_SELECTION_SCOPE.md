# V0.2 automatic circuit selection scope

The selector answers the forward-sizing question: given a load and supported installation conditions, what is the first breaker/cable combination in the declared candidate sets that passes the implemented numerical checks?

## Current supported slice

- load input: kW, kVA or A
- automatic cable selection: three-phase only
- XLPE/EPR multi-core cable, IEC reference Method E, air
- three loaded conductors
- copper or aluminium sizes already present in the verified V0 ampacity dataset
- supported ambient/grouping factors already present in the V0 dataset
- optional voltage-drop screening using the existing Annex G calculation module

## Safety rules

- Candidate cable sizes come only from the existing evidence-backed ampacity dataset.
- The cable must have Iz >= the suggested breaker In, not merely Iz >= Ib.
- A voltage-drop failure rejects that candidate when a permitted limit and source are supplied.
- Unsupported conditions are not interpolated or guessed.
- Breaker ratings are currently a declared conventional candidate set, **not an IEC 60364-4-43 verified selection**. Every suggestion carries this limitation until the current 4-43 source/rules layer is implemented.
- `NO SUPPORTED SOLUTION` means the current narrow dataset could not produce a suggestion; it does not prove that no engineering solution exists.
