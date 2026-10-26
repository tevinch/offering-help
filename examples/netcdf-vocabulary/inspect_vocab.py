"""Read root netCDF variable annotations and report direct NVS concept links."""
import argparse
from datetime import datetime, timezone
import itertools
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from netCDF4 import Dataset

NAMESPACES = {"skos": "http://www.w3.org/2004/02/skos/core#",
              "owl": "http://www.w3.org/2002/07/owl#", "pav": "http://purl.org/pav/"}
PREDICATES = ("owl:sameAs", "skos:exactMatch", "skos:closeMatch", "skos:related",
              "skos:broader", "skos:narrower", "skos:broadMatch", "skos:narrowMatch",
              "skos:relatedMatch", "skos:broaderTransitive", "skos:narrowerTransitive")
IRI = re.compile(r"http://vocab\.nerc\.ac\.uk/collection/[A-Z0-9]+/current/[A-Za-z0-9_-]+/")


def fetch_url(uri):
    if not isinstance(uri, str) or not IRI.fullmatch(uri):
        raise ValueError(f"Unsupported canonical NVS current-concept identifier: {uri!r}")
    return uri.replace("http://", "https://", 1) + "?_mediatype=application/ld+json"


def as_list(value):
    return value if isinstance(value, list) else [value]


def english_text(value):
    for item in as_list(value):
        if isinstance(item, str) and item:
            return item
        if (isinstance(item, dict) and item.get("@language", "en") == "en"
                and isinstance(item.get("@value"), str) and item["@value"]):
            return item["@value"]
    raise ValueError("Missing English label or definition in NVS response")


def parse_concept(payload, uri):
    """Bounded parser for the NVS compact JSON-LD response, without inference."""
    fetch_url(uri)
    nodes = as_list(payload)
    matching = [n for n in nodes if isinstance(n, dict) and n.get("@id") == uri]
    if len(matching) != 1:
        raise ValueError(f"Expected exactly one NVS node with @id {uri}")
    node = matching[0]
    context = node.get("@context")
    if not isinstance(context, dict) or any(context.get(k) != v for k, v in NAMESPACES.items()):
        raise ValueError("Missing or unexpected NVS JSON-LD namespace context")
    used_terms = set(PREDICATES) | {"skos:Concept", "skos:prefLabel", "skos:definition",
                                    "owl:deprecated", "pav:version", "pav:hasCurrentVersion"}
    if used_terms.intersection(context):
        raise ValueError("Term overrides are outside this compact JSON-LD example's scope")
    if "skos:Concept" not in as_list(node.get("@type")):
        raise ValueError("NVS response is not a skos:Concept")
    edges = []
    for predicate in PREDICATES:
        for value in as_list(node.get(predicate, [])):
            target = value.get("@id") if isinstance(value, dict) else None
            if not isinstance(target, str) or not target.startswith(("http://", "https://")):
                raise ValueError(f"Malformed {predicate} link in {uri}")
            edges.append({"subject": uri, "predicate": predicate, "object": target})
    deprecated = node.get("owl:deprecated")
    if deprecated not in (None, True, False, "true", "false"):
        raise ValueError("Unexpected owl:deprecated value")
    current = node.get("pav:hasCurrentVersion")
    if current is not None and (not isinstance(current, dict) or not isinstance(current.get("@id"), str)):
        raise ValueError("Malformed pav:hasCurrentVersion")
    return {"id": uri, "label": english_text(node.get("skos:prefLabel")),
            "definition": english_text(node.get("skos:definition")),
            "deprecated": None if deprecated is None else deprecated in (True, "true"),
            "version": node.get("pav:version"),
            "current_version_id": current["@id"] if current else None, "relations": edges}


class NVSRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        raise urllib.error.HTTPError(request.full_url, code, "Redirects are outside this example\'s scope", headers, None)


HTTP = urllib.request.build_opener(NVSRedirectHandler())


def fetch_concept(uri, timeout):
    url = fetch_url(uri)
    request = urllib.request.Request(url, headers={"Accept": "application/ld+json"})
    with HTTP.open(request, timeout=timeout) as response:
        final = urllib.parse.urlsplit(response.geturl())
        if final.scheme != "https" or final.netloc != "vocab.nerc.ac.uk":
            raise ValueError("Unexpected NVS response location")
        if response.status != 200:
            raise ValueError(f"NVS returned HTTP {response.status}")
        body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise ValueError("NVS concept response exceeds 2 MB")
    result = parse_concept(json.loads(body), uri)
    result.update(fetch_url=url, retrieved_at=datetime.now(timezone.utc).isoformat())
    return result


def read_variables(paths, attribute):
    variables = []
    for path in paths:
        path = Path(path)
        with Dataset(path, "r") as dataset:
            for name, variable in dataset.variables.items():
                uri = variable.getncattr(attribute) if attribute in variable.ncattrs() else None
                if uri is not None:
                    fetch_url(uri)
                units = variable.getncattr("units") if "units" in variable.ncattrs() else None
                variables.append({"file": str(path), "variable": name,
                                  "dimensions": list(variable.dimensions), "shape": list(variable.shape),
                                  "units": str(units) if units is not None else None,
                                  "vocabulary": uri,
                                  "status": "annotated" if uri is not None else "missing_vocabulary"})
    return variables


def compare_concepts(left, right):
    a, b = left["id"], right["id"]
    relations = [edge for edge in left["relations"] + right["relations"]
                 if (edge["subject"], edge["object"]) in ((a, b), (b, a))]
    predicates = {edge["predicate"] for edge in relations}
    if a == b:
        status = "same_identifier_review_needed"
    elif "owl:sameAs" in predicates:
        status = "concept_identity_review_needed"
    elif "skos:exactMatch" in predicates:
        status = "concept_exact_match_review_needed"
    else:
        status = "direct_relation_review_needed" if relations else "no_direct_mapping"
    return relations, status


def inspect(paths, attribute="vocabulary", timeout=20):
    variables = read_variables(paths, attribute)
    uris = list(dict.fromkeys(v["vocabulary"] for v in variables if v["vocabulary"] is not None))
    if len(uris) > 32:
        raise ValueError("This small example supports at most 32 distinct concepts per run")
    concepts = {uri: fetch_concept(uri, timeout) for uri in uris}
    comparisons = []
    annotated = [v for v in variables if v["vocabulary"] is not None]
    for left, right in itertools.combinations(annotated, 2):
        if left["file"] == right["file"]:
            continue
        relations, status = compare_concepts(concepts[left["vocabulary"]], concepts[right["vocabulary"]])
        comparisons.append({"left": left, "right": right, "relations": relations,
                            "status": status, "data_equivalence": "not_assessed"})
    return {"attribute": attribute, "variables": variables, "concepts": concepts,
            "comparisons": comparisons,
            "review": "Direct concept links only. Check units, calibration, processing, coordinates/time and QC before comparing or combining observations. No arrays are merged or modified."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--attribute", default="vocabulary")
    parser.add_argument("--timeout", type=float, default=20, help="Seconds per request (1–60)")
    args = parser.parse_args(argv)
    if not 1 <= args.timeout <= 60:
        parser.error("--timeout must be between 1 and 60 seconds")
    try:
        report = inspect(args.files, args.attribute, args.timeout)
        rendered = json.dumps(report, indent=2, ensure_ascii=False)
    except (OSError, ValueError, TypeError, urllib.error.URLError) as error:
        print(f"Lookup failed: {error}", file=sys.stderr)
        return 1
    print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
