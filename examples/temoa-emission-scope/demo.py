"""Solve a small emissions-accounting example with Temoa 4.1.0 and HiGHS."""
from __future__ import annotations

import argparse
import hashlib
from importlib import metadata, resources
import json
from pathlib import Path
import shutil
import sqlite3

from pyomo.environ import check_optimal_termination, value
from pyomo.repn import generate_standard_repn
from temoa._internal.temoa_sequencer import TemoaSequencer
from temoa.cli import setup_logging
from temoa.core.config import TemoaConfig

PERIODS = (2030, 2031)


def create_source(path: Path) -> None:
    """Create only our own synthetic input, using the installed package's schema."""
    schema = resources.files("temoa").joinpath("db_schema/temoa_schema_v4.sql").read_text()
    with sqlite3.connect(path) as db:
        db.executescript(schema)
        db.execute("UPDATE metadata_real SET value=0.01 WHERE element='global_discount_rate'")
        db.executemany("INSERT INTO region(region) VALUES(?)", [("North",), ("South",)])
        db.execute("INSERT INTO sector_label(sector) VALUES('power')")
        db.executemany("INSERT INTO commodity(name,flag) VALUES(?,?)", [
            ("fuel", "s"), ("clean_source", "s"), ("power", "d"), ("CO2", "e"),
        ])
        db.executemany("INSERT INTO time_period VALUES(?,?,?)", [
            (0, 2020, "e"), (1, 2030, "f"), (2, 2031, "f"), (3, 2032, "f"),
        ])
        db.execute("INSERT INTO time_season VALUES(1,'year',1,NULL)")
        db.execute("INSERT INTO time_of_day VALUES(1,'all',24,NULL)")
        for tech in ("covered", "outside", "clean"):
            db.execute("INSERT INTO technology(tech,flag,sector) VALUES(?,'p','power')", (tech,))
        for region, tech, fuel, cost in [
            ("North", "covered", "fuel", 10),
            ("North", "outside", "fuel", 20),
            ("North", "clean", "clean_source", 100),
            ("South", "outside", "fuel", 20),
            ("South", "clean", "clean_source", 100),
        ]:
            db.execute("INSERT INTO efficiency(region,input_comm,tech,vintage,output_comm,efficiency) "
                       "VALUES(?,?,?,2020,'power',1)", (region, fuel, tech))
            db.execute("INSERT INTO existing_capacity(region,tech,vintage,capacity) VALUES(?,?,2020,100)",
                       (region, tech))
            db.execute("INSERT INTO lifetime_process(region,tech,vintage,lifetime) VALUES(?,?,2020,50)",
                       (region, tech))
            if tech != "clean":
                db.execute("INSERT INTO emission_activity(region,emis_comm,input_comm,tech,vintage,output_comm,activity) "
                           "VALUES(?,'CO2',?,?,2020,'power',1)", (region, fuel, tech))
            for period in PERIODS:
                db.execute("INSERT INTO cost_variable(region,period,tech,vintage,cost) VALUES(?,?,?,2020,?)",
                           (region, period, tech, cost))
        for period in PERIODS:
            for region, demand in (("North", 60), ("South", 40)):
                db.execute("INSERT INTO demand(region,period,commodity,demand) VALUES(?,?,'power',?)",
                           (region, period, demand))
            # This independent, loose physical cap is preserved in every variant.
            db.execute("INSERT INTO limit_emission(region,period,emis_comm,operator,value) "
                       "VALUES('global',?,'CO2','le',1000)", (period,))
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("The synthetic input has invalid foreign keys")


def configure_case(path: Path, name: str) -> None:
    with sqlite3.connect(path) as db:
        if name != "reference":
            db.execute("INSERT INTO commodity(name,flag,description) "
                       "VALUES('CO2_covered','e','Overlapping accounting label for covered processes')")
            db.execute("INSERT INTO emission_activity "
                       "SELECT region,'CO2_covered',input_comm,tech,vintage,output_comm,activity,units,notes "
                       "FROM emission_activity WHERE emis_comm='CO2' AND tech='covered'")
        if name in {"scoped", "priced", "high_price", "myopic"}:
            cap_label = "CO2_covered"
        elif name == "wide":
            cap_label = "CO2"
        else:
            cap_label = None
        for period in PERIODS:
            if cap_label:
                db.execute("INSERT INTO limit_emission(region,period,emis_comm,operator,value) "
                           "VALUES('North+South',?,?,'le',30)", (period, cap_label))
            if name in {"priced", "myopic", "high_price"}:
                price = 200 if name == "high_price" else 5
                for region in ("North", "South"):
                    db.execute("INSERT INTO cost_emission(region,period,emis_comm,cost) VALUES(?,?,'CO2',?)",
                               (region, period, price))
            if name == "price_only":
                db.execute("INSERT INTO cost_emission(region,period,emis_comm,cost) "
                           "VALUES('North',?,'CO2_covered',5)", (period,))


def read_summary(path: Path) -> list[dict]:
    with sqlite3.connect(path) as db:
        rows = []
        for period in PERIODS:
            flows = dict(db.execute("SELECT tech,SUM(flow) FROM output_flow_out WHERE period=? GROUP BY tech",
                                    (period,)))
            physical = db.execute("SELECT COALESCE(SUM(emission),0) FROM output_emission "
                                  "WHERE period=? AND emis_comm='CO2'", (period,)).fetchone()[0]
            covered = db.execute("SELECT COALESCE(SUM(emission),0) FROM output_emission "
                                 "WHERE period=? AND emis_comm='CO2_covered'", (period,)).fetchone()[0]
            charge = db.execute("SELECT COALESCE(SUM(emiss),0) FROM output_cost WHERE period=?",
                                (period,)).fetchone()[0]
            rows.append({"period": period, "generation": flows, "physical_CO2": physical,
                         "covered_CO2": covered, "emission_cost": charge})
        return rows


def solve_case(path: Path, directory: Path, name: str) -> dict:
    directory.mkdir()
    setup_logging(directory, debug=False, silent=True)
    config = TemoaConfig(
        scenario=name, scenario_mode="myopic" if name == "myopic" else "perfect_foresight",
        input_database=path, output_database=path, output_path=directory,
        solver="appsi_highs", time_sequencing="seasonal_timeslices",
        price_check=False, save_lp_file=True, silent=True,
        myopic={"view_depth": 1, "step_size": 1, "evolving": False} if name == "myopic" else None,
    )
    run = TemoaSequencer(config=config)
    run.start()
    constraints = []
    if name != "myopic":
        if not check_optimal_termination(run.pf_results):
            raise RuntimeError(f"{name}: optimization did not finish optimally")
        for index, constraint in run.pf_solved_instance.limit_emission_constraint.items():
            if index[2] == "CO2_covered":
                representation = generate_standard_repn(constraint.body)
                constraints.append({
                    "index": list(index), "body": value(constraint.body),
                    "upper": value(constraint.upper),
                    "variables": [variable.name for variable in representation.linear_vars],
                })
    lp_files = sorted(directory.rglob("model.lp"))
    stages = sorted(int(lp.parent.name[2:]) for lp in lp_files if lp.parent.name.startswith("LP"))
    return {"periods": read_summary(path), "scoped_constraints": constraints,
            "solved_base_years": stages,
            "lp_files": [str(lp.relative_to(directory.parent)) for lp in lp_files]}


def run_example(output: Path) -> dict:
    if metadata.version("temoa") != "4.1.0":
        raise RuntimeError("This example requires temoa==4.1.0")
    # A new directory prevents overwriting any existing data.
    output.mkdir(parents=True, exist_ok=False)
    source = output / "source.sqlite"
    create_source(source)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    cases = {}
    for name in ("reference", "scoped", "wide", "priced", "price_only", "high_price", "myopic"):
        path = output / f"{name}.sqlite"
        shutil.copyfile(source, path)
        configure_case(path, name)
        cases[name] = solve_case(path, output / name, name)
    after = hashlib.sha256(source.read_bytes()).hexdigest()
    if before != after:
        raise RuntimeError("The source fixture changed")
    report = {"temoa_version": metadata.version("temoa"), "highspy_version": metadata.version("highspy"),
              "source_before": before, "source_after": after, "cases": cases}
    (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results"), help="A new output directory")
    arguments = parser.parse_args()
    result = run_example(arguments.output.resolve())
    for label, case in result["cases"].items():
        print(label, json.dumps(case["periods"]))
