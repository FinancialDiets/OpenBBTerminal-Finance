```
usage: baas [-c COIN] [-l N] [-vs VS] [-d DAYS]
            [-s {date,baseCurrency,quoteCurrency,dailySpread,averageBidPrice,averageAskPrice}]
            [--reverse] [-h] [--export {csv,json,xlsx}]
```

Display average bid, ask prices, spread for given crypto pair for chosen time
period [Source: https://graphql.bitquery.io/]

```
optional arguments:
  -c COIN, --coin COIN  ERC20 token symbol or address. (default: None)
  -l N, --limit N     display N number records (default: 10)
  -vs VS, --vs VS       Quote currency (default: USDT)
  -d DAYS, --days DAYS  Number of days to display data for. (default: 10)
  -s {date,baseCurrency,quoteCurrency,dailySpread,averageBidPrice,averageAskPrice}, --sort {date,baseCurrency,quoteCurrency,dailySpread,averageBidPrice,averageAskPrice}
                        Sort by given column. (default: date)
  -r, --reverse         Data is sorted in descending order by default.
                        Reverse flag will sort it in an ascending way.
                        Only works when raw data is displayed. (default: False)
  -h, --help            show this help message (default: False)
  --export {csv,json,xlsx}
                        Export raw data into csv, json, xlsx (default: )
```
