# Read vocabulary links from netCDF variables

Find candidate variables across two files even when their local names differ. This example reads each variable's annotation, retrieves its label and definition from the NERC Vocabulary Server (NVS), and reports the direct relation between the annotated concepts. It opens inputs read-only and leaves arrays and attributes unchanged.

For the pair in [this consumer question](https://github.com/nvs-vocabs/Guides-and-Resources/issues/6), `OG1:TCPUCHLA` and `P01:TCNTICPU` have a direct `skos:related` link in the responses checked on 2026-10-26. That is an association requiring review. It does not establish that the measurements can be substituted or merged. The separate conductivity pair `OG1:CNDC` / `P01:CNDCZZ01` illustrates an explicit `owl:sameAs` assertion; dataset compatibility still needs checking.

## Run the complete example

Use Python 3.11 or later. From this directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --index-url https://pypi.org/simple --only-binary=:all: -r requirements.txt
.venv/bin/python make_demo.py demo
.venv/bin/python inspect_vocab.py demo/og.nc demo/partner.nc > report.json
.venv/bin/python -m unittest -v
```

The dependency is pinned to the tested netCDF4 1.7.4 wheel (Python 3.12, macOS 14 arm64). At the check date, [PyPI's latest release](https://pypi.org/project/netCDF4/) is 1.7.5.1.post1; its macOS wheels require macOS 15. The pin makes the binary-only install usable on the tested system. No source build is needed. See the [public Dataset API](https://unidata.github.io/netcdf4-python/) for other netCDF operations.

`make_demo.py` writes two small **synthetic** files, with two measurements and an unannotated sample index in each. It refuses to write either output if `og.nc` or `partner.nc` already exists. Run the inspection command again on the same files; to regenerate, choose a new directory. These are focused metadata examples, not complete CF or OceanGliders mission datasets. Full [official OceanGliders example files](https://github.com/OceanGlidersCommunity/OG-format-user-manual/tree/main/og_format_examples_files) already exist.

The four distinct concept requests use the [documented NVS API](https://vocab.nerc.ac.uk/doc/api) over HTTPS with JSON-LD content negotiation. Internet access is required. `current` records can change, so the report includes the retrieval time, request URL, concept version and current-version identifier when supplied. A service, JSON or metadata error exits nonzero, writes an explanation to stderr and prints no success report. Shell redirection may leave an empty `report.json` after failure; check the command's exit status before using it. There are no automatic retries.

## Read the result

```sh
.venv/bin/python -c 'import json; r=json.load(open("report.json")); [print(c["left"]["variable"], "->", c["right"]["variable"], c["status"], [e["predicate"] for e in c["relations"]]) for c in r["comparisons"]]'
```

The report separates:

- `variables`: actual file/variable names, dimensions, shape, units and annotation. An absent attribute is `missing_vocabulary`, including each sample index.
- `concepts`: canonical identifier, authoritative label/definition, deprecation/version information, retrieval provenance and direct edges. Look up a variable's `vocabulary` in this dictionary to enrich its local name with the source definition.
- `comparisons`: annotated variables from different input files, direct edges as `subject` / `predicate` / `object`, and a review status.

Expected statuses for the synthetic files, based on the checked service records:

| Variables | Status | Meaning |
| --- | --- | --- |
| `TCPUCHLA` → `cpu_temperature` | `direct_relation_review_needed` | Both retrieved nodes assert `skos:related`; no direct identity assertion for this pair. |
| `CNDC` → `conductivity` | `concept_identity_review_needed` | The retrieved nodes assert `owl:sameAs` for these concepts. |
| Either cross-pair | `no_direct_mapping` | No supported direct predicate connects this pair in the two retrieved nodes. This does not prove different scientific meaning. |

`same_identifier_review_needed` and `concept_exact_match_review_needed` distinguish a shared identifier and a `skos:exactMatch` mapping. Exact match is a SKOS retrieval-level mapping; the report preserves it separately from OWL identity. Other links, including `skos:closeMatch`, remain `direct_relation_review_needed`. In `A skos:broader B`, **B** is broader; in `A skos:narrower B`, **B** is narrower. Direction is retained even when only one node asserts a link. See the [SKOS relation definitions](https://www.w3.org/TR/skos-reference/#semantic-relations) and [mapping definitions](https://www.w3.org/TR/skos-reference/#mapping).

Every comparison reports `data_equivalence: not_assessed`. Before comparing or combining observations, check units, calibration, processing, coordinates/time alignment and QC. Matching units alone is insufficient. There is no numerical conversion, merging, transitive reasoning or label matching here.

## Use your own files

```sh
.venv/bin/python inspect_vocab.py first.nc second.nc --timeout 20 > report.json
.venv/bin/python inspect_vocab.py first.nc second.nc --attribute vocabulary_uri > report.json
```

The default `vocabulary` attribute follows the [OceanGliders format manual](https://oceangliderscommunity.github.io/OG-format-user-manual/OG_Format.html). It is separate from `standard_name` and `units`; netCDF itself does not prescribe a universal vocabulary attribute. Use `--attribute` explicitly for another producer convention. All root variables are listed; nested groups are outside this small example's scope.

Supported annotations are canonical `http://vocab.nerc.ac.uk/collection/COLLECTION/current/CONCEPT/` identifiers, including the trailing slash. The [NVS HTTP/HTTPS guidance](https://github.com/nvs-vocabs/Guides-and-Resources/blob/main/HTTP%20versus%20HTTPS.md) distinguishes these identifiers from HTTPS retrieval. The script preserves identifiers exactly; it does not rewrite RDF identity to HTTPS. Unsupported identifiers fail clearly instead of being guessed.

The parser handles the service's compact single-node or list-of-nodes JSON-LD shape, verifies the selected `@id` and the SKOS/OWL/PAV namespaces, and reads only the listed direct predicates. It is not a general JSON-LD processor. Requests are limited to 32 distinct concepts per run, with a 1–60 second timeout per request and a 2 MB response limit. Redirects are rejected. Review a saved report rather than repeatedly requesting the same concepts.

## Sources and reuse

The example source is original and uses this repository's MIT license. Retrieved labels, definitions and semantic links come from the [NERC Vocabulary Server](https://vocab.nerc.ac.uk/), operated by BODC at the National Oceanography Centre, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) as described in [NVS's terms](https://vocab.nerc.ac.uk/about). Attribute these sources if redistributing a report; the source-data license is separate from the example's code license.

- [OceanGliders Parameter Usage Vocabulary (OG1)](https://vocab.nerc.ac.uk/collection/OG1/current/), created by the OceanGliders Data Management Task Team: [TCPUCHLA](https://vocab.nerc.ac.uk/collection/OG1/current/TCPUCHLA/) and [CNDC](https://vocab.nerc.ac.uk/collection/OG1/current/CNDC/).
- [BODC Parameter Usage Vocabulary (P01)](https://vocab.nerc.ac.uk/collection/P01/current/), from the British Oceanographic Data Centre: [TCNTICPU](https://vocab.nerc.ac.uk/collection/P01/current/TCNTICPU/) and [CNDCZZ01](https://vocab.nerc.ac.uk/collection/P01/current/CNDCZZ01/).

The report extracts fields and preserves direct assertions from live records; it does not modify their source definitions. The tests use synthetic metadata and actual local netCDF files. They do not establish validation on a real mission dataset or scientific suitability for a particular analysis.

## Optional coffee

This example is free. If it saved you time, an entirely optional coffee is welcome:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
