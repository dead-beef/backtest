from unittest import TestCase
try:
    from unittest.mock import patch, call, MagicMock # pylint:disable=import-error,no-name-in-module
except ImportError:
    from mock import patch, call, MagicMock

from decimal import Decimal
from types import MethodType
from sys import exc_info
from StringIO import StringIO
from numpy.testing import assert_array_almost_equal

from backtest.api.tradewave.api import TradewaveAPI
from backtest.api.tradewave.util import (
    CURRENCIES, PAIR_CURRENCIES, EXCHANGES, PAIRS,
    TradewaveInvalidOrderError, TradewaveFundsError
)
from backtest.util import Namespace


@patch('backtest.api.tradewave.api.Portfolio')
@patch('backtest.api.tradewave.api.Data')
class TestTradewaveAPI(TestCase):
    src = MagicMock(
        tick_size=3,
        start_time=4,
        get_max_ticks=MagicMock(return_value=5),
        datasets=MagicMock(return_value=['btc_usd'])
    )

    def testInitDefault(self, data, portfolio):
        portfolio.return_value = 5
        data.return_value = 0
        api = TradewaveAPI('/test/module', {}, self.src)
        portfolio.assert_called_with()
        data.assert_called_with(self.src)
        self.assertIsNone(api.module)
        self.assertEqual(api.module_path, '/test/module')
        self.assertEqual(api.fees,
                         [[Decimal(0)] * len(CURRENCIES)] * len(EXCHANGES))
        self.assertEqual(api.primary_pair, tuple(PAIRS[0].split('_')))
        self.assertEqual(api.plots, {})
        assert_array_almost_equal(api.plots[0], [0, 0, 0, 0, 0])
        self.assertEqual(api.secondary_plots, {})
        assert_array_almost_equal(api.secondary_plots[0], [0, 0, 0, 0, 0])
        self.assertEqual(api.buy_plot, ([], []))
        self.assertEqual(api.sell_plot, ([], []))
        self.assertEqual(api.data, 0)
        self.assertEqual(api.storage, Namespace())
        self.assertEqual(api.info.tick, 0)
        self.assertEqual(api.info.max_ticks, 5)
        self.assertEqual(api.info.interval, 3)
        self.assertEqual(api.info.begin, 4)
        self.assertEqual(api.info.end, 16)
        self.assertEqual(api.info.starting_portfolio, 5)
        self.assertEqual(api.info.primary_pair, 0)
        self.assertEqual(api.info.primary_exchange, 0)

    def testInit(self, data, portfolio):
        portfolio.return_value = 5
        pdata = {'btc': 1, 'ltc': 2}
        data.return_value = 1
        fees = dict((currency, idx) for idx, currency in enumerate(CURRENCIES))
        api = TradewaveAPI('/test/module', pdata, self.src,
                           max_ticks=3,
                           primary_pair=PAIRS[1],
                           primary_exchange=EXCHANGES[2],
                           fees=fees)
        fees = [Decimal(fees[currency]) for currency in CURRENCIES]
        fees = [fees] * len(EXCHANGES)
        portfolio.assert_called_with(**pdata)
        data.assert_called_with(self.src)
        self.assertIsNone(api.module)
        self.assertEqual(api.module_path, '/test/module')
        self.assertEqual(api.fees, fees)
        self.assertEqual(api.primary_pair, tuple(PAIRS[1].split('_')))
        self.assertEqual(api.plots, {})
        assert_array_almost_equal(api.plots[0], [0, 0, 0])
        self.assertEqual(api.secondary_plots, {})
        assert_array_almost_equal(api.secondary_plots[0], [0, 0, 0])
        self.assertEqual(api.buy_plot, ([], []))
        self.assertEqual(api.sell_plot, ([], []))
        self.assertEqual(api.data, 1)
        self.assertEqual(api.storage, Namespace())
        self.assertEqual(api.info.tick, 0)
        self.assertEqual(api.info.max_ticks, 3)
        self.assertEqual(api.info.interval, 3)
        self.assertEqual(api.info.begin, 4)
        self.assertEqual(api.info.end, 10)
        self.assertEqual(api.info.starting_portfolio, 5)
        self.assertEqual(api.info.primary_pair, 1)
        self.assertEqual(api.info.primary_exchange, 2)

    def testInitError(self, data, portfolio):
        src = MagicMock(
            get_max_ticks=MagicMock(return_value=0),
            datasets=MagicMock(return_value=['btc_usd'])
        )
        with self.assertRaises(ValueError):
            TradewaveAPI('', {}, src)
        with self.assertRaises(ValueError):
            TradewaveAPI('', {}, self.src, primary_pair='test')
        with self.assertRaises(ValueError):
            TradewaveAPI('', {}, self.src, primary_exchange='test')

        src.get_max_ticks.return_value = 1
        src.datasets.return_value = []
        with self.assertRaises(ValueError):
            TradewaveAPI('', {}, src)

    def testGetEnv(self, data, portfolio):
        api = TradewaveAPI('', {}, self.src)
        env = api.get_env()
        for name, value in api.CONST_ENV.items():
            self.assertEqual(env[name], value)
            if isinstance(value, (list, dict)):
                self.assertIsNot(env[name], value)
        for name in api.ENV:
            if isinstance(env[name], MethodType):
                self.assertEqual(env[name], getattr(api, name))
            else:
                self.assertIs(env[name], getattr(api, name))

    @patch('backtest.api.base.PythonAPI.do_start')
    def testDoStart(self, do_start, data, portfolio):
        api = TradewaveAPI('', {}, self.src)
        api.module = MagicMock()
        api.do_start()
        do_start.assert_called_with()
        api.module.initialize.assert_called_with()

        initialize = api.module.initialize
        initialize.reset_mock()
        del api.module.initialize
        do_start.reset_mock()
        api.do_start()
        do_start.assert_called_with()
        self.assertFalse(initialize.called)

    def testDoTick(self, data, portfolio):
        api = TradewaveAPI('', {}, self.src)
        api.module = MagicMock()
        api.do_tick(2)
        self.assertEqual(api.info.tick, 2)
        self.assertEqual(api.info.running_time, 2 * self.src.tick_size)
        self.assertEqual(api.info.current_time,
                         self.src.start_time + 2 * self.src.tick_size)
        api.data.update.assert_called_with(2)
        api.portfolio.update.assert_called_with()
        api.module.tick.assert_called_with()

    def testDoStop(self, data, portfolio):
        api = TradewaveAPI('', {}, self.src)
        api.module = MagicMock()
        api.do_stop()
        api.module.stop.assert_called_with()

        stop = api.module.stop
        stop.reset_mock()
        del api.module.stop
        api.do_stop()
        self.assertFalse(stop.called)

    def testValidateOrder(self, data, portfolio):
        api = TradewaveAPI('', {}, self.src)

        with self.assertRaises(NotImplementedError):
            api.validate_order(0, 1, 1)

        tests = [
            (-1, 1, None),
            (len(PAIRS), 1, None),
            (0, 0, None),
            (0, -1, None)
        ]

        for test in tests:
            try:
                with self.assertRaises(TradewaveInvalidOrderError):
                    api.validate_order(*test)
            except AssertionError as err:
                raise AssertionError(err.message, test), None, exc_info()[2]

    def testBuy(self, data, portfolio):
        api = TradewaveAPI('', {}, self.src)

        pair = 0
        dst, src = PAIR_CURRENCIES[pair]

        api.info.tick = 2
        api.data[pair].price = Decimal(4)
        api.portfolio.next = {
            src: Decimal(10),
            dst: Decimal(1)
        }

        with self.assertRaises(TradewaveFundsError):
            api.buy(pair, 3)

        api.buy(pair, 0.5)
        self.assertAlmostEqual(api.portfolio.next[src], Decimal(8))
        self.assertAlmostEqual(api.portfolio.next[dst], Decimal(1.5))
        self.assertEqual(api.buy_plot, ([2], [4]))

        api.info.tick = 3
        api.data[pair].price = Decimal(8)

        api.buy(pair)
        self.assertAlmostEqual(api.portfolio.next[src], Decimal(0))
        self.assertAlmostEqual(api.portfolio.next[dst], Decimal(2.5))
        self.assertEqual(api.buy_plot, ([2, 3], [4, 8]))

        with self.assertRaises(TradewaveFundsError):
            api.buy(pair)

    def testSell(self, data, portfolio):
        api = TradewaveAPI('', {}, self.src)

        pair = 0
        src, dst = PAIR_CURRENCIES[pair]

        api.info.tick = 2
        api.data[pair].price = Decimal(4)
        api.portfolio.next = {
            dst: Decimal(10),
            src: Decimal(1)
        }

        with self.assertRaises(TradewaveFundsError):
            api.sell(pair, 3)

        api.sell(pair, 0.5)
        self.assertAlmostEqual(api.portfolio.next[src], Decimal(0.5))
        self.assertAlmostEqual(api.portfolio.next[dst], Decimal(12))
        self.assertEqual(api.sell_plot, ([2], [4]))

        api.info.tick = 3

        api.sell(pair)
        self.assertAlmostEqual(api.portfolio.next[src], Decimal(0))
        self.assertAlmostEqual(api.portfolio.next[dst], Decimal(14))
        self.assertEqual(api.sell_plot, ([2, 3], [4, 4]))

        with self.assertRaises(TradewaveFundsError):
            api.sell(pair)

    @patch('sys.stdout', new_callable=StringIO)
    @patch('backtest.api.tradewave.api.ctime', return_value='time')
    def testLog(self, ctime, stdout, data, portfolio):
        api = TradewaveAPI('module', {}, self.src)
        api.info.current_time = 10
        api.log('test')
        ctime.assert_called_with(10)
        self.assertEqual(stdout.getvalue(), '[time] [module] LOG: test\n')

    @patch('sys.stdout', new_callable=StringIO)
    @patch('backtest.api.tradewave.api.ctime', return_value='time')
    def testEmail(self, ctime, stdout, data, portfolio):
        api = TradewaveAPI('module', {}, self.src)
        api.info.current_time = 2
        api.email('message', 'subject')
        ctime.assert_called_with(2)
        self.assertEqual(
            stdout.getvalue(),
            '[time] [module] EMAIL: subject message\n'
        )
        stdout.seek(0)
        stdout.truncate(0)
        api.email('message')
        self.assertEqual(
            stdout.getvalue(),
            '[time] [module] EMAIL: <no subject> message\n'
        )

    def testPlot(self, data, portfolio):
        api = TradewaveAPI('', {}, self.src)
        api.info.tick = 2
        api.plot('key', 0.5)
        assert_array_almost_equal(api.plots['key'], [0, 0, 0.5, 0, 0])

        api.info.tick = 3
        api.plot('key', 0.25, secondary=True)
        assert_array_almost_equal(
            api.secondary_plots['key'],
            [0, 0, 0, 0.25, 0]
        )

    def testGetPlots(self, data, portfolio):
        api = TradewaveAPI('', {}, self.src)
        plots = api.get_plots()
        self.assertEqual(len(plots), 1)
        self.assertEqual(len(plots[0]), 2)
        self.assertIs(plots[0][0], api.plots)
        self.assertEqual(plots[0][1], {})

        api.plot('key', 0.5)
        plots = api.get_plots()
        self.assertEqual(len(plots), 1)
        self.assertEqual(len(plots[0]), 2)
        self.assertIs(plots[0][0], api.plots)
        self.assertEqual(plots[0][1], {})

        api.info.tick = 0
        api.plot('key', 0.5, secondary=True)
        plots = api.get_plots()
        self.assertEqual(len(plots), 2)
        self.assertEqual(len(plots[0]), 2)
        self.assertIs(plots[0][0], api.plots)
        self.assertEqual(plots[0][1], {})
        self.assertEqual(len(plots[1]), 2)
        self.assertIs(plots[1][0], api.secondary_plots)
        self.assertEqual(plots[1][1], {})

        api.buy_plot = ([0], [0])
        api.sell_plot = ([1], [1])
        plots = api.get_plots()
        self.assertEqual(len(plots), 2)
        self.assertEqual(len(plots[0]), 2)
        self.assertIs(plots[0][0], api.plots)
        self.assertEqual(plots[0][1],
                         {'buy': api.buy_plot, 'sell': api.sell_plot})
        self.assertEqual(len(plots[1]), 2)
        self.assertIs(plots[1][0], api.secondary_plots)
        self.assertEqual(plots[1][1], {})

    @patch('backtest.api.tradewave.api.CURRENCIES', new_callable=list)
    @patch('backtest.api.tradewave.api.TradewaveAPI.CONST_ENV',
           new_callable=dict)
    def testAddCurrency(self, const_env, currencies, data, portfolio):
        const_env['currencies'] = {}
        TradewaveAPI.add_currency('btc')
        self.assertEqual(currencies, ['btc'])
        self.assertEqual(const_env['currencies'], {'btc': 0})

        TradewaveAPI.add_currency('ltc')
        self.assertEqual(currencies, ['btc', 'ltc'])
        self.assertEqual(const_env['currencies'], {'btc': 0, 'ltc': 1})

        TradewaveAPI.add_currency('btc')
        self.assertEqual(currencies, ['btc', 'ltc'])
        self.assertEqual(const_env['currencies'], {'btc': 0, 'ltc': 1})

    @patch('backtest.api.tradewave.api.TradewaveAPI.add_currency')
    @patch('backtest.api.tradewave.api.PAIRS', new_callable=list)
    @patch('backtest.api.tradewave.api.PAIR_CURRENCIES', new_callable=list)
    @patch('backtest.api.tradewave.api.TradewaveAPI.CONST_ENV',
           new_callable=dict)
    def testAddPair(self, const_env, pair_currencies,
                    pairs, add_currency, data, portfolio):
        const_env['pairs'] = {}
        TradewaveAPI.add_pair('btc_ltc')
        self.assertEqual(pairs, ['btc_ltc'])
        self.assertEqual(pair_currencies, [('btc', 'ltc')])
        self.assertEqual(const_env['pairs'], {'btc_ltc': 0})
        self.assertEqual(add_currency.call_count, 2)
        add_currency.assert_has_calls([call('btc'), call('ltc')])

        add_currency.reset_mock()
        TradewaveAPI.add_pair('btc_ltc')
        self.assertEqual(pairs, ['btc_ltc'])
        self.assertEqual(pair_currencies, [('btc', 'ltc')])
        self.assertEqual(const_env['pairs'], {'btc_ltc': 0})
        self.assertEqual(add_currency.call_count, 0)

        with self.assertRaises(ValueError):
            TradewaveAPI.add_pair('btc_ltc_eth')
        self.assertEqual(add_currency.call_count, 0)

        TradewaveAPI.add_pair('btc_eth')
        self.assertEqual(pairs, ['btc_ltc', 'btc_eth'])
        self.assertEqual(pair_currencies, [('btc', 'ltc'), ('btc', 'eth')])
        self.assertEqual(const_env['pairs'], {'btc_ltc': 0, 'btc_eth': 1})
        self.assertEqual(add_currency.call_count, 2)
        add_currency.assert_has_calls([call('btc'), call('eth')])
