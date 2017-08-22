from unittest import TestCase
try:
    from unittest.mock import patch # pylint:disable=import-error,no-name-in-module
except ImportError:
    from mock import patch

from argparse import ArgumentTypeError
from time import strptime, strftime
from sys import exc_info

from backtest.util import (Namespace, TqdmFileWrapper,
                           enum, parse_date, parse_time)


class TestNamespace(TestCase):
    def testGetAttr(self):
        ns = Namespace(x=0)
        ns['y'] = 1
        self.assertEqual(ns.x, 0)
        self.assertEqual(ns.y, 1)
        with self.assertRaises(AttributeError):
            ns.z
        self.assertEqual(set(ns.items()), set([('x', 0), ('y', 1)]))

    def testSetAttr(self):
        ns = Namespace()
        ns.x = 0
        self.assertEqual(ns['x'], 0)
        self.assertEqual(list(ns.items()), [('x', 0)])

    def testDelAttr(self):
        ns = Namespace(x=0)
        del ns.x
        with self.assertRaises(AttributeError):
            ns.x
        self.assertEqual(list(ns.items()), [])
        with self.assertRaises(AttributeError):
            del ns.x


@patch('backtest.util.tqdm.write')
class TestTqdmFileWrapper(TestCase):
    def testInit(self, write):
        fp = TqdmFileWrapper(0)
        self.assertEqual(fp.file, 0)
        self.assertEqual(fp.linebuf, '')

    def testWrite(self, write):
        fp = TqdmFileWrapper(1)
        fp.write('123')
        self.assertEqual(write.call_count, 0)
        self.assertEqual(fp.linebuf, '123')
        fp.write('4')
        self.assertEqual(write.call_count, 0)
        self.assertEqual(fp.linebuf, '1234')
        fp.write('5\n\n6\n7 ')
        write.assert_called_with('12345\n\n6', file=1)
        self.assertEqual(fp.linebuf, '7 ')


class TestEnum(TestCase):
    def testEmpty(self):
        self.assertEqual(enum([]), Namespace())

    def test(self):
        self.assertEqual(enum(['x', 'y', 'z']), Namespace(x=0, y=1, z=2))


class TestParseDate(TestCase):
    @staticmethod
    def ts(fmt, time):
        return int(strftime('%s', strptime(time, fmt)))

    def testParse(self):
        tests = [
            ('10', 10),
            ('2016-01-01', self.ts('%Y-%m-%d', '2016-01-01')),
            ('2010-02-03 12:34', self.ts('%Y-%m-%d %H:%M', '2010-02-03 12:34'))
        ]

        for test, res in tests:
            try:
                self.assertEqual(parse_date(test), res)
            except AssertionError as err:
                raise AssertionError(err.message, test), None, exc_info()[2]

    def testParseError(self):
        tests = [
            '',
            '-1',
            '16-01-01',
            '2016-01',
            '2016-01-01 00',
            '2016-01-01 00:00:00'
        ]

        for test in tests:
            try:
                with self.assertRaises(ArgumentTypeError):
                    parse_date(test)
            except AssertionError as err:
                raise AssertionError(err.message, test), None, exc_info()[2]


class TestParseTime(TestCase):
    def testParse(self):
        tests = [
            ('10', 10),
            ('10s', 10),
            ('10S', 10),
            ('5m', 300),
            ('2h', 7200),
            ('04d', 345600),
            ('000d', 0)
        ]

        for test, res in tests:
            try:
                self.assertEqual(parse_time(test), res)
            except AssertionError as err:
                raise AssertionError(err.message, test), None, exc_info()[2]

    def testParseError(self):
        tests = [
            '',
            '10ss',
            's',
            '-1m'
        ]

        for test in tests:
            try:
                with self.assertRaises(ArgumentTypeError):
                    parse_time(test)
            except AssertionError as err:
                raise AssertionError(err.message, test), None, exc_info()[2]
