from unittest import TestCase
try:
    from unittest.mock import patch, call # pylint:disable=import-error,no-name-in-module
except ImportError:
    from mock import patch, call

import operator
from sys import exc_info
from decimal import Decimal
import numpy as np
from numpy.testing import assert_array_equal

from backtest.data import DataSource
from backtest.api.tradewave.data import (
    Portfolio, Storage, Money, Data, PairData
)
from backtest.api.tradewave.util import (
    TradewaveDataError, CURRENCIES, DATA, DATA_INDEX, MAX_PERIOD, PAIRS
)


class TestPortfolio(TestCase):
    def testInitDefault(self):
        p = Portfolio()
        self.assertIsInstance(p.next, Portfolio)
        self.assertIsNone(p.next.next)
        for i, currency in enumerate(CURRENCIES):
            self.assertAlmostEqual(p[currency], 0)
            self.assertAlmostEqual(p[i], 0)
            self.assertAlmostEqual(p.next[currency], 0)

    def testInit(self):
        c = CURRENCIES[0]
        args = {}
        args[c] = 1.0
        p = Portfolio(**args)
        for i, currency in enumerate(CURRENCIES):
            amount = args.get(currency, 0)
            self.assertAlmostEqual(p[currency], amount)
            self.assertAlmostEqual(p[i], amount)
            self.assertIsInstance(p[currency], Decimal)
            self.assertAlmostEqual(p.next[currency], amount)

    def testUpdate(self):
        p = Portfolio()
        for amount, currency in enumerate(CURRENCIES):
            p.next[currency] = amount + 1
            self.assertNotAlmostEqual(p[currency], p.next[currency])
        p.update()
        for currency in CURRENCIES:
            self.assertAlmostEqual(p[currency], p.next[currency])


class TestStorage(TestCase):
    def testChannel(self):
        s = Storage()
        self.assertIsNot(s(channel='test'), s)
        s.set_channel('test')
        self.assertIs(Storage()(channel='test'), s)


@patch('backtest.data.DataSource.__contains__', return_value=True)
@patch('backtest.api.tradewave.data.PairData')
class TestData(TestCase):
    def testInitDefault(self, pairData, contains):
        src = DataSource()
        data = Data(src)
        self.assertIs(data._source, src)
        self.assertIsNone(data._tick)
        self.assertIsNone(data._interval)
        self.assertEqual(contains.call_count, len(PAIRS))
        self.assertEqual(pairData.call_count, len(PAIRS))
        contains.assert_has_calls([call(pair) for pair in PAIRS])
        pairData.assert_has_calls([call(src, pair, interval=None)
                                   for pair in PAIRS])

    def testInit(self, pairData, contains):
        src = DataSource()
        data = Data(src, interval=1)
        self.assertIs(data._source, src)
        self.assertEqual(data._interval, 1)
        self.assertEqual(pairData.call_count, len(PAIRS))
        pairData.assert_has_calls([call(src, pair, interval=1)
                                   for pair in PAIRS])

    def testUpdate(self, pairData, contains):
        src = DataSource()
        data = Data(src)
        data.update(1)
        self.assertEqual(data._tick, 1)
        for pair in PAIRS:
            data[pair].update.assert_called_with(1)

    def testNoData(self, pairData, contains):
        contains.return_value = False
        src = DataSource()
        data = Data(src)
        self.assertIs(data._source, src)
        self.assertIsNone(data._interval)
        self.assertEqual(contains.call_count, len(PAIRS))
        self.assertFalse(pairData.called)
        for pair in PAIRS:
            self.assertIsNone(data[pair])
        data.update(1)

    def testGetItem(self, pairData, contains):
        pairData.side_effect = [i for i, _ in enumerate(PAIRS)]
        src = DataSource()
        data = Data(src)
        for i, pair in enumerate(PAIRS):
            self.assertEqual(data[pair], i)
            self.assertEqual(data[i], i)

    def testCall(self, pairData, contains):
        src = DataSource()
        data = Data(src)
        pairData.reset_mock()
        data.update(1)
        d = data(interval=3)
        self.assertIs(d._source, src)
        self.assertEqual(d._interval, 3)
        self.assertEqual(d._tick, data._tick)
        self.assertEqual(pairData.call_count, len(PAIRS))
        pairData.assert_has_calls([call(src, pair, interval=3)
                                   for pair in PAIRS])


@patch('backtest.data.DataSource.get_current',
       return_value=list(range(4)))
@patch('backtest.data.DataSource.get_prev',
       return_value=np.array([range(4), range(2, 6), range(3, 7), range(4, 8)]))
class TestPairData(TestCase):
    def testInit(self, get_prev, get_current):
        src = DataSource()
        data = PairData(src, 'test', 1, interval=1)
        self.assertIs(data._source, src)
        self.assertEqual(data._name, 'test')
        self.assertEqual(data._tick, 1)
        self.assertEqual(data._interval, 1)
        get_current.assert_called_with(1, 'test', 1)
        candle = get_current.return_value
        for attr in DATA:
            self.assertEqual(data[attr], candle[DATA_INDEX[attr]])

    def testUpdate(self, get_prev, get_current):
        data = PairData(DataSource(), 'test')
        self.assertIsNone(data._tick)
        data.update(2)
        get_current.assert_called_with(2, 'test', None)
        self.assertEqual(data._tick, 2)
        candle = get_current.return_value
        for attr in DATA:
            self.assertEqual(data[attr], candle[DATA_INDEX[attr]])

    def testUpdateError(self, get_prev, get_current):
        get_current.side_effect = IndexError
        data = PairData(DataSource(), 'test')
        with self.assertRaises(TradewaveDataError):
            data.update(1)
        get_current.side_effect = KeyError
        with self.assertRaises(TradewaveDataError):
            data.update(1)

    def testPeriod(self, get_prev, get_current):
        data = PairData(DataSource(), 'test', 1, interval=2)
        dataset = get_prev.return_value
        for attr in DATA:
            assert_array_equal(
                data.period(2, attr),
                dataset[:, DATA_INDEX[attr]]
            )
            get_prev.assert_called_with(1, 2, 'test', 2)

    def testPeriodError(self, get_prev, get_current):
        data = PairData(DataSource(), 'test', 1)

        with self.assertRaises(TradewaveDataError):
            data.period(0, 'test')

        get_prev.side_effect = IndexError
        with self.assertRaises(TradewaveDataError):
            data.period(1, 'test')

        get_prev.side_effect = KeyError
        with self.assertRaises(TradewaveDataError):
            data.period(1, 'test')

    def testGetItem(self, get_prev, get_current):
        data = PairData(DataSource(), 'test', 3)

        self.assertIs(data[0], data)

        prev_candle = get_current.return_value
        candle = [5, 4, 3, 2]
        get_current.return_value = candle
        d = data[-2]
        get_current.assert_called_with(1, 'test', None)

        for attr in DATA:
            self.assertEqual(data[attr], prev_candle[DATA_INDEX[attr]])
            self.assertEqual(d[attr], candle[DATA_INDEX[attr]])

        prev_candle = get_prev.return_value
        assert_array_equal(
            d.period(2, 'open'),
            prev_candle[:, DATA_INDEX['open']]
        )
        get_prev.assert_called_with(1, 2, 'test', None)

    def testGetItemError(self, get_prev, get_current):
        data = PairData(DataSource(), 'test', 3)
        with self.assertRaises(TradewaveDataError):
            data[1]
        with self.assertRaises(TradewaveDataError):
            data[-MAX_PERIOD - 1]


class TestMoney(TestCase):
    def testInit(self):
        m = Money('100', 'btc')
        self.assertAlmostEqual(m.amount, 100.0)
        self.assertEqual(m.currency, 'btc')
        self.assertIs(m.to_decimal(), m.amount)
        self.assertIsInstance(m.to_decimal(), Decimal)
        self.assertAlmostEqual(m.to_float(), m.amount)
        self.assertIsInstance(m.to_float(), float)

    def testEquality(self):
        tests = [
            ((Money(10, 'btc'), 10.0), True),
            ((Money(10, 'btc'), 10.01), False),
            ((Money(10, 'btc'), Money(10, 'btc')), True),
            ((Money(10, 'btc'), Money(10.01, 'btc')), False),
            ((Money(10, 'btc'), Money(10, 'ltc')), False)
        ]
        for test, res in tests:
            try:
                self.assertEqual(test[0] == test[1], res)
                self.assertEqual(test[0] != test[1], not res)
                self.assertEqual(test[1] == test[0], res)
                self.assertEqual(test[1] != test[0], not res)
            except AssertionError as err:
                raise AssertionError(err.message, test), None, exc_info()[2]

    def testComparsion(self):
        tests = [
            ((Money(10, 'btc'), 1), True, True),
            ((Money(10, 'btc'), 11), False, False),
            ((Money(10, 'btc'), Money(1, 'btc')), True, True),
            ((Money(10, 'btc'), Money(11, 'btc')), False, False),
            ((Money(10, 'btc'), Money(10, 'btc')), False, True),
        ]

        for test, gt, ge in tests:
            try:
                self.assertEqual(test[0] > test[1], gt)
                self.assertEqual(test[0] >= test[1], ge)
                self.assertEqual(test[0] < test[1], not ge)
                self.assertEqual(test[0] <= test[1], not gt)

                self.assertEqual(test[1] > test[0], not ge)
                self.assertEqual(test[1] >= test[0], not gt)
                self.assertEqual(test[1] < test[0], gt)
                self.assertEqual(test[1] <= test[0], ge)
            except AssertionError as err:
                raise AssertionError(err.message, test), None, exc_info()[2]

    def testComparsionError(self):
        with self.assertRaises(ValueError):
            Money(10, 'btc') < Money(10, 'ltc')
        with self.assertRaises(ValueError):
            Money(10, 'btc') > Money(10, 'ltc')

    def testArithmetic(self):
        ops = [
            operator.add, operator.sub,
            operator.mul, operator.div
        ]

        val = Money(10, 'btc')
        val2 = 2.0
        val2d = Decimal(val2)

        for opfn in ops:
            try:
                self.assertAlmostEqual(
                    opfn(val, val2),
                    Money(opfn(val.amount, val2d), val.currency)
                )
                self.assertAlmostEqual(
                    opfn(val2, val),
                    Money(opfn(val2d, val.amount), val.currency)
                )
            except AssertionError as err:
                raise AssertionError(err.message, opfn), None, exc_info()[2]

    def testArithmeticError(self):
        ops = [
            operator.add, operator.sub,
            operator.mul, operator.div
        ]
        val = Money(10, 'btc')
        val2 = Money(10, 'ltc')
        for opfn in ops:
            try:
                with self.assertRaises(ValueError):
                    opfn(val, val2)
            except AssertionError as err:
                raise AssertionError(err.message, opfn), None, exc_info()[2]
