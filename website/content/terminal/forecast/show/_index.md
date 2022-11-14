```
usage: show [-n {}] [-s SORTCOL [SORTCOL ...]] [-a]
      [--limit-col LIMIT_COL] [-h] [--export EXPORT] [-l LIMIT]
```

Show a portion of the loaded dataset

```
optional arguments:
  -n {}, --name {AAPL,MSFT,TSLA}
                        The name of the database you want to show data for (default: None)
  -s SORTBY [SORTBY ...], --sortby SORTBY [SORTBY ...]
                        Sort based on a column in the DataFrame (default: )
  -r, --reverse         Data is sorted in descending order by default.
                        Reverse flag will sort it in an ascending way.
                        Only works when raw data is show this help message (default: False)
  --limit-col LIMIT_COL
                        Set the number of columns to display when showing the dataset (default: 10)
  -h, --help            show this help message (default: False)
  --export EXPORT       Export raw data into csv, json, xlsx (default: )
  -l LIMIT, --limit LIMIT
                        Number of entries to show in data. (default: 10)

For more information and examples, use 'about show' to access the related guide.
```

Example:
```
(🦋) /forecast/ $ load aapl.csv

(🦋) /forecast/ $ show aapl

aapl dataset has shape (row, column): (759, 7)

                  Dataset aapl | Showing 10 of 759 rows
┏━━━┳━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┓
┃   ┃ date       ┃ open  ┃ high  ┃ low   ┃ close ┃ adj_close ┃ volume    ┃
┡━━━╇━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━┩
│ 0 │ 2019-06-10 │ 47.95 │ 48.84 │ 47.90 │ 48.15 │ 46.99     │ 104883600 │
├───┼────────────┼───────┼───────┼───────┼───────┼───────────┼───────────┤
│ 1 │ 2019-06-11 │ 48.72 │ 49.00 │ 48.40 │ 48.70 │ 47.53     │ 107731600 │
├───┼────────────┼───────┼───────┼───────┼───────┼───────────┼───────────┤
│ 2 │ 2019-06-12 │ 48.49 │ 48.99 │ 48.35 │ 48.55 │ 47.38     │ 73012800  │
├───┼────────────┼───────┼───────┼───────┼───────┼───────────┼───────────┤
│ 3 │ 2019-06-13 │ 48.67 │ 49.20 │ 48.40 │ 48.54 │ 47.37     │ 86698400  │
├───┼────────────┼───────┼───────┼───────┼───────┼───────────┼───────────┤
│ 4 │ 2019-06-14 │ 47.89 │ 48.40 │ 47.58 │ 48.19 │ 47.03     │ 75046000  │
├───┼────────────┼───────┼───────┼───────┼───────┼───────────┼───────────┤
│ 5 │ 2019-06-17 │ 48.22 │ 48.74 │ 48.04 │ 48.47 │ 47.31     │ 58676400  │
├───┼────────────┼───────┼───────┼───────┼───────┼───────────┼───────────┤
│ 6 │ 2019-06-18 │ 49.01 │ 50.07 │ 48.80 │ 49.61 │ 48.42     │ 106204000 │
├───┼────────────┼───────┼───────┼───────┼───────┼───────────┼───────────┤
│ 7 │ 2019-06-19 │ 49.92 │ 49.97 │ 49.33 │ 49.47 │ 48.28     │ 84496800  │
├───┼────────────┼───────┼───────┼───────┼───────┼───────────┼───────────┤
│ 8 │ 2019-06-20 │ 50.09 │ 50.15 │ 49.51 │ 49.87 │ 48.67     │ 86056000  │
├───┼────────────┼───────┼───────┼───────┼───────┼───────────┼───────────┤
│ 9 │ 2019-06-21 │ 49.70 │ 50.21 │ 49.54 │ 49.69 │ 48.50     │ 191202400 │
└───┴────────────┴───────┴───────┴───────┴───────┴───────────┴───────────┘

```
