from __future__ import print_function

from time import time, ctime
from urllib2 import urlopen
import os.path
import json

import numpy as np

from backtest.data import DataSource
from backtest.util import parse_date, parse_time


def create_argument_parser(parser):
    default_end = int(time())
    default_start = default_end - 15552000
    date_format = '%%Y-%%m-%%d | %%Y-%%m-%%d %%H:%%M | timestamp'

    parser.add_argument(
        '-b', '--begin', metavar='DATETIME',
        help='start time ({0}) (default: {1})'.format(
            date_format, ctime(default_start)
        ),
        type=parse_date, default=default_start
    )
    parser.add_argument(
        '-e', '--end', metavar='DATETIME',
        help='end time ({0}) (default: {1})'.format(
            date_format, ctime(default_end)
        ),
        type=parse_date, default=default_end
    )
    parser.add_argument(
        '-i', '--interval', metavar='TIME',
        help='interval (<value><s | m | h | d>) (default: 4h)',
        type=parse_time, default=14400
    )
    parser.add_argument(
        '-p', '--pair',
        help='currency pair (default: %(default)s)',
        default='btc_usd'
    )
    parser.add_argument(
        '-s', '--source',
        help='data source (default: %(default)s)',
        choices=['poloniex'], default='poloniex'
    )
    parser.add_argument(
        '-o', '--output', metavar='PATH',
        help='output file/directory ' \
             '(default: <source>_<pair>_<start>_<end>_<interval>.npz)',
        default=None
    )
    return parser


def main(args):
    args.pair = args.pair.lower()

    if args.output is None or os.path.isdir(args.output):
        fname = '{0}_{1}_{2}_{3}_{4}.npz'.format(args.source, args.pair.lower(),
                                                 args.begin, args.end,
                                                 args.interval)
        if args.output is None:
            args.output = fname
        else:
            args.output = os.path.join(args.output, fname)

    if args.source == 'poloniex':
        url = 'https://poloniex.com/public?command=returnChartData' \
              '&currencyPair={0}&start={1}&end={2}&period={3}' \
                  .format(args.pair.upper(), args.begin,
                          args.end, args.interval)

        if args.pair == 'usdt_btc':
            args.pair = 'btc_usd'

        print('GET', url)

        data = json.load(urlopen(url))

        if 'error' in data:
            print('Error:', data['error'])
            exit(1)
        if not isinstance(data, list):
            print('Error: invalid data:', data)
            exit(1)
        if not data:
            print('Error: no data')
            exit(1)

        start = data[0]['date']

        print('start  ', ctime(start))
        print('end    ', ctime(data[-1]['date']))
        print('length ', len(data))

        info = np.array([start, args.interval], dtype=int)
        dataset = np.empty(
            (len(data), len(DataSource.CANDLE_VALUES)),
            dtype=float
        )
        save = {
            'info': info,
            args.pair: dataset
        }

        for i, candle in enumerate(data):
            for attr in DataSource.CANDLE_VALUES:
                dataset[i, DataSource.CANDLE[attr]] = candle[attr]

        print('save   ', args.output)

        np.savez_compressed(args.output, **save)
