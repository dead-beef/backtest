from __future__ import print_function

from copy import deepcopy
from decimal import Decimal
from time import ctime
from collections import defaultdict

import numpy as np

from .data import Portfolio, Storage, Data, Money
from .util import (TradewaveInvalidOrderError,
                   TradewaveFundsError, TradewaveDataError,
                   EXCHANGES, CURRENCIES, PAIRS, PAIR_CURRENCIES, INTERVALS)
from ..base import PythonAPI, Stop, Namespace
from backtest.util import enum


class TradewaveAPI(PythonAPI):
    def __init__(self, module, portfolio, source, max_ticks=None,
                 primary_pair=None, primary_exchange=EXCHANGES[0],
                 fees=None, verbose=False):
        super(TradewaveAPI, self).__init__(module, verbose)

        if primary_pair is None:
            try:
                primary_pair = next(iter(source.datasets()))
            except StopIteration:
                raise ValueError('empty data source')

        if primary_pair not in self.CONST_ENV['pairs']:
            raise ValueError('invalid pair {0}'.format(primary_pair))

        if primary_exchange not in self.CONST_ENV['exchanges']:
            raise ValueError('invalid exchange {0}'.format(primary_exchange))

        src_max_ticks = source.get_max_ticks(primary_pair)
        if src_max_ticks == 0:
            raise ValueError('no data for primary pair {0}'
                             .format(primary_pair))
        if max_ticks is None or max_ticks <= 0 or max_ticks > src_max_ticks:
            max_ticks = src_max_ticks

        if fees is None:
            fees = {}
        fees = [Decimal(fees.get(currency, 0)) for currency in CURRENCIES]
        self.fees = [fees] * len(EXCHANGES)

        self.portfolio = Portfolio(**portfolio)
        self.storage = Storage()
        self.data = Data(source)
        self.info = Namespace(
            tick=0,
            running_time=0,
            current_time=source.start_time,
            max_ticks=max_ticks,
            interval=source.tick_size,
            begin=source.start_time,
            end=source.start_time + (max_ticks - 1) * source.tick_size,
            starting_portfolio=deepcopy(self.portfolio),
            primary_pair=self.CONST_ENV['pairs'][primary_pair],
            primary_exchange=self.CONST_ENV['exchanges'][primary_exchange]
        )

        self.primary_pair = PAIR_CURRENCIES[self.info.primary_pair]

        new_plot = lambda: np.zeros(max_ticks, dtype=np.float)

        self.plots = defaultdict(new_plot)
        self.secondary_plots = defaultdict(new_plot)
        self.buy_plot = ([], [])
        self.sell_plot = ([], [])

    def do_start(self):
        super(TradewaveAPI, self).do_start()
        if hasattr(self.module, 'initialize'):
            self.module.initialize()

    def do_tick(self, tick):
        self.info.tick = tick
        self.info.running_time = tick * self.info.interval
        self.info.current_time = self.info.begin + self.info.running_time
        self.data.update(tick)
        self.portfolio.update()
        self.module.tick()
        return self.portfolio

    def do_stop(self):
        if hasattr(self.module, 'stop'):
            self.module.stop()

    def get_plots(self):
        point_plots = {}
        if self.buy_plot[0]:
            point_plots['buy'] = self.buy_plot
        if self.sell_plot[0]:
            point_plots['sell'] = self.sell_plot

        ret = [(self.plots, point_plots)]

        if self.secondary_plots:
            ret.append((self.secondary_plots, {}))

        return ret

    def get_env(self):
        env = deepcopy(self.CONST_ENV)
        for attr in self.ENV:
            env[attr] = getattr(self, attr)
        return env

    @staticmethod
    def validate_order(pair, amount, price):
        if price is not None:
            raise NotImplementedError('limit order')
        if pair < 0 or pair >= len(PAIRS):
            raise TradewaveInvalidOrderError('invalid pair: {0}'.format(pair))
        if amount is not None and amount <= 0:
            raise TradewaveInvalidOrderError(
                'invalid amount: {0}'.format(amount)
            )

    def buy(self, pair, amount=None, price=None, timeout=60): # pylint: disable=unused-argument
        self.validate_order(pair, amount, price)

        dst, src = PAIR_CURRENCIES[pair]
        price = self.data[pair].close # self.data[pair].price

        if amount is None:
            if self.portfolio.next[src] == 0:
                raise TradewaveFundsError('buy: portfolio=0')
            amount = self.portfolio.next[src] / price
            self.portfolio.next[dst] += amount
            self.portfolio.next[src] = Decimal(0)
        else:
            amount = Decimal(amount)
            max_amount = self.portfolio.next[src] / price
            if amount > max_amount:
                raise TradewaveFundsError(
                    'buy: amount={0} portfolio={1} max={2}'
                    .format(amount, self.portfolio.next[src], max_amount)
                )
            self.portfolio.next[dst] += amount
            self.portfolio.next[src] -= amount * price

        if self.verbose:
            print(
                '[{0}] [{1}] BUY {2:.8f} {3} -> {4:.8f} {5} (price {6:.8f})'
                .format(
                    ctime(self.info.current_time),
                    self, amount * price, src.upper(),
                    amount, dst.upper(), price
                )
            )
        self.buy_plot[0].append(self.info.tick)
        self.buy_plot[1].append(price)

    def sell(self, pair, amount=None, price=None, timeout=60): # pylint: disable=unused-argument
        self.validate_order(pair, amount, price)

        src, dst = PAIR_CURRENCIES[pair]
        price = self.data[pair].close # self.data[pair].price

        if amount is None:
            amount = self.portfolio.next[src]
            if amount == 0:
                raise TradewaveFundsError('sell: portfolio=0')
        elif amount > self.portfolio.next[src]:
            raise TradewaveFundsError('sell: amount={0} portfolio={1}'
                                      .format(amount, self.portfolio.next[src]))
        amount = Decimal(amount)

        if self.verbose:
            print(
                '[{0}] [{1}] SELL {2:.8f} {3} -> {4:.8f} {5} (price {6})'
                .format(
                    ctime(self.info.current_time),
                    self, amount, src.upper(),
                    amount * price, dst.upper(), price
                )
            )

        self.portfolio.next[dst] += amount * price
        self.portfolio.next[src] -= amount
        self.sell_plot[0].append(self.info.tick)
        self.sell_plot[1].append(price)

    def log(self, *args, **kwargs):
        print('[{0}] [{1}] LOG: '
              .format(ctime(self.info.current_time), self),
              end='')
        print(*args, **kwargs)

    def email(self, message, subject=None):
        print('[{0}] [{1}] EMAIL: {2} {3}'
              .format(ctime(self.info.current_time), self,
                      subject or '<no subject>', message))

    def plot(self, series_key, value, secondary=False):
        plots = self.secondary_plots if secondary else self.plots
        plots[series_key][self.info.tick] = value

    @staticmethod
    def get_json(url):
        raise NotImplementedError('get_json "{0}"'.format(url))

    @staticmethod
    def get_text(url):
        raise NotImplementedError('get_text "{0}"'.format(url))

    @classmethod
    def add_currency(cls, currency):
        if currency not in cls.CONST_ENV['currencies']:
            cls.CONST_ENV['currencies'][currency] = len(CURRENCIES)
            CURRENCIES.append(currency)

    @classmethod
    def add_pair(cls, pair):
        if pair not in cls.CONST_ENV['pairs']:
            currencies = pair.split('_')
            if len(currencies) != 2:
                raise ValueError('invalid pair {0}'.format(pair))
            cls.add_currency(currencies[0])
            cls.add_currency(currencies[1])
            cls.CONST_ENV['pairs'][pair] = len(PAIRS)
            PAIRS.append(pair)
            PAIR_CURRENCIES.append(tuple(currencies))


    CONST_ENV = {
        'Decimal': Decimal,
        'Money': Money,
        'TradewaveInvalidOrderError': TradewaveInvalidOrderError,
        'TradewaveFundsError': TradewaveFundsError,
        'TradewaveDataError': TradewaveDataError,
        'Stop': Stop,
        'currencies': enum(CURRENCIES),
        'pairs': enum(PAIRS),
        'exchanges': enum(EXCHANGES),
        'intervals': INTERVALS,
    }

    ENV = [
        'fees', 'portfolio', 'storage', 'info', 'data',
        'buy', 'sell', 'plot', 'log', 'email', 'get_json', 'get_text'
    ]
