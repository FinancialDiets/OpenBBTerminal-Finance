```
usage: expo [--trend {N,A,M}] [--dampen DAMPEN] [--naive] [-d {AAPL}] [-c TARGET_COLUMN] [-n N_DAYS] [-s {N,A,M}] [-p SEASONAL_PERIODS]
            [-w START_WINDOW] [--end S_END_DATE] [--start S_START_DATE] [--residuals] [--forecast-only] [--export-pred-raw] [-h]
            [--export EXPORT]
```

Perform Probabilistic Exponential Smoothing forecast:
https://unit8co.github.io/darts/generated_api/darts.models.forecasting.exponential_smoothing.html

```
optional arguments:
  --trend {N,A,M}       Trend: N: None, A: Additive, M: Multiplicative. (default: A)
  --dampen DAMPEN       Dampening (default: F)
  --naive               Show the naive baseline for a model. (default: False)
  -d {AAPL}, --target-dataset {AAPL}
                        The name of the dataset you want to select (default: None)
  -c TARGET_COLUMN, --target-column TARGET_COLUMN
                        The name of the specific column you want to use (default: close)
  -n N_DAYS, --n-days N_DAYS
                        prediction days. (default: 5)
  -s {N,A,M}, --seasonal {N,A,M}
                        Seasonality: N: None, A: Additive, M: Multiplicative. (default: A)
  -p SEASONAL_PERIODS, --periods SEASONAL_PERIODS
                        Seasonal periods: 4: Quarterly, 7: Daily (default: 7)
  -w START_WINDOW, --window START_WINDOW
                        Start point for rolling training and forecast window. 0.0-1.0 (default: 0.85)
  --end S_END_DATE      The end date (format YYYY-MM-DD) to select for testing (default: None)
  --start S_START_DATE  The start date (format YYYY-MM-DD) to select for testing (default: None)
  --residuals           Show the residuals for the model. (default: False)
  --forecast-only       Do not plot the hisotorical data without forecasts. (default: False)
  --export-pred-raw     Export predictions to a csv file. (default: False)
  -h, --help            show this help message (default: False)
  --export EXPORT       Export figure into png, jpg, pdf, svg (default: )

For more information and examples, use 'about expo' to access the related guide.
```

Example:
```
2022 Jul 23, 10:36 (🦋) /forecast/ $ load GME_20220719_123734.csv -a GME

2022 Jul 23, 10:52 (🦋) /forecast/ $ expo GME
100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 115/115 [00:16<00:00,  6.80it/s]
Exponential smoothing obtains MAPE: 12.88%



       Actual price: $ 146.64
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Datetime            ┃ Prediction ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ 2022-07-19 00:00:00 │ $ 146.35   │
├─────────────────────┼────────────┤
│ 2022-07-20 00:00:00 │ $ 148.63   │
├─────────────────────┼────────────┤
│ 2022-07-21 00:00:00 │ $ 148.86   │
├─────────────────────┼────────────┤
│ 2022-07-22 00:00:00 │ $ 151.76   │
├─────────────────────┼────────────┤
│ 2022-07-25 00:00:00 │ $ 149.74   │
└─────────────────────┴────────────┘
```
![expo](https://user-images.githubusercontent.com/72827203/180615313-e45d6cb3-06a8-45aa-ae4e-505df07e7210.png)
