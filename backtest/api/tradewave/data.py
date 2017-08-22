from __future__ import division
import operator
from decimal import Decimal
from collections import defaultdict
import talib as ta

from .util import (Namespace, TradewaveDataError,
                   CURRENCIES, PAIRS, DATA, DATA_INDEX, MAX_PERIOD)


class Portfolio(Namespace):
    def __init__(self, **kwargs):
        super(Portfolio, self).__init__()

        for currency in CURRENCIES:
            self[currency] = Decimal(kwargs.get(currency, 0))

        if 'is_next' not in kwargs:
            self.next = Portfolio(is_next=True, **kwargs)
        else:
            self.next = None

    def __getitem__(self, item):
        if not isinstance(item, basestring):
            item = CURRENCIES[item]
        return super(Portfolio, self).__getitem__(item)

    def assign(self, portfolio):
        for currency in CURRENCIES:
            self[currency] = portfolio[currency]

    def update(self):
        self.assign(self.next)


class Storage(Namespace):
    CHANNELS = defaultdict(lambda: Storage()) # pylint: disable=unnecessary-lambda

    def __call__(self, channel):
        return self.CHANNELS[channel]

    def set_channel(self, key):
        self.CHANNELS[key] = self

    def reset(self):
        super(Storage, self).clear()


class Data(Namespace):
    def __init__(self, source, interval=None):
        super(Data, self).__init__()
        self._tick = None
        self._interval = interval
        self._source = source
        for pair in PAIRS:
            if pair in self._source:
                self[pair] = PairData(self._source, pair,
                                      interval=self._interval)
            else:
                self[pair] = None

    def __getitem__(self, item):
        if not isinstance(item, basestring):
            item = PAIRS[item]
        return super(Data, self).__getitem__(item)

    def __call__(self, exchange=None, interval=None, smooth=True):
        ret = Data(self._source, interval or self._interval)
        if self._tick is not None:
            ret.update(self._tick)
        return ret

    def update(self, tick):
        self._tick = tick
        for pair in (self[p] for p in PAIRS):
            if pair is not None:
                pair.update(tick)


class PairData(Namespace): # pylint:disable=too-many-public-methods
    def __init__(self, source, name=None, tick=None, interval=None):
        super(PairData, self).__init__()
        self._source = source
        self._name = name
        self._interval = interval
        if tick is not None:
            self.update(tick)
        else:
            self._tick = None

    def __getitem__(self, idx):
        if isinstance(idx, basestring):
            return super(PairData, self).__getitem__(idx)
        if idx > 0 or idx < -MAX_PERIOD:
            raise TradewaveDataError('invalid index {0}'.format(idx))
        if idx == 0:
            return self
        return PairData(self._source, self._name,
                        self._tick + idx, self._interval)

    def update(self, tick):
        self._tick = tick

        try:
            candle = self._source.get_current(tick, self._name, self._interval)
        except (IndexError, KeyError) as err:
            raise TradewaveDataError(err.message)

        for attr in DATA:
            self[attr] = Decimal(candle[DATA_INDEX[attr]])

    def period(self, length, name):
        if length <= 0 or length > MAX_PERIOD:
            raise TradewaveDataError('invalid period length: {0}'
                                     .format(length))
        try:
            data = self._source.get_prev(self._tick, length,
                                         self._name, self._interval)
            return data[:, DATA_INDEX[name]]
        except (IndexError, KeyError) as err:
            raise TradewaveDataError(err.message)

    def warmup_period(self, name):
        return self.period(30, name)

    def vwap(self, period):
        raise NotImplementedError('vwap')

    def macd(self, fast_period, slow_period, signal_period=9):
        raise NotImplementedError('macd')

    def mfi(self, period):
        raise NotImplementedError('mfi')

    def ma(self, period): # pylint:disable=invalid-name
        return Decimal(self.period(period, 'price').mean())

    def std(self, period):
        return Decimal(self.period(period, 'price').std())

    def ema(self, period):
        return Decimal(ta.EMA(self.period(period, 'price'), period)[-1])

    def aroon(self, period):
        aroon_down, aroon_up = ta.AROON(self.period(period, 'high'),
                                        self.period(period, 'low'),
                                        period)
        return Decimal(aroon_down[-1]), Decimal(aroon_up[-1])

    def sar(self, acceleration, max_acceleration):
        period = 30
        return Decimal(
            ta.SAR(
                self.period(period, 'high'),
                self.period(period, 'low'),
                acceleration,
                max_acceleration
            )[-1]
        )

    def rsi(self, period):
        return Decimal(ta.RSI(self.period(period + 1, 'price'), period)[-1])

    def stochrsi(self, period, fastk_period, fastd_period, fastd_matype=0):
        fastk, fastd = ta.STOCHRSI(
            self.period(period + fastk_period + fastd_period, 'price'),
            fastk_period,
            fastd_period,
            fastd_matype
        )
        return Decimal(fastk[-1]), Decimal(fastd[-1])

    def stoch(self, fastk_period, slowk_period,
              slowd_period, slowk_matype=0, slowd_matype=0):
        period = fastk_period + slowk_period + 1
        slowk, slowd = ta.STOCH(
            self.period(period, 'high'),
            self.period(period, 'low'),
            self.period(period, 'close'),
            fastk_period, slowk_period, slowd_period,
            slowk_matype, slowd_matype
        )
        return Decimal(slowk[-1]), Decimal(slowd[-1])

    def adx(self, period):
        return Decimal(
            ta.ADX(
                self.period(period * 2, 'high'),
                self.period(period * 2, 'low'),
                self.period(period * 2, 'close'),
                period
            )[-1]
        )

    def atr(self, period):
        return Decimal(
            ta.ATR(
                self.period(period + 1, 'high'),
                self.period(period + 1, 'low'),
                self.period(period + 1, 'close'),
                period
            )[-1]
        )

    def mom(self, period):
        return Decimal(ta.MOM(self.period(period + 1, 'price'), period)[-1])

    def tsf(self, period):
        return Decimal(ta.MOM(self.period(period, 'price'), period)[-1])


class Money(object):
    BINOP = lambda opfn: \
            lambda self, other: self.bin_op(other, opfn)
    RBINOP = lambda opfn: \
             lambda self, other: Money(other, self.currency).bin_op(self, opfn)

    def __init__(self, amount, currency):
        self.amount = Decimal(amount)
        self.currency = currency

    def __repr__(self):
        return str(self)

    def __str__(self):
        return '{0} {1}'.format(self.amount, self.currency)

    def get_amount(self, other):
        if isinstance(other, Money):
            if self.currency != other.currency:
                raise ValueError('self.currency != other.currency: {0} {1}'
                                 .format(self.currency, other.currency))
            return other.amount
        return Decimal(other)

    def bin_op(self, other, opfn):
        return Money(opfn(self.amount, self.get_amount(other)), self.currency)

    def to_decimal(self):
        return self.amount

    def to_float(self):
        return float(self.amount)

    def __cmp__(self, other):
        res = self.amount - self.get_amount(other)
        return -1 if res < 0 else 1 if res > 0 else 0

    def __eq__(self, other):
        if isinstance(other, Money):
            return (self.amount == other.amount
                    and self.currency == other.currency)
        return self.amount == other

    def __ne__(self, other):
        return not self.__eq__(other)

    __add__ = BINOP(operator.add)
    __sub__ = BINOP(operator.sub)
    __mul__ = BINOP(operator.mul)
    __div__ = BINOP(operator.div)
    __radd__ = RBINOP(operator.add)
    __rsub__ = RBINOP(operator.sub)
    __rmul__ = RBINOP(operator.mul)
    __rdiv__ = RBINOP(operator.div)
