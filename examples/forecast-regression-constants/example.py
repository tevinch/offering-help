"""Fit regression/ARIMA examples with explicit constant and future-feature choices."""
import argparse
from functools import partial
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import urllib.request
import warnings

import numpy as np
import pandas as pd
import rdata
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import acf
from utilsforecast.feature_engineering import fourier, pipeline, trend


SOURCES = {
    "LakeHuron.R": {
        "url": "https://svn.r-project.org/R/trunk/src/library/datasets/data/LakeHuron.R",
        "sha256": "83dd85a9fbd9f84f17477d733495f3c9501ea584a03f6701d222a8da1b24dfd2",
    },
    "us_gasoline.rda": {
        "url": "https://raw.githubusercontent.com/robjhyndman/fpp3/12beccaaf4f2f2d578d6da76d3fe314f689f9c6f/data/us_gasoline.rda",
        "sha256": "b70d98541faed725421c857bff0e3564d5943c6e26b359de24844c47f37057ff",
    },
}


def download_data(directory):
    directory.mkdir()
    for name, source in SOURCES.items():
        request = urllib.request.Request(source["url"], headers={"User-Agent": "Forecast-regression-example"})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise ValueError(f"The published data changed: {name}. Review its source before using it.")
        (directory / name).write_bytes(data)


def load_data(directory):
    # Parse a numeric vector; do not execute the R source.
    text = (directory / "LakeHuron.R").read_text()
    match = re.search(r"ts\(c\((.*?)\), 1875, 1972\)", text, re.S)
    if match is None:
        raise ValueError("Unexpected LakeHuron source structure")
    levels = np.array([float(value.strip()) for value in match[1].split(",")])
    if len(levels) != 98:
        raise ValueError("Expected all 98 annual LakeHuron values")
    lake = pd.DataFrame({"unique_id": "LakeHuron", "ds": pd.date_range("1875-01-01", periods=98, freq="YS"), "y": levels})

    # rdata reads an R data object without evaluating R code. Record its
    # unsupported metadata-class notices separately from model warnings.
    with warnings.catch_warnings(record=True) as notices:
        warnings.simplefilter("always")
        obj = rdata.conversion.convert(rdata.parser.parse_file(directory / "us_gasoline.rda"))
    raw = obj["us_gasoline"]
    if list(raw.columns) != ["Week", "Barrels"] or len(raw) != 1355:
        raise ValueError("Unexpected us_gasoline data structure")
    # The stored yearweek values are Date day counts, not week counts.
    dates = pd.to_datetime(raw.Week.to_numpy(), unit="D", origin="unix")
    expected = pd.date_range("1991-02-04", periods=1355, freq="W-MON")
    if not dates.equals(expected) or dates[-1] != pd.Timestamp("2017-01-16"):
        raise ValueError("Unexpected weekly range or calendar decoding")
    gas = pd.DataFrame({"unique_id": "us_gasoline", "ds": dates, "y": raw.Barrels.to_numpy()})
    if not np.isfinite(lake.y).all() or not np.isfinite(gas.y).all():
        raise ValueError("Missing or nonfinite source values")
    return lake, gas, [str(w.message) for w in notices]


def validate_features(train, future, *, h, freq, k=0, season_length=52):
    """Check one series' time grid, column order and continuous regressors."""
    features = [c for c in train.columns if c not in ("unique_id", "ds", "y")]
    if list(future.columns) != ["unique_id", "ds", *features]:
        raise ValueError("Future columns must match training regressor order and omit y")
    if len(future) != h or train.unique_id.nunique() != 1 or future.unique_id.nunique() != 1:
        raise ValueError("Expected one series and exactly h future rows")
    if train.unique_id.iloc[0] != future.unique_id.iloc[0]:
        raise ValueError("Training/future series IDs differ")
    if not pd.DatetimeIndex(train.ds).equals(pd.date_range(train.ds.iloc[0], periods=len(train), freq=freq)):
        raise ValueError("Training dates must be complete, ordered and regular")
    expected_dates = pd.date_range(train.ds.iloc[-1], periods=h + 1, freq=freq)[1:]
    if not pd.DatetimeIndex(future.ds).equals(expected_dates):
        raise ValueError("Future dates must continue the training grid")
    if not np.isfinite(train[["y", *features]].to_numpy()).all() or not np.isfinite(future[features].to_numpy()).all():
        raise ValueError("Nonfinite response or regressor")
    n = len(train)
    if "trend" in features:
        if not np.array_equal(train.trend, np.arange(1, n + 1)) or not np.array_equal(future.trend, np.arange(n + 1, n + h + 1)):
            raise ValueError("Trend must continue from n+1; do not restart it at 1")
    # Independent trigonometric check. utilsforecast's terms use float32,
    # so allow its rounding while rejecting a restarted seasonal phase.
    for frame, times in ((train, np.arange(1, n + 1)), (future, np.arange(n + 1, n + h + 1))):
        for order in range(1, k + 1):
            angle = 2 * np.pi * order * times / season_length
            for prefix, expected in (("sin", np.sin(angle)), ("cos", np.cos(angle))):
                if not np.allclose(frame[f"{prefix}{order}_{season_length}"], expected, atol=2e-4, rtol=0):
                    raise ValueError("Fourier terms must keep the training time origin")


def fit_and_predict(train, future, *, alias, freq, diagnostic_lag, **kwargs):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sf = StatsForecast(models=[AutoARIMA(alias=alias, **kwargs)], freq=freq).fit(train)
        forecasts = sf.predict(h=len(future), X_df=future, level=[80, 95])
    if not np.isfinite(forecasts.iloc[:, 2:].to_numpy()).all():
        raise ValueError(f"Nonfinite forecast or interval from {alias}")
    if forecasts[["unique_id", "ds"]].to_dict("list") != future[["unique_id", "ds"]].to_dict("list"):
        raise ValueError("Forecast keys/order differ from future features")
    model = sf.fitted_[0, 0].model_
    arma = [int(x) for x in model["arma"]]  # p, q, P, Q, m, d, D
    burn = arma[5] + arma[6] * arma[4]
    residuals = np.asarray(model["residuals"])[burn:]
    residuals = residuals[np.isfinite(residuals)]
    model_df = sum(arma[:4])
    lb = acorr_ljungbox(residuals, lags=[diagnostic_lag], model_df=model_df, return_df=True).iloc[0]
    correlation = acf(residuals, nlags=diagnostic_lag, fft=True)
    regressors = [c for c in train.columns if c not in ("unique_id", "ds", "y")]
    details = {
        "settings": kwargs,
        "arma": arma,
        "coefficients": {key: float(value) for key, value in model["coef"].items()},
        "regressor_names": {f"ex_{i}": name for i, name in enumerate(regressors, 1)},
        "aicc": float(model["aicc"]),
        "warnings": [{"category": type(w.message).__name__, "message": str(w.message)} for w in caught],
        "ljung_box": {"lag": diagnostic_lag, "model_df": model_df, "burn_in": burn, "statistic": float(lb.lb_stat), "p_value": float(lb.lb_pvalue)},
        "residual_acf": {"lag_1": float(correlation[1]), f"lag_{diagnostic_lag}": float(correlation[diagnostic_lag])},
        "forecast_min": float(forecasts[alias].min()),
        "forecast_max": float(forecasts[alias].max()),
        "negative_point_forecasts": int((forecasts[alias] < 0).sum()),
    }
    return forecasts, details


def run(output):
    output = Path(output)
    output.mkdir()  # Refuse to overwrite an earlier result.
    download_data(output / "source-data")
    lake, gas, reader_notices = load_data(output / "source-data")
    originals = [frame.copy(deep=True) for frame in (lake, gas)]
    report = {"versions": {name: version(name) for name in ("statsforecast", "utilsforecast", "statsmodels", "numpy", "pandas", "scipy", "rdata")}, "sources": SOURCES, "data_reader_notices": reader_notices}

    train, future = trend(lake, freq="YS", h=30)
    validate_features(train, future, h=30, freq="YS")
    lake_report = {"rows": len(lake)}
    outputs = {}
    cases = [
        ("duplicate", True, {}),
        ("automatic_mean", False, {"d": 0, "seasonal": False}),
        ("explicit_constant", True, {"d": 0, "seasonal": False, "allowmean": False, "allowdrift": False}),
    ]
    for alias, explicit, options in cases:
        fit_frame, predict_frame = train.copy(), future.copy()
        if explicit:
            fit_frame["intercept"] = 1.0
            predict_frame["intercept"] = 1.0
        forecasts, details = fit_and_predict(fit_frame, predict_frame, alias=alias, freq="YS", diagnostic_lag=10, **options)
        forecasts.to_csv(output / f"lake_{alias}.csv", index=False)
        outputs[alias] = forecasts
        lake_report[alias] = details
    lake_report["max_difference_auto_vs_explicit"] = float(np.max(np.abs(outputs["automatic_mean"].iloc[:, 2:].to_numpy() - outputs["explicit_constant"].iloc[:, 2:].to_numpy())))
    train.to_csv(output / "lake_train.csv", index=False)
    future.to_csv(output / "lake_future.csv", index=False)
    report["lake"] = lake_report

    train, future = pipeline(gas, [trend, partial(fourier, season_length=52, k=7)], freq="W-MON", h=52)
    validate_features(train, future, h=52, freq="W-MON", k=7)
    train.to_csv(output / "gas_train.csv", index=False)
    future.to_csv(output / "gas_future.csv", index=False)
    gas_report = {"rows": len(gas), "start": str(gas.ds.iloc[0].date()), "end": str(gas.ds.iloc[-1].date()), "k": 7, "season_length": 52}
    fc, details = fit_and_predict(train, future, alias="deterministic", freq="W-MON", diagnostic_lag=52, d=0, seasonal=False, allowdrift=False)
    fc.to_csv(output / "gas_deterministic.csv", index=False)
    gas_report["deterministic"] = details

    # A different model: ARIMA handles d=1 internally. Do not also difference
    # y manually or add a trend column that can duplicate the allowed drift.
    stoch_train, stoch_future = train.drop(columns="trend"), future.drop(columns="trend")
    validate_features(stoch_train, stoch_future, h=52, freq="W-MON", k=7)
    fc, details = fit_and_predict(stoch_train, stoch_future, alias="stochastic", freq="W-MON", diagnostic_lag=52, d=1, seasonal=False, allowdrift=True)
    fc.to_csv(output / "gas_stochastic.csv", index=False)
    gas_report["stochastic"] = details
    report["gas"] = gas_report
    report["inputs_unchanged"] = all(before.equals(after) for before, after in zip(originals, (lake, gas)))
    if not report["inputs_unchanged"]:
        raise ValueError("Input values changed during fitting")
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("results"), help="New directory for data, forecasts, features and diagnostics")
    args = parser.parse_args()
    result = run(args.output)
    print("Saved all forecasts, future features and diagnostics to", args.output)
    print("LakeHuron: maximum automatic-mean versus explicit-constant difference:", result["lake"]["max_difference_auto_vs_explicit"])
    for name in ("deterministic", "stochastic"):
        model = result["gas"][name]
        print(f"Gasoline {name}: order tuple={model['arma']}; lag-52 Ljung-Box p={model['ljung_box']['p_value']:.6g}")
