```
usage: linregr [--past-covariates PAST_COVARIATES] [--all-past-covariates] [--naive] [-d {AAPL}] [-c TARGET_COLUMN]
                [-n N_DAYS] [-t TRAIN_SPLIT] [-o OUTPUT_CHUNK_LENGTH] [--end S_END_DATE][--start S_START_DATE]
                [--lags LAGS] [--residuals] [--forecast-only] [--explainability-raw] [--export-pred-raw] [-h]
                [--export EXPORT]
```

Perform a linear regression forecast:
https://unit8co.github.io/darts/generated_api/darts.models.forecasting.linear_regression_model.html

```
optional arguments:
  --past-covariates PAST_COVARIATES
                        Past covariates(columns/features) in same dataset. Comma separated. (default: None)
  --all-past-covariates
                        Adds all rows as past covariates except for date and the target column. (default: False)
  --naive               Show the naive baseline for a model. (default: False)
  -d {AAPL}, --target-dataset {AAPL}
                        The name of the dataset you want to select (default: None)
  -c TARGET_COLUMN, --target-column TARGET_COLUMN
                        The name of the specific column you want to use (default: close)
  -n N_DAYS, --n-days N_DAYS
                        prediction days. (default: 5)
  -t TRAIN_SPLIT, --train-split TRAIN_SPLIT
                        Start point for rolling training and forecast window. 0.0-1.0 (default: 0.85)
  -o OUTPUT_CHUNK_LENGTH, --output-chunk-length OUTPUT_CHUNK_LENGTH
                        The length of the forecast of the model. (default: 5)
  --end S_END_DATE      The end date (format YYYY-MM-DD) to select for testing (default: None)
  --start S_START_DATE  The start date (format YYYY-MM-DD) to select for testing (default: None)
  --lags LAGS           Lagged target values used to predict the next time step. (default: 14)
  --residuals           Show the residuals for the model. (default: False)
  --forecast-only       Do not plot the hisotorical data without forecasts. (default: False)
  --explainability-raw  Prints out a raw dataframe showing explainability results. (default: False)
  --export-pred-raw     Export predictions to a csv file. (default: False)
  -h, --help            show this help message (default: False)
  --export EXPORT       Export figure into png, jpg, pdf, svg (default: )

For more information and examples, use 'about linregr' to access the related guide.
```

Example:
```
2022 Jul 23, 10:36 (🦋) /forecast/ $ load GME_20220719_123734.csv -a GME

2022 Jul 23, 11:03 (🦋) /forecast/ $ linregr GME
100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 115/115 [00:07<00:00, 15.10it/s]
Logistic Regression model obtains MAPE: 10.85%



       Actual price: $ 146.64
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Datetime            ┃ Prediction ┃
┡━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ 2022-07-19 00:00:00 │ $ 144.41   │
├─────────────────────┼────────────┤
│ 2022-07-20 00:00:00 │ $ 142.69   │
├─────────────────────┼────────────┤
│ 2022-07-21 00:00:00 │ $ 140.94   │
├─────────────────────┼────────────┤
│ 2022-07-22 00:00:00 │ $ 139.89   │
├─────────────────────┼────────────┤
│ 2022-07-25 00:00:00 │ $ 136.04   │
└─────────────────────┴────────────┘
```
![linregr](https://user-images.githubusercontent.com/72827203/180615335-26395da8-3848-40f4-a68b-d2c14475db95.png)
