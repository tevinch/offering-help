"""Run the actual Temoa/HiGHS example and inspect its saved SQLite results."""
from pathlib import Path
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest


class EmissionScopeWorkflow(unittest.TestCase):
    def test_scope_dispatch_price_and_two_myopic_stages(self):
        """Catch a broad cap, missing solve/stage, omitted coverage, or duplicate price."""
        script = Path(__file__).with_name("demo.py")
        self.assertTrue(script.is_file(), "The runnable consumer example is missing")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "results"
            run = subprocess.run(
                [sys.executable, str(script), "--output", str(output)],
                capture_output=True, text=True, timeout=180,
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            report = json.loads((output / "results.json").read_text())
            self.assertEqual(report["temoa_version"], "4.1.0")
            self.assertEqual(report["source_before"], report["source_after"])
            self.assertEqual(
                report["source_before"],
                hashlib.sha256((output / "source.sqlite").read_bytes()).hexdigest(),
            )
            with sqlite3.connect(output / "source.sqlite") as source:
                original = {
                    table: source.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
                    for table in ("region", "demand", "efficiency", "existing_capacity",
                                  "lifetime_process", "cost_variable", "time_period")
                }
            for name, expected in {
                "reference": (60, 40, 0, 100, 0),
                "scoped": (30, 70, 0, 100, 0),
                "wide": (30, 0, 70, 30, 0),
                "priced": (30, 70, 0, 100, 500),
                "price_only": (60, 40, 0, 100, 300),
                "high_price": (0, 0, 100, 0, 0),
                "myopic": (30, 70, 0, 100, 500),
            }.items():
                with self.subTest(case=name), sqlite3.connect(output / f"{name}.sqlite") as db:
                    periods = [r[0] for r in db.execute(
                        "SELECT DISTINCT period FROM output_flow_out ORDER BY period"
                    )]
                    self.assertEqual(periods, [2030, 2031])
                    self.assertEqual(db.execute("SELECT region FROM region ORDER BY region").fetchall(),
                                     [("North",), ("South",)])
                    for table, rows in original.items():
                        self.assertEqual(db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall(), rows)
                    self.assertEqual(db.execute(
                        "SELECT period,value FROM limit_emission WHERE region='global' "
                        "AND emis_comm='CO2' ORDER BY period"
                    ).fetchall(), [(2030, 1000), (2031, 1000)])
                    for period in periods:
                        flows = dict(db.execute(
                            "SELECT tech, SUM(flow) FROM output_flow_out WHERE period=? GROUP BY tech",
                            (period,),
                        ))
                        covered = flows.get("covered", 0)
                        outside = flows.get("outside", 0)
                        clean = flows.get("clean", 0)
                        physical = db.execute(
                            "SELECT COALESCE(SUM(emission),0) FROM output_emission "
                            "WHERE period=? AND emis_comm='CO2'", (period,),
                        ).fetchone()[0]
                        if name != "reference":
                            covered_emissions = db.execute(
                                "SELECT COALESCE(SUM(emission),0) FROM output_emission "
                                "WHERE period=? AND emis_comm='CO2_covered'", (period,),
                            ).fetchone()[0]
                            self.assertAlmostEqual(covered_emissions, covered, places=6)
                        charge = db.execute(
                            "SELECT COALESCE(SUM(emiss),0) FROM output_cost WHERE period=?", (period,),
                        ).fetchone()[0]
                        for got, want in zip((covered, outside, clean, physical, charge), expected):
                            self.assertAlmostEqual(got, want, places=6)
                    if name in {"scoped", "priced", "myopic"}:
                        self.assertGreater(db.execute(
                            "SELECT SUM(flow) FROM output_flow_out "
                            "WHERE region='North' AND tech='outside'"
                        ).fetchone()[0], 0)
                        self.assertGreater(db.execute(
                            "SELECT SUM(flow) FROM output_flow_out "
                            "WHERE region='South' AND tech='outside'"
                        ).fetchone()[0], 0)
                        self.assertEqual(db.execute(
                            "SELECT DISTINCT tech FROM emission_activity WHERE emis_comm='CO2_covered'"
                        ).fetchall(), [("covered",)])
                    if name in {"priced", "myopic"}:
                        self.assertEqual(db.execute(
                            "SELECT COUNT(*) FROM cost_emission WHERE emis_comm='CO2_covered'"
                        ).fetchone()[0], 0)
            self.assertEqual(report["cases"]["myopic"]["solved_base_years"], [2030, 2031])
            for name in ("scoped", "priced"):
                for constraint in report["cases"][name]["scoped_constraints"]:
                    self.assertAlmostEqual(constraint["body"], 30, places=6)
                    self.assertAlmostEqual(constraint["upper"], 30, places=6)
                    self.assertTrue(constraint["variables"])
                    self.assertTrue(all("covered" in v and "outside" not in v
                                        for v in constraint["variables"]))
                self.assertTrue(report["cases"][name]["scoped_constraints"])
            stage_paths = [output / x for x in report["cases"]["myopic"]["lp_files"]]
            self.assertEqual(len(stage_paths), 2)
            for lp in stage_paths:
                self.assertTrue(lp.is_file())
                self.assertIn("CO2_covered", lp.read_text())
            # The source remains the unaugmented, unsolved synthetic input.
            with sqlite3.connect(output / "source.sqlite") as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM output_flow_out").fetchone()[0], 0)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM commodity WHERE name='CO2_covered'").fetchone()[0], 0)
                self.assertEqual(db.execute("SELECT SUM(demand) FROM demand").fetchone()[0], 200)


if __name__ == "__main__":
    unittest.main()
