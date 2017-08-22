from __future__ import print_function, division

from argparse import ArgumentParser
from sys import exc_info
from time import ctime
from datetime import datetime
from decimal import Decimal
from traceback import print_tb
from random import randint

from tqdm import trange

from .api import TradewaveAPI
from .data import FileDataSource
from .util import TqdmFileWrapper, parse_date, parse_time


def create_argument_parser():
    parser = ArgumentParser()
    parser.add_argument('-p', '--pair', default=None,
                        help='primary currency pair')
    parser.add_argument('-P', '--portfolio', metavar='AMOUNT',
                        help='starting portfolio',
                        type=float, nargs=2, default=(1.0, 0.0))
    parser.add_argument('-b', '--begin', type=parse_date, default=None,
                        metavar='DATETIME',
                        help='start time (default: data start time)')
    parser.add_argument('-e', '--end', type=parse_date, default=None,
                        metavar='DATETIME',
                        help='end time (default: data end time)')
    parser.add_argument('-i', '--interval', type=parse_time, default=None,
                        metavar='TIME',
                        help='interval (default: data interval)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='log strategy operations')
    parser.add_argument('-np', '--no-progress', action='store_true')
    parser.add_argument('-nP', '--no-plot', action='store_true')
    parser.add_argument('data')
    parser.add_argument('strategy', nargs='+')
    return parser

def tick(strategies, i, exit_on_error):
    for strategy in strategies:
        try:
            strategy.tick(i)
        except Exception: # pylint: disable=broad-except
            err = exc_info()
            print('[ERROR] [{0}] tick {1}: {2}'
                  .format(strategy, i, repr(err[1])))
            print_tb(err[2])
            if exit_on_error:
                exit(1)
            strategy.stop()

def run(strategies, ticks, progress=True, exit_on_error=True):
    for strategy in strategies:
        try:
            strategy.start()
        except Exception: # pylint: disable=broad-except
            err = exc_info()
            print('[ERROR] [{0}] start: {1}'
                  .format(strategy, repr(err[1])))
            print_tb(err[2])
            if exit_on_error:
                exit(1)

    if progress:
        with TqdmFileWrapper.stdout() as stdout:
            for i in trange(ticks, leave=False, dynamic_ncols=True, file=stdout):
                tick(strategies, i, exit_on_error)
    else:
        for i in xrange(ticks):
            tick(strategies, i, exit_on_error)

    for strategy in strategies:
        try:
            strategy.stop()
        except Exception: # pylint: disable=broad-except
            err = exc_info()
            print('[ERROR] [{0}] stop: {1}'
                  .format(strategy, repr(err[1])))
            print_tb(err[2])
            if exit_on_error:
                exit(1)

    return [strategy.state for strategy in strategies]

def plot(strategies, data, args):
    import numpy as np
    import matplotlib.cm as cm
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    plt.style.use('dark_background')

    start = args.begin
    step = args.interval
    date_formatter = FuncFormatter(
        lambda x, _: datetime.fromtimestamp((int(start + x * step)))
    )

    fig, ax = plt.subplots()

    price = data.get_plot(args.pair)

    plot_data = [strategy.get_plots() for strategy in strategies]

    n_subplots = max(1, *(len(d) for d in plot_data))
    subplots = [
        plt.subplot(n_subplots, 1, n_subplots - i, sharex=ax)
        for i in range(n_subplots)
    ]

    colors = [
        (
            iter(cm.rainbow(np.linspace(
                0, 1,
                int(i == 0) +
                sum(len(subplot[i][0]) if len(subplot) > i else 0
                    for subplot in plot_data)
            ))),
            iter(cm.Pastel1(np.linspace(
                0, 1,
                sum(len(subplot[i][0]) if len(subplot) > i else 0
                    for subplot in plot_data)
            )))
        )
        for i in range(n_subplots)
    ]

    plots = [[] for _ in range(n_subplots)]
    plots[0].append(
        subplots[0].plot(
            price,
            color=next(colors[0][0]),
            alpha=0.75,
            label='price'
        )[0]
    )

    for pdata in plot_data:
        size = randint(100, 400)
        for subplot, handles, (plot_colors, scatter_colors), (plots_, points_) \
            in zip(subplots, plots, colors, pdata):
            for label, values in plots_.items():
                color = next(plot_colors)
                handles.append(
                    subplot.plot(
                        values,
                        color=color,
                        alpha=0.9,
                        label=label
                    )[0]
                )
            for label, (xs, ys) in points_.items():
                color = next(scatter_colors)
                handles.append(
                    subplot.scatter(
                        xs, ys,
                        s=size,
                        color=color,
                        alpha=0.6,
                        marker='o',
                        label=label
                    )
                )

    for subplot, handles in zip(subplots, plots):
        subplot.grid(True)
        subplot.legend(handles=handles, scatterpoints=1)

    ax.xaxis.set_major_formatter(date_formatter)
    ax.set_xlim(0, args.max_ticks - 1)
    fig.autofmt_xdate()
    plt.show()

def buy_and_hold(portfolio, data, max_ticks, pair):
    currencies = pair.split('_')

    start_price = Decimal(
        data.get_current(0, pair)[data.CANDLE.close]
    )
    end_price = Decimal(
        data.get_current(max_ticks - 1, pair)[data.CANDLE.close]
    )

    start_asset = Decimal(portfolio.get(currencies[0], 0))
    start_currency = Decimal(portfolio.get(currencies[1], 0))

    start_asset += start_currency / start_price
    start_currency = 0

    start_max_currency = start_asset * start_price
    end_max_currency = start_asset * end_price

    return (start_price, end_price, start_asset,
            start_max_currency, end_max_currency)

def print_result(strategies, results, data, args):
    (start_price, end_price,
     start_max_asset, start_max_currency, bnh_end_currency) = buy_and_hold(
         args.portfolio, data, args.max_ticks, args.pair
     )

    pair = args.pair
    get_asset, get_currency = tuple(currency for currency in pair.split('_'))

    pair = args.pair.upper()
    asset, currency = tuple(currency for currency in pair.split('_'))

    fmt = '{0}\t{1:.8f} {2}\t{3:.2f}\t{4:.8f} {5}\t{6:.2f}'

    print('-' * 60)
    print('Pair               ', pair)
    print('Start date         ', ctime(args.begin))
    print('End date           ', ctime(args.end))
    print('Start price        ', '{0:.8f}'.format(start_price))
    print('End price          ', '{0:.8f}'.format(end_price))
    print('Start portfolio    ', args.portfolio)
    print('Start max currency ',
          '{0:.8f}'.format(start_max_currency),
          currency)
    print('Start max asset    ',
          '{0:.8f}'.format(start_max_asset),
          asset)
    print('-' * 60)
    print('Strategy\tMax currency\tROI currency\tMax asset\tROI asset')
    print(fmt.format(
        'buy and hold',
        bnh_end_currency, currency, bnh_end_currency / start_max_currency,
        start_max_asset, asset, 1.0
    ))
    for strategy, res in zip(strategies, results):
        res_asset = Decimal(res.get(get_asset, 0))
        res_currency = Decimal(res.get(get_currency, 0))
        res_max_asset = res_asset + res_currency / end_price
        res_max_currency = res_asset * end_price + res_currency
        print(fmt.format(
            strategy,
            res_max_currency, currency, res_max_currency / start_max_currency,
            res_max_asset, asset, res_max_asset / start_max_asset
        ))
    print('-' * 60)

def main():
    parser = create_argument_parser()
    args = parser.parse_args()

    data = FileDataSource(
        args.data,
        start_time=args.begin,
        tick_size=args.interval
    )

    if args.begin is None:
        args.begin = data.start_time

    if args.interval is None:
        args.interval = data.tick_size

    if args.end is None:
        args.max_ticks = data.get_max_ticks()
        args.end = args.begin + (args.max_ticks - 1) * args.interval
    else:
        args.max_ticks = (args.end - args.begin) // args.interval
        args.max_ticks += 1

    if args.max_ticks <= 0:
        print('Error: invalid interval: {0} -- {1}'
              .format(ctime(args.begin), ctime(args.end)))
        exit(1)

    args.max_ticks = min(args.max_ticks, data.get_max_ticks())

    if args.pair is None:
        try:
            args.pair = next(iter(data.datasets()))
        except StopIteration:
            print('Error: data source is empty')
            exit(1)
    else:
        args.pair = args.pair.lower()

    TradewaveAPI.add_pair(args.pair)

    args.portfolio = dict(zip(args.pair.split('_'), args.portfolio))

    strategies = [
        TradewaveAPI(fname, args.portfolio, data,
                     max_ticks=args.max_ticks,
                     primary_pair=args.pair,
                     verbose=args.verbose)
        for fname in args.strategy
    ]

    res = run(strategies, args.max_ticks, not args.no_progress)

    print_result(strategies, res, data, args)

    if not args.no_plot:
        plot(strategies, data, args)
