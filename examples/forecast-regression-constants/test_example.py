"""Check actual model fits, saved forecasts and future feature alignment."""
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from example import run, validate_features


class ForecastExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="forecast example ")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.output = Path(cls.temp.name) / "results"
        cls.report = run(cls.output)

    def test_real_lake_fits_and_thirty_years(self):
        report = self.report["lake"]
        self.assertEqual(report["rows"], 98)
        self.assertTrue(any(w["category"] == "SingularMatrixWarning" for w in report["duplicate"]["warnings"]))
        for name in ("automatic_mean", "explicit_constant"):
            self.assertFalse(report[name]["warnings"])
            self.assertEqual(report[name]["arma"], [1, 1, 0, 0, 1, 0, 0])
        auto = pd.read_csv(self.output / "lake_automatic_mean.csv", parse_dates=["ds"])
        explicit = pd.read_csv(self.output / "lake_explicit_constant.csv", parse_dates=["ds"])
        self.assertEqual(len(auto), 30)
        self.assertEqual(auto.ds.tolist(), pd.date_range("1973-01-01", periods=30, freq="YS").tolist())
        np.testing.assert_allclose(auto.iloc[:, 2:], explicit.iloc[:, 2:], rtol=0, atol=1e-4)
        self.assertAlmostEqual(auto["automatic_mean"].iloc[0], 579.37892, places=3)
        self.assertAlmostEqual(auto["automatic_mean"].iloc[-1], 577.38029, places=3)

    def test_complete_gas_data_and_forecasts(self):
        gas = self.report["gas"]
        self.assertEqual(gas["rows"], 1355)
        self.assertEqual(gas["start"], "1991-02-04")
        self.assertEqual(gas["end"], "2017-01-16")
        self.assertTrue(self.report["inputs_unchanged"])
        for name in ("deterministic", "stochastic"):
            frame = pd.read_csv(self.output / ("gas_" + name + ".csv"), parse_dates=["ds"])
            self.assertEqual(len(frame), 52)
            self.assertEqual(frame.ds.tolist(), pd.date_range("2017-01-23", periods=52, freq="W-MON").tolist())
            self.assertTrue(np.isfinite(frame.iloc[:, 2:].to_numpy()).all())
            self.assertTrue((frame[f"{name}-lo-95"] <= frame[f"{name}-lo-80"]).all())
            self.assertTrue((frame[f"{name}-lo-80"] <= frame[name]).all())
            self.assertTrue((frame[name] <= frame[f"{name}-hi-80"]).all())
            self.assertTrue((frame[f"{name}-hi-80"] <= frame[f"{name}-hi-95"]).all())
            self.assertEqual(gas[name]["ljung_box"]["lag"], 52)
            self.assertTrue(np.isfinite(gas[name]["ljung_box"]["p_value"]))
        self.assertLess(gas["deterministic"]["ljung_box"]["p_value"], .05)

    def test_future_regressors_continue_and_mistakes_are_rejected(self):
        train = pd.read_csv(self.output / "gas_train.csv", parse_dates=["ds"])
        future = pd.read_csv(self.output / "gas_future.csv", parse_dates=["ds"])
        validate_features(train, future, h=52, freq="W-MON", k=7)
        self.assertEqual(future.trend.iloc[0], 1356)
        self.assertEqual(future.trend.iloc[-1], 1407)
        bad = future.copy()
        bad["trend"] = np.arange(1, 53)
        with self.assertRaises(ValueError):
            validate_features(train, bad, h=52, freq="W-MON", k=7)
        bad = future.copy()
        fourier_columns = [c for c in future if c.startswith(("sin", "cos"))]
        bad[fourier_columns] = train.loc[:51, fourier_columns].to_numpy()
        with self.assertRaises(ValueError):
            validate_features(train, bad, h=52, freq="W-MON", k=7)
        with self.assertRaises(ValueError):
            validate_features(train, future[list(reversed(future.columns))], h=52, freq="W-MON", k=7)
        bad = future.copy()
        bad.loc[1, "ds"] = bad.loc[0, "ds"]
        with self.assertRaises(ValueError):
            validate_features(train, bad, h=52, freq="W-MON", k=7)

    def test_existing_destination_is_unchanged(self):
        marker = self.output / "keep.txt"
        marker.write_text("keep")
        with self.assertRaises(FileExistsError):
            run(self.output)
        self.assertEqual(marker.read_text(), "keep")


if __name__ == "__main__":
    unittest.main(verbosity=2)
