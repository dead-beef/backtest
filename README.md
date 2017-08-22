# backtest

## Overview

## Requirements

- [`Python 2`](https://www.python.org/)
- [`TA-Lib`](http://ta-lib.org/)

## Installation

```
python setup.py install
```

## Usage

### Test

```
backtest ...
python -m backtest ...
```

```
usage: backtest [-h] [-p PAIR] [-P AMOUNT AMOUNT] [-b DATETIME]
                [-e DATETIME] [-i TIME] [-v] [-np] [-nP]
                data strategy [strategy ...]

positional arguments:
  data
  strategy

optional arguments:
  -h, --help            show this help message and exit
  -p PAIR, --pair PAIR  primary currency pair
  -P AMOUNT AMOUNT, --portfolio AMOUNT AMOUNT
                        starting portfolio
  -b DATETIME, --begin DATETIME
                        start time (default: data start time)
  -e DATETIME, --end DATETIME
                        end time (default: data end time)
  -i TIME, --interval TIME
                        interval (default: data interval)
  -v, --verbose         log strategy operations
  -np, --no-progress
  -nP, --no-plot
```

### Data

```
backtest-data ...
python -m backtest.data ...
```

```
usage: backtest-data [-h] {plot,get} ...

positional arguments:
  {plot,get}

optional arguments:
  -h, --help  show this help message and exit
```

```
usage: backtest-data plot [-h] [-i] [-d DATASET [DATASET ...]]
                          [-p {high,low,open,close} [{high,low,open,close} ...]]
                          file

positional arguments:
  file

optional arguments:
  -h, --help            show this help message and exit
  -i, --info            print metadata and exit
  -d DATASET [DATASET ...], --dataset DATASET [DATASET ...]
                        select datasets (default: all)
  -p {high,low,open,close} [{high,low,open,close} ...], --price {high,low,open,close} [{high,low,open,close} ...]
                        select prices (default: all)
```

```
usage: backtest-data get [-h] [-b DATETIME] [-e DATETIME] [-i TIME] [-p PAIR]
                         [-s {poloniex}] [-o PATH]

optional arguments:
  -h, --help            show this help message and exit
  -b DATETIME, --begin DATETIME
                        start time (%Y-%m-%d | %Y-%m-%d %H:%M | timestamp)
                        (default: current time - 6 months)
  -e DATETIME, --end DATETIME
                        end time (%Y-%m-%d | %Y-%m-%d %H:%M | timestamp)
                        (default: current time)
  -i TIME, --interval TIME
                        interval (<value><s | m | h | d>) (default: 4h)
  -p PAIR, --pair PAIR  currency pair (default: btc_usd)
  -s {poloniex}, --source {poloniex}
                        data source (default: poloniex)
  -o PATH, --output PATH
                        output file/directory (default:
                        <source>_<pair>_<start>_<end>_<interval>.npz)
```

## Testing

```
python setup.py test
```

```
python -m unittest discover tests
```

## Licenses

* [`backtest`](LICENSE)
