from unittest import TestCase
try:
    from unittest.mock import patch # pylint:disable=import-error,no-name-in-module
except ImportError:
    from mock import patch

from backtest.api.base import API, PythonAPI, Stop


@patch('backtest.api.base.API.do_stop')
@patch('backtest.api.base.API.do_tick', return_value=1)
@patch('backtest.api.base.API.do_start')
class TestAPI(TestCase):
    def testInit(self, do_start, do_tick, do_stop):
        api = API()
        self.assertFalse(api.started)
        self.assertIsNone(api.state)
        self.assertFalse(api.verbose)

        api = API(verbose=True)
        self.assertFalse(api.started)
        self.assertIsNone(api.state)
        self.assertTrue(api.verbose)

    def testStart(self, do_start, do_tick, do_stop):
        api = API()
        api.start()
        self.assertTrue(api.started)
        self.assertIsNone(api.state)
        do_start.assert_called_with()

        do_start.reset_mock()
        api.start()
        self.assertFalse(do_start.called)

        api = API()
        do_start.reset_mock()
        do_start.side_effect = Stop
        api.start()
        self.assertFalse(api.started)
        self.assertIsNone(api.state)
        do_start.assert_called_with()

    def testTick(self, do_start, do_tick, do_stop):
        api = API()

        res = api.tick(0)
        self.assertIsNone(res)
        self.assertIsNone(api.state)
        self.assertFalse(api.started)
        self.assertFalse(do_tick.called)

        api.start()
        res = api.tick(0)
        do_tick.assert_called_with(0)
        self.assertEqual(res, 1)
        self.assertEqual(api.state, 1)

        do_tick.side_effect = Stop
        res = api.tick(1)
        do_tick.assert_called_with(1)
        self.assertEqual(res, 1)
        self.assertEqual(api.state, 1)
        self.assertFalse(api.started)

    def testStop(self, do_start, do_tick, do_stop):
        api = API()
        api.stop()
        self.assertFalse(do_stop.called)

        api.start()
        api.stop()
        do_stop.assert_called_with()
        self.assertFalse(api.started)

        api.start()
        do_stop.reset_mock()
        do_stop.side_effect = Stop
        api.stop()
        self.assertFalse(api.started)
        do_stop.assert_called_with()

    def testGetPlots(self, do_start, do_stop, do_tick):
        api = API()
        self.assertEqual(api.get_plots(), [])


@patch('backtest.api.base.PythonAPI.get_env', return_value={'x': 0})
@patch('backtest.module.ModuleLoader.load', return_value=0)
class TestPythonAPI(TestCase):
    def testInit(self, load, get_env):
        api = PythonAPI('/test/path')
        self.assertFalse(api.started)
        self.assertIsNone(api.state)
        self.assertFalse(api.verbose)
        self.assertEqual(api.module_path, '/test/path')
        self.assertIsNone(api.module)
        self.assertFalse(load.called)
        self.assertFalse(get_env.called)

    def testStart(self, load, get_env):
        api = PythonAPI('/test/path')
        api.start()
        load.assert_called_with('/test/path', env={'x': 0})
        get_env.assert_called_with()
        self.assertEqual(api.module, 0)
        self.assertTrue(api.started)

        load.reset_mock()
        get_env.reset_mock()
        api.do_start()
        self.assertFalse(load.called)
        self.assertFalse(get_env.called)
        self.assertEqual(api.module, 0)
