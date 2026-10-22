# Constants and continuous regressors in AutoARIMA

A runnable companion to [OTexts discussion 174](https://github.com/orgs/OTexts/discussions/174): fit the LakeHuron trend with ARMA errors, compare two ways of specifying its intercept, and construct consistent future trend/Fourier features for the gasoline example.

## Which constant belongs in the model?

With `d=0` and no seasonal differencing, a regression with stationary ARMA errors can be written as `y[t] = intercept + slope*t + error[t]`. Include one constant if that is the intended specification.

In StatsForecast 2.1.1, `allowmean=True` lets AutoARIMA consider a nonzero mean; it does **not** force the selected model to include one. `allowdrift=True` similarly allows drift when total differencing is one. Both defaults changed to `True` in [StatsForecast 2.0.0](https://github.com/Nixtla/statsforecast/releases/tag/v2.0.0).

For exercise 1, use the existing `df` with `unique_id`, `ds`, and `y` columns:

```python
from statsforecast import StatsForecast
from statsforecast.models import AutoARIMA
from utilsforecast.feature_engineering import trend

train, future = trend(df, freq="YS", h=30)
sf = StatsForecast(
    models=[AutoARIMA(d=0, seasonal=False)], freq="YS"
).fit(train)
forecast = sf.predict(h=30, X_df=future, level=[80, 95])
```

There is no extra column of ones here. The chosen LakeHuron model includes an intercept. If you explicitly want the constant in the regressor matrix, add it to **both** frames and disable the automatic mean candidates:

```python
train["intercept"] = 1.0
future["intercept"] = 1.0
model = AutoARIMA(d=0, seasonal=False, allowmean=False, allowdrift=False)
sf = StatsForecast(models=[model], freq="YS").fit(train)
forecast = sf.predict(h=30, X_df=future, level=[80, 95])
```

Adding a manual constant while also allowing automatic mean candidates can create redundant columns **during the search**. On the data below, the original setup emits `SingularMatrixWarning`, but its final selected model represents the constant as `ex_2` and has no additional `intercept` coefficient. The warning does not imply that the final selected model necessarily contains both. The example records all warnings and the selected coefficients instead of disabling warnings globally.

For `d=1`, differencing removes a constant column. A linear time regressor differences to a constant; combining it with an automatic drift can duplicate the same role. The alternative gasoline model below supplies Fourier terms only and lets AutoARIMA consider drift. It passes the original response with `d=1`; it does not manually difference the response a second time. This is a different model from a deterministic trend with ARMA errors. The [stable implementation](https://github.com/Nixtla/statsforecast/blob/v2.1.1/python/statsforecast/arima.py#L2067) restricts mean/drift candidates according to the differencing orders.

## Run both datasets

Tested with Python 3.12 and the pinned dependencies:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python example.py --output results
python test_example.py
```

The output directory must be new. The program downloads two small, hash-checked primary-source data files, then writes:

- `lake_automatic_mean.csv`, `lake_explicit_constant.csv`, and `lake_duplicate.csv`: all 30 forecasts and 80/95% intervals, from 1973 through 2002.
- `gas_deterministic.csv` and `gas_stochastic.csv`: all 52 forecasts and intervals.
- `lake_train.csv`, `lake_future.csv`, `gas_train.csv`, and `gas_future.csv`: the actual response and regressor frames.
- `report.json`: versions, data URLs/hashes, selected orders, coefficient-to-feature mappings, captured warnings and residual diagnostics.

The data sources are [R's LakeHuron series](https://svn.r-project.org/R/trunk/src/library/datasets/data/LakeHuron.R), containing 98 annual levels from 1875–1972, and the book author's [fpp3 us_gasoline data](https://github.com/robjhyndman/fpp3/blob/12beccaaf4f2f2d578d6da76d3fe314f689f9c6f/data/us_gasoline.rda), containing 1,355 weeks from 1991 W06 through 2017 W03. The latter's values are million barrels per day. The stored `yearweek` dates are decoded to Mondays and checked against the complete date grid. R source is parsed as numeric data, never evaluated; R metadata conversion notices are recorded separately from model warnings.

These are the named series from the original R sources. The Python edition's CSV endpoints were unavailable during verification, so no equality claim is made about those CSV files. The datasets are downloaded from their original sources, not bundled with this example.

On this LakeHuron series, the two clear constant specifications select ARMA(1,1) errors with coefficients approximately `ar1=0.653`, `ma1=0.357`, constant `580.082`, and slope `-0.021`. Both run without singular warnings; their forecasts and interval bounds differ by less than `0.0001`. The first and thirtieth point forecasts are about `579.379` and `577.380`. That downward extrapolation is the fitted model's implication, not evidence that a 30-year linear trend is realistic.

## Gasoline: preserve the time origin and inspect the model

Generate the training and future features together:

```python
from functools import partial
from utilsforecast.feature_engineering import fourier, pipeline, trend

train, future = pipeline(
    df,
    [trend, partial(fourier, season_length=52, k=7)],
    freq="W-MON", h=52,
)
```

For this 1,355-row dataset, training trend is `1..1355` and future trend is `1356..1407`. Fourier terms use the same continuing index. The ID, future dates and regressor column order must also agree. `validate_features` checks those conditions before fitting and rejects a future trend restarted at one.

A large time index alone does not imply negative forecasts. With an intercept, translating `t` by a fixed `c` gives the equivalent expression `a + b*t = (a + b*c) + b*(t-c)`, provided the **same** transformation is used for training and future values. Numerical optimization can still introduce small differences. The complete original gasoline code is not available in the discussion, so this example does not establish the cause of its negative predictions.

The two illustrative fits keep the question's `K=7` and period 52:

| Fit on the full series | Selected errors | Point forecast range | Lag-52 Ljung–Box p-value |
|---|---|---|---|
| Trend + Fourier, `d=0` | ARMA(5,0) | 8.53–9.48 | about `1.7e-9` |
| Fourier, `d=1`, drift allowed | ARIMA(0,1,1), drift selected | 8.67–9.41 | about `0.081` |

Both produce finite forecasts in this run, but the deterministic fit still has substantial residual autocorrelation. Its positive forecasts do not make it a satisfactory final model. The second result is a candidate for further checking, not proof of white noise or forecast accuracy. These diagnostics use lag 52, `model_df=p+q+P+Q`, and omit the first `d+D*m` residuals; a p-value computed with different settings need not match. The report also records residual autocorrelations.

This checks constant handling and the complete forecast call. It does not select `K` empirically or finish every model-assessment step in exercise 5. Inspect residual plots and out-of-sample performance and compare models before choosing a final specification, as the [chapter's exercise](https://otexts.com/fpppy/10-dynamic-regression.html#sec-dynamic-exercises) requests. No predictions are clipped or otherwise adjusted to make them positive.

The tests perform real fits, reproduce the original singular warning, compare both 30-year forecasts, check all 52 weekly outputs and interval ordering, verify unchanged inputs, and reject restarted/shuffled/duplicated future features. They do not substitute mock model results.

## Optional coffee

This example is free. If it saved you time and you would like to buy me a coffee, contributions are entirely optional:

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
