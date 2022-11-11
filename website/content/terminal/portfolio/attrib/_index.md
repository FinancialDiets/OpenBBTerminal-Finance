```
usage: attrib [-p TIME PERIOD [TIME PERIOD ...]] [-t] [-r] [-h]
```

Display attributions of sector performance in terms of the S&P 500 benchmark (SPY), and the user's portfolio. Graph visualisation and tabular values available.

Default output is the graph visualisation of relative sector attribution, which gives attribution as a percentage. 

```
optional arguments:
  -p TIME PERIOD [TIME PERIOD ...]
                        Set the time period for the portfolio. (default: all)
  -t, --type            Allows user to choose between relative or absolute. Relative gives as percentage and absolute gives raw values. (default: relative)
  -r, --raw             Allows user to also display tabular format of data (default: False)
  -h, --help            Show this help message (default: False)
```
Example:


Filtering to a specific time period is executed via the -p argument.

```
2022 Nov 03, 23:37 (🦋) /portfolio/ $ attrib -p 3m
```

<img width="853" alt="Screen Shot 2022-11-04 at 14 38 20" src="https://user-images.githubusercontent.com/74476622/199880234-75e09a47-e44a-486a-a668-14f69e23aeb3.png">

If I would call `attrib` (or `attrib --type relative`) I would get the graph of the relative performance and nothing else.

```
2022 Nov 03, 23:31 (🦋) /portfolio/ $ attrib
```

<img width="774" alt="Screen Shot 2022-11-04 at 14 32 10" src="https://user-images.githubusercontent.com/74476622/199879420-386bc9a9-8087-429f-b142-3e11f4dd8844.png">

If I would call `attrib --type absolute` I would get the graph of the absolute performance and nothing else.

```
2022 Nov 03, 23:32 (🦋) /portfolio/ $ attrib --type absolute
```

<img width="777" alt="Screen Shot 2022-11-04 at 14 32 48" src="https://user-images.githubusercontent.com/74476622/199879501-8dcdb3ff-8399-48e1-ad2c-66a44b4a99b4.png">

If I would call `attrib --raw` I would get the graph of the relative performance (see above at attrib command for visual) and the table of relative performance.

```
2022 Nov 07, 04:58 (🦋) /portfolio/ $ attrib --raw

                                              Contributions as % of PF: Portfolio vs. Benchmark Attribution Categorisation all                                               
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                             ┃ S&P500 [%] ┃ Portfolio [%] ┃ Excess Attribution ┃ Attribution Ratio ┃ Attribution Direction [+/-] ┃ Attribution Sensitivity ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ S&P 500 Consumer Discretionary (Sector)     │ 12.83      │ 34.71         │ 21.88              │ 2.71              │ Correlated (+)              │ High                    │
├─────────────────────────────────────────────┼────────────┼───────────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Consumer Staples (Sector)           │ 5.62       │ 0.00          │ -5.62              │ 0.00              │ Correlated (+)              │ Low                     │
├─────────────────────────────────────────────┼────────────┼───────────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Energy (Sector)                     │ 3.03       │ 0.00          │ -3.03              │ 0.00              │ Correlated (+)              │ Low                     │
├─────────────────────────────────────────────┼────────────┼───────────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Financials (Sector)                 │ 11.71      │ 0.00          │ -11.71             │ 0.00              │ Correlated (+)              │ Low                     │
├─────────────────────────────────────────────┼────────────┼───────────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Health Care (Sector)                │ 17.28      │ 4.96          │ -12.32             │ 0.29              │ Correlated (+)              │ Low                     │
├─────────────────────────────────────────────┼────────────┼───────────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Industrials (Sector)                │ 7.43       │ 0.00          │ -7.43              │ 0.00              │ Correlated (+)              │ Low                     │
├─────────────────────────────────────────────┼────────────┼───────────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Information Technology (Sector)     │ 33.40      │ 58.77         │ 25.37              │ 1.76              │ Correlated (+)              │ High                    │
├─────────────────────────────────────────────┼────────────┼───────────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Materials (Sector)                  │ 1.77       │ 0.00          │ -1.77              │ 0.00              │ Correlated (+)              │ Low                     │
├─────────────────────────────────────────────┼────────────┼───────────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Real Estate (Sector)                │ 1.95       │ 0.00          │ -1.95              │ 0.00              │ Correlated (+)              │ Low                     │
├─────────────────────────────────────────────┼────────────┼───────────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Telecommunication Services (Sector) │ 3.28       │ 1.56          │ -1.72              │ 0.47              │ Correlated (+)              │ Low                     │
├─────────────────────────────────────────────┼────────────┼───────────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Utilities (Sector)                  │ 1.70       │ 0.00          │ -1.70              │ 0.00              │ Correlated (+)              │ Low                     │
└─────────────────────────────────────────────┴────────────┴───────────────┴────────────────────┴───────────────────┴─────────────────────────────┴─────────────────────────┘
```

If I would call `attrib --type absolute --raw` I would get the graph of the absolute performance (see above at attrib --type absolute for visual) and the table of absolute performance.

```
2022 Nov 07, 04:59 (🦋) /portfolio/ $ attrib --type absolute  --raw

                                   Raw contributions (Return x PF Weight): Portfolio vs. Benchmark Attribution Categorisation all                                    
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃                                             ┃ S&P500 ┃ Portfolio ┃ Excess Attribution ┃ Attribution Ratio ┃ Attribution Direction [+/-] ┃ Attribution Sensitivity ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ S&P 500 Consumer Discretionary (Sector)     │ 0.18   │ 1.07      │ 0.89               │ 5.89              │ Correlated (+)              │ High                    │
├─────────────────────────────────────────────┼────────┼───────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Consumer Staples (Sector)           │ 0.08   │ 0.00      │ -0.08              │ 0.00              │ Correlated (+)              │ Low                     │
├─────────────────────────────────────────────┼────────┼───────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Energy (Sector)                     │ 0.04   │ 0.00      │ -0.04              │ 0.00              │ Correlated (+)              │ Low                     │
├─────────────────────────────────────────────┼────────┼───────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Financials (Sector)                 │ 0.17   │ 0.00      │ -0.17              │ 0.00              │ Correlated (+)              │ Low                     │
├─────────────────────────────────────────────┼────────┼───────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Health Care (Sector)                │ 0.24   │ 0.15      │ -0.09              │ 0.62              │ Correlated (+)              │ Low                     │
├─────────────────────────────────────────────┼────────┼───────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Industrials (Sector)                │ 0.11   │ 0.00      │ -0.11              │ 0.00              │ Correlated (+)              │ Low                     │
├─────────────────────────────────────────────┼────────┼───────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Information Technology (Sector)     │ 0.47   │ 1.81      │ 1.34               │ 3.83              │ Correlated (+)              │ High                    │
├─────────────────────────────────────────────┼────────┼───────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Materials (Sector)                  │ 0.03   │ 0.00      │ -0.03              │ 0.00              │ Correlated (+)              │ Low                     │
├─────────────────────────────────────────────┼────────┼───────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Real Estate (Sector)                │ 0.03   │ 0.00      │ -0.03              │ 0.00              │ Correlated (+)              │ Low                     │
├─────────────────────────────────────────────┼────────┼───────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Telecommunication Services (Sector) │ 0.05   │ 0.05      │ 0.00               │ 1.03              │ Correlated (+)              │ Normal                  │
├─────────────────────────────────────────────┼────────┼───────────┼────────────────────┼───────────────────┼─────────────────────────────┼─────────────────────────┤
│ S&P 500 Utilities (Sector)                  │ 0.02   │ 0.00      │ -0.02              │ 0.00              │ Correlated (+)              │ Low                     │
└─────────────────────────────────────────────┴────────┴───────────┴────────────────────┴───────────────────┴─────────────────────────────┴─────────────────────────┘
```