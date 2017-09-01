from unittest import TestCase

from tempfile import mkstemp
from os import remove, close
from sys import exc_info
import numpy as np
from numpy.testing import assert_array_equal

from backtest.data.array import ArrayDataSource, FileDataSource


class TestArrayDataSource(TestCase):
    data = {
        'dataset0': np.array([
            range(4), range(4, 8), range(8, 12),
            range(12, 16), range(16, 20), range(20, 24),
            range(24, 28), range(28, 32)
        ]),
        'dataset1': np.array([
            range(1, 5), range(5, 9), range(9, 13),
            range(13, 17), range(17, 21)
        ])
    }

    def testInitDefault(self):
        src = ArrayDataSource(self.data)
        self.assertIs(src.data, self.data)
        self.assertEqual(src.tick_offset, 0)
        self.assertEqual(src.tick_multiplier, 1)
        self.assertEqual(src.start_time, 0)
        self.assertEqual(src.tick_size, 1)
        self.assertEqual(src.data_start_time, src.start_time)
        self.assertEqual(src.data_tick_size, src.tick_size)

    def testInit(self):
        tests = [
            ((self.data, 8, 4, 2, 2), (3, 2, 8, 4, 2, 2)),
            ((self.data, 10, 4, 3, 2), (3, 2, 8, 4, 2, 2)),
            ((self.data, None, None, 5, 2), (0, 1, 4, 2, 4, 2)),
            ((self.data, 10, 4, None, None), (0, 1, 8, 4, 8, 4)),
            ((self.data, None, None, None, None), (0, 1, 0, 1, 0, 1))
        ]

        for test, res in tests:
            try:
                src = ArrayDataSource(*test)
                self.assertIs(src.data, test[0])
                self.assertEqual(src.tick_offset, res[0])
                self.assertEqual(src.tick_multiplier, res[1])
                self.assertEqual(src.start_time, res[2])
                self.assertEqual(src.tick_size, res[3])
                self.assertEqual(src.data_start_time, res[4])
                self.assertEqual(src.data_tick_size, res[5])
            except AssertionError as err:
                raise AssertionError(err.message, test, res), \
                      None, exc_info()[2]

    def testInitError(self):
        tests = [
            (self.data, 0, 1, 1, 1),
            (self.data, 0, 1, 0, -1),
            (self.data, 0, 2, 0, 3),
            (self.data, 0, 3, 0, 2)
        ]
        for test in tests:
            try:
                with self.assertRaises(ValueError):
                    ArrayDataSource(*test)
            except AssertionError as err:
                raise AssertionError(err.message, test), None, exc_info()[2]

    def testContains(self):
        src = ArrayDataSource(self.data)
        self.assertTrue('dataset0' in src)
        self.assertTrue('dataset1' in src)
        self.assertFalse('dataset2' in src)

    def testGetDatasets(self):
        src = ArrayDataSource(self.data)
        self.assertEqual(set(src.datasets()), set(['dataset0', 'dataset1']))

    def testGetMaxTicks(self):
        src = ArrayDataSource(self.data)
        self.assertEqual(src.get_max_ticks('dataset0'), 8)
        self.assertEqual(src.get_max_ticks('dataset1'), 5)
        self.assertEqual(src.get_max_ticks('dataset2'), 0)
        self.assertEqual(src.get_max_ticks(), 5)

        src.tick_offset = 1
        src.tick_multiplier = 2
        self.assertEqual(src.get_max_ticks('dataset0'), 3)
        self.assertEqual(src.get_max_ticks('dataset1'), 2)
        self.assertEqual(src.get_max_ticks(), 2)

        src = ArrayDataSource({})
        self.assertEqual(src.get_max_ticks(), 0)

    def testGetCurrent(self):
        src = ArrayDataSource(self.data)
        assert_array_equal(
            src.get_current(1, 'dataset0'),
            self.data['dataset0'][1]
        )
        assert_array_equal(
            src.get_current(2, 'dataset1'),
            self.data['dataset1'][2]
        )
        src.tick_offset = 1
        src.tick_multiplier = 2
        assert_array_equal(src.get_current(1, 'dataset0'), [16, 13, 14, 19])

    def testGetCurrentError(self):
        tests = [
            (-1, 'dataset0', None),
            (0, 'dataset0', 3),
            (0, 'dataset0', 0),
            (len(self.data['dataset0']), 'dataset0', None),
            (0, 'dataset2', None)
        ]

        src = ArrayDataSource(self.data, tick_size=2)

        for test in tests:
            try:
                with self.assertRaises((KeyError, ValueError, IndexError)):
                    src.get_current(*test)
            except AssertionError as err:
                raise AssertionError(err.message, test), None, exc_info()[2]

    def testGetCurrentInterval(self):
        src = ArrayDataSource(self.data, tick_size=2)
        assert_array_equal(
            src.get_current(1, 'dataset0', interval=2),
            self.data['dataset0'][1]
        )
        assert_array_equal(
            src.get_current(1, 'dataset0', interval=4),
            [4, 1, 2, 7]
        )
        assert_array_equal(
            src.get_current(2, 'dataset0', interval=4),
            [12, 9, 10, 15]
        )

    def testGetPrev(self):
        src = ArrayDataSource(self.data)
        assert_array_equal(
            src.get_prev(3, 2, 'dataset0'),
            self.data['dataset0'][1:3]
        )
        assert_array_equal(
            src.get_prev(4, 3, 'dataset1'),
            self.data['dataset1'][1:4]
        )
        src.tick_offset = 1
        src.tick_multiplier = 2
        assert_array_equal(
            src.get_prev(2, 2, 'dataset0'),
            [[8, 5, 6, 11], [16, 13, 14, 19]]
        )

    def testGetPrevInterval(self):
        src = ArrayDataSource(self.data, tick_size=2)
        assert_array_equal(
            src.get_prev(3, 2, 'dataset0', interval=2),
            self.data['dataset0'][1:3]
        )
        assert_array_equal(
            src.get_prev(7, 3, 'dataset0', interval=4),
            [[8, 5, 6, 11], [16, 13, 14, 19], [24, 21, 22, 27]]
        )
        assert_array_equal(
            src.get_prev(5, 1, 'dataset0', interval=6),
            [[16, 9, 10, 19]]
        )

    def testGetPrevError(self):
        tests = [
            (-1, 1, 'dataset0', None),
            (0, 1, 'dataset0', 3),
            (0, 1, 'dataset0', 0),
            (len(self.data['dataset0']), 1, 'dataset0', None),
            (1, 1, 'dataset2', None),
            (1, 1, 'dataset0', 4),
            (2, 4, 'dataset0', None)
        ]

        src = ArrayDataSource(self.data, tick_size=2)

        for test in tests:
            try:
                with self.assertRaises((KeyError, ValueError, IndexError)):
                    src.get_prev(*test)
            except AssertionError as err:
                raise AssertionError(err.message, test), None, exc_info()[2]


class TestFileDataSource(TestCase):
    @classmethod
    def setUpClass(cls):
        fd, cls.fname = mkstemp(suffix='.npz')
        close(fd)
        cls.x = np.array(range(10))
        cls.y = np.array(range(10, 20))
        info = np.array([6, 4])
        np.savez(cls.fname, x=cls.x, y=cls.y, info=info)

    @classmethod
    def tearDownClass(cls):
        remove(cls.fname)

    def testInit(self):
        src = FileDataSource(self.fname, start_time=9, tick_size=8)
        self.assertEqual(src.data_start_time, 4)
        self.assertEqual(src.data_tick_size, 4)
        self.assertEqual(src.tick_offset, 1)
        self.assertEqual(src.tick_multiplier, 2)
        self.assertEqual(list(sorted(src.data.keys())), ['x', 'y'])
        assert_array_equal(src.data['x'], self.x)
        assert_array_equal(src.data['y'], self.y)

        src = FileDataSource(self.fname)
        self.assertEqual(src.start_time, 4)
        self.assertEqual(src.tick_size, 4)

    def testInitError(self):
        with self.assertRaises(ValueError):
            FileDataSource(self.fname, start_time=1, tick_size=8)

        with self.assertRaises(ValueError):
            FileDataSource(self.fname, start_time=8, tick_size=9)
