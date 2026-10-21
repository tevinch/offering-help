# Cap emissions from selected Temoa processes

Keep the existing regions and physical `CO2` accounting. Add a second emission commodity, `CO2_covered`, whose activity coefficients exist only for the processes covered by the intended cap. Apply that cap to `CO2_covered`. An existing price on physical `CO2` can continue to apply to all emitting processes.

This is a runnable input-data example for **Temoa 4.1.0, Python 3.12 and HiGHS**, using ordinary activity emissions. It creates a small synthetic model; it does not modify an existing model database.

## Run

From this directory:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python demo.py --output results
python -m unittest -v test_demo.py
```

Choose a new output directory for each run. The script refuses to overwrite one that already exists. `results/` contains the source fixture, seven independently solved databases, solver logs, LP files and a `results.json` summary. The test runs the complete example in a temporary directory and independently queries its SQLite outputs.

## What the solved example shows

Both periods, 2030 and 2031, have demand 60 in North and 40 in South. North has covered and uncovered emitting generators plus a clean alternative. South has an uncovered emitting generator and a clean alternative. All capacities, lifetimes, efficiencies, region names and demands stay the same across cases. Costs favor covered generation first, then uncovered generation, then clean generation. The cap uses the unchanged `North+South` region group.

Actual results in **each** period:

| Case | Covered generation | Uncovered generation | Clean generation | Physical CO₂ | Emission cost |
| --- | ---: | ---: | ---: | ---: | ---: |
| No program cap | 60 | 40 | 0 | 100 | 0 |
| Cap `CO2_covered` at 30 | 30 | 70 | 0 | 100 | 0 |
| Cap physical `CO2` at 30 | 30 | 0 | 70 | 30 | 0 |
| Subset cap plus physical CO₂ price 5 | 30 | 70 | 0 | 100 | 500 |
| Covered-label price 5, no program cap | 60 | 40 | 0 | 100 | 300 |
| Subset cap plus physical CO₂ price 200 | 0 | 0 | 100 | 0 | 0 |
| Subset cap plus physical CO₂ price 5, myopic | 30 | 70 | 0 | 100 | 500 |

All quantities and costs use consistent synthetic model units. Costs are undiscounted per-period emission-cost outputs; they are not currency receipts or a real policy calibration.

The subset cap binds at 30 while uncovered generation remains positive in **both** regions: North contributes 30 and South 40. Physical emissions stay 100. Applying the same limit to physical `CO2` instead forces 70 units of clean generation. A small fixed price on the covered label leaves covered emissions at 60, so a price does not guarantee the quantity limit.

The physical CO₂ price charges all 100 units, including the uncovered 70: `5 × 100 = 500`. The overlapping label has no additional price in that case. The myopic example actually solves two one-period stages; its LP files and saved results cover both 2030 and 2031.

The test also checks optimal perfect-foresight termination, the solved subset constraint's variables and bound, both myopic stages' output, preservation of the original input tables and an unrelated global CO₂ cap, and an unchanged source database hash.

## Apply the accounting pattern

1. Work on a copy of your input database. Define the covered processes explicitly using the full region/input/technology/vintage/output key.
2. Keep every original physical `CO2` activity coefficient. Add `CO2_covered` as an emission commodity and copy the coefficients only for the covered keys. In the synthetic model, every vintage of the toy technology named `covered` is covered; that name-based filter is specific to this fixture.
3. Change only the intended program cap's emission commodity to `CO2_covered`, preserving its period, bound and existing region group. Retain unrelated legitimate physical-CO₂ caps.
4. Keep an existing physical-CO₂ price on `CO2`. Do not also price the overlapping label unless a separate additional charge is intended. If you want a price only on covered emissions, that is a different objective-cost scenario; it still does not enforce a quantity cap.
5. Compare a no-program-cap run, the subset-cap run and a whole-region physical-cap run. Inspect the actual covered and uncovered process flows, emissions and costs in every solved period, including every myopic stage.

`CO2_covered` is a second measurement of some of the same emissions. **Do not add `CO2` and `CO2_covered` together as physical emissions.** Copy coefficients in the same units as the original cap, with the same treatment of vintages and activity.

A label cannot infer geographic coverage inside an already aggregated process row. If a single PJME technology/vintage row combines covered and uncovered facilities, you still need a defensible process-level allocation or a more detailed process representation. Naming a second commodity does not recover that missing information. The example does not determine which facilities belong in any real program.

This example covers ordinary activity emissions. It does not establish equivalent handling of embodied emissions, retirement emissions, unit commitment, flex technologies or curtailment across different Temoa versions.

## Older `mip-dev` models

The public `mip-dev` source uses the same basic selection by emission commodity, with different input names:

| Meaning | Temoa 4.1.0 | Public `mip-dev` schema |
| --- | --- | --- |
| Emission commodity | `commodity(name, flag='e')` | `commodities(comm_name, flag='e')` |
| Activity coefficient | `emission_activity.activity` | `EmissionActivity.emis_act` |
| Region and period columns | `region`, `period` | `regions`, `periods` |
| Cap | `limit_emission(..., operator='le', value=...)` | `EmissionLimit(..., emis_limit=...)` |

For that schema, retain physical `CO2` rows, add the new name to `commodities`, duplicate only the covered process keys in `EmissionActivity`, and redirect the intended `EmissionLimit` row to the new commodity. Its `EmissionLimit_Constraint` selects the requested `emis_comm` and accepts a `+`-joined region group. Preserve the original group string rather than assuming a new region is required.

This mapping is based on reading public `mip-dev` commit `424017755dac106ad3beb26c4cd89dece8546603`. The executable example and cost results above were tested with the released **4.1.0** package and HiGHS. They do not validate a private fork, its pricing extensions, Python 3.11, Gurobi or an HPC configuration. Check that fork's exact schema, constraint implementation and myopic input filtering before adopting the pattern there; the stable package's pricing table is not a claim about the older fork's pricing API.

## Sources and dependency boundary

- [Temoa 4.1.0 release](https://github.com/TemoaProject/temoa/releases/tag/v4.1.0)
- [Official programmatic usage](https://github.com/TemoaProject/temoa/blob/v4.1.0/README.md#programmatic-usage)
- [4.1.0 emission-limit implementation](https://github.com/TemoaProject/temoa/blob/v4.1.0/temoa/components/limits.py)
- [4.1.0 emission-cost implementation](https://github.com/TemoaProject/temoa/blob/v4.1.0/temoa/components/costs.py)
- [Pinned public `mip-dev` emission constraint](https://github.com/TemoaProject/temoa/blob/424017755dac106ad3beb26c4cd89dece8546603/temoa_model/temoa_rules.py#L1530)
- [Pinned public `mip-dev` database schema](https://github.com/TemoaProject/temoa/blob/424017755dac106ad3beb26c4cd89dece8546603/data_files/temoa_schema.sql)

`demo.py` and `test_demo.py` are original consumer examples. The script loads the schema from the installed Temoa package; no upstream schema or model implementation is bundled here. Temoa 4.1.0 declares an MIT license. Installed dependencies retain their own licenses. The older branch is linked as a source reference and its code is not included in this example.

## Optional coffee

This example is free. If it helped, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
