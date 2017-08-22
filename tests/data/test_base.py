from unittest import TestCase

from sys import exc_info

from backtest.data.base import DataSource


class TestDataSource(TestCase):
    def testInit(self):
        src = DataSource()
        self.assertIsNone(src.start_time)
        self.assertIsNone(src.tick_size)

        src = DataSource(start_time=8, tick_size=3)
        self.assertEqual(src.start_time, 6)
        self.assertEqual(src.tick_size, 3)

    def testError(self):
        tests = [(0, 0), (-1, 1), (1, -1)]
        for test in tests:
            try:
                with self.assertRaises(ValueError):
                    DataSource(*test)
            except AssertionError as err:
                raise AssertionError(err.message, test), None, exc_info()[2]
