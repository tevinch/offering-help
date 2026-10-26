"""Offline tests; the live API is exercised by the README command separately."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

from netCDF4 import Dataset

A = "http://vocab.nerc.ac.uk/collection/OG1/current/TCPUCHLA/"
B = "http://vocab.nerc.ac.uk/collection/P01/current/TCNTICPU/"
CONTEXT = {"skos": "http://www.w3.org/2004/02/skos/core#",
           "owl": "http://www.w3.org/2002/07/owl#", "pav": "http://purl.org/pav/"}

def node(uri=A, **relations):
    return {"@id": uri, "@context": CONTEXT.copy(), "@type": "skos:Concept",
            "skos:prefLabel": {"@value": "Example concept", "@language": "en"},
            "skos:definition": {"@value": "Synthetic test definition.", "@language": "en"},
            "owl:deprecated": "false", "pav:version": "2", **relations}

class LookupTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(Path("inspect_vocab.py").exists(), "lookup script is missing")
        import inspect_vocab
        self.lookup = inspect_vocab

    def test_jsonld_single_and_list_keep_canonical_id_and_direct_edges(self):
        payload = node(**{"skos:related": {"@id": B}})
        for shape in (payload, [payload]):
            concept = self.lookup.parse_concept(shape, A)
            self.assertEqual(concept["id"], A)
            self.assertEqual(concept["relations"], [{"subject": A, "predicate": "skos:related", "object": B}])
            self.assertFalse(concept["deprecated"])
            self.assertEqual(concept["version"], "2")

    def test_related_is_not_identity_and_hierarchy_direction_is_retained(self):
        left = self.lookup.parse_concept(node(**{"skos:related": {"@id": B}}), A)
        right = self.lookup.parse_concept(node(B, **{"skos:broader": {"@id": A},
                                                    "skos:narrower": [{"@id": A}]}), B)
        relations, status = self.lookup.compare_concepts(left, right)
        self.assertEqual(status, "direct_relation_review_needed")
        self.assertIn({"subject": B, "predicate": "skos:broader", "object": A}, relations)
        self.assertIn({"subject": B, "predicate": "skos:narrower", "object": A}, relations)

    def test_identity_exact_match_absence_and_same_identifier_are_distinct(self):
        left = self.lookup.parse_concept(node(), A)
        for predicate, status in [("owl:sameAs", "concept_identity_review_needed"),
                                  ("skos:exactMatch", "concept_exact_match_review_needed")]:
            right = self.lookup.parse_concept(node(B, **{predicate: {"@id": A}}), B)
            self.assertEqual(self.lookup.compare_concepts(left, right)[1], status)
        other = self.lookup.parse_concept(node(B), B)
        self.assertEqual(self.lookup.compare_concepts(left, other), ([], "no_direct_mapping"))
        self.assertEqual(self.lookup.compare_concepts(left, left)[1], "same_identifier_review_needed")

    def test_malformed_or_mismatched_metadata_cannot_be_success(self):
        bad_context = node()
        bad_context["@context"]["skos"] = "https://example.com/other#"
        bad_term = node()
        bad_term["@context"]["skos:related"] = "https://example.com/other#relation"
        for bad in ({}, node(B), [node(), node()], bad_context, bad_term,
                    node(**{"skos:related": "not-a-node"}), node(**{"skos:definition": {}})):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.lookup.parse_concept(bad, A)
        for bad_uri in (A.replace("http:", "https:"), A.rstrip("/"),
                        "https://example.com/collection/OG1/current/X/", A + "?x=1"):
            with self.subTest(uri=bad_uri), self.assertRaises(ValueError):
                self.lookup.fetch_url(bad_uri)

    def test_native_input_metadata_and_data_survive_and_missing_attribute_is_visible(self):
        import make_demo
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            make_demo.make_demo(folder)
            paths = [folder / "og.nc", folder / "partner.nc"]
            before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
            variables = self.lookup.read_variables(paths, "vocabulary")
            self.assertEqual(len(variables), 6)
            self.assertEqual(sum(v["status"] == "missing_vocabulary" for v in variables), 2)
            self.assertEqual(next(v for v in variables if v["variable"] == "cpu_temperature")["vocabulary"], B)
            with Dataset(paths[0], "r") as ds:
                self.assertEqual(ds.variables["TCPUCHLA"][:].tolist(), [100.0, 101.0, 102.0])
                self.assertEqual(ds.variables["TCPUCHLA"].units, "1")
            self.assertEqual([hashlib.sha256(p.read_bytes()).hexdigest() for p in paths], before)
            missing = self.lookup.read_variables(paths, "other_attribute")
            self.assertTrue(all(v["status"] == "missing_vocabulary" for v in missing))
            with self.assertRaises(OSError):
                self.lookup.read_variables([folder / "absent.nc"], "vocabulary")

    def test_generator_refuses_both_outputs_if_either_exists(self):
        import make_demo
        for existing in ("og.nc", "partner.nc"):
            with tempfile.TemporaryDirectory() as td:
                folder = Path(td)
                (folder / existing).write_bytes(b"keep this")
                with self.assertRaises(FileExistsError):
                    make_demo.make_demo(folder)
                self.assertEqual(list(folder.iterdir()), [folder / existing])
                self.assertEqual((folder / existing).read_bytes(), b"keep this")

    def test_redirect_is_rejected_before_any_followup_request(self):
        self.assertTrue(hasattr(self.lookup, "NVSRedirectHandler"), "redirect boundary missing")
        received = []
        class Redirect(BaseHTTPRequestHandler):
            def do_GET(self):
                received.append(self.path)
                self.send_response(302)
                self.send_header("Location", "/must-not-follow")
                self.end_headers()
            def log_message(self, *args):
                pass
        with HTTPServer(("127.0.0.1", 0), Redirect) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                opener = urllib.request.build_opener(self.lookup.NVSRedirectHandler())
                with self.assertRaises(urllib.error.HTTPError):
                    opener.open(f"http://127.0.0.1:{server.server_port}/start", timeout=2)
                self.assertEqual(received, ["/start"])
            finally:
                server.shutdown()
                worker.join()

    def test_http_error_and_invalid_json_emit_no_successful_report(self):
        import contextlib
        import io
        import make_demo
        with tempfile.TemporaryDirectory() as td:
            make_demo.make_demo(Path(td))
            error = urllib.error.HTTPError("https://vocab.nerc.ac.uk/", 503, "Unavailable", {}, None)
            with patch.object(self.lookup.HTTP, "open", side_effect=error), \
                 contextlib.redirect_stdout(io.StringIO()) as out, \
                 contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(self.lookup.main([str(Path(td) / "og.nc")]), 1)
            self.assertEqual(out.getvalue(), "")
            self.assertIn("503", err.getvalue())
        class Response(io.BytesIO):
            status = 200
            def geturl(self):
                return "https://vocab.nerc.ac.uk/collection/OG1/current/TCPUCHLA/?_mediatype=application/ld+json"
        with patch.object(self.lookup.HTTP, "open", return_value=Response(b"<html>oops</html>")):
            with self.assertRaises(ValueError):
                self.lookup.fetch_concept(A, 10)

if __name__ == "__main__":
    unittest.main()
