`usage: rossidx [-s SORTBY [SORTBY {GitHub,Company,Country,City,Founded,Raised [$M],Stars,Forks,Stars AGR [%],Forks AGR [%]}]] [--reverse] [--chart] [--growth] [-ct {stars,forks}] [-h] [--export EXPORT] [-l LIMIT]`

Display list of startups from ross index [Source: https://runacap.com/]
Use --chart to display chart and -t {stars,forks} to set chart type

```
optional arguments:
  -s SORTBY [SORTBY ...], --sortby SORTBY [SORTBY {GitHub,Company,Country,City,Founded,Raised [$M],Stars,Forks,Stars AGR [%],Forks AGR [%]}]
                        Sort startups by column (default: Stars AGR [%])
  -r, --reverse         Data is sorted in descending order by default. Reverse
                        flag will sort it in an ascending way. Only works when raw
                        data is displayed. (default: False)
  -c, --chart           Flag to show chart (default: False)
  -g, --growth          Flag to show growth chart (default: False)
  -t {stars,forks}, --chart-type {stars,forks}
                        Chart type: {stars, forks} (default: stars)
  -h, --help            show this help message (default: False)
  --export EXPORT       Export raw data into csv, json, xlsx (default: )
  -l LIMIT, --limit LIMIT
                        Number of entries to show in data. (default: 10)
```
