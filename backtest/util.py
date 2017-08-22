from argparse import ArgumentTypeError
from time import strptime, strftime
from contextlib import contextmanager
#from itertools import islice
import sys

from tqdm import tqdm


TIME_UNIT = {
    's': 1,
    'm': 60,
    'h': 3600,
    'd': 86400
}


class Namespace(dict):
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError as err:
            raise AttributeError(err.message)

    def __setattr__(self, attr, value):
        self[attr] = value

    def __delattr__(self, attr):
        try:
            del self[attr]
        except KeyError as err:
            raise AttributeError(err.message)


class TqdmFileWrapper(object):
    def __init__(self, fp):
        self.file = fp
        self.linebuf = ''

    def write(self, x):
        #lines = (self.linebuf + x).split('\n')
        #for line in islice(lines, 0, len(lines) - 1):
        #    tqdm.write(line, file=self.file)
        #self.linebuf = lines[-1]
        try:
            i = x.rindex('\n')
            tqdm.write(self.linebuf + x[:i], file=self.file)
            self.linebuf = x[i + 1:]
        except ValueError:
            self.linebuf += x

    @classmethod
    @contextmanager
    def stdout(cls):
        sys.stdout = cls(sys.stdout)
        try:
            yield sys.stdout.file
        finally:
            sys.stdout = sys.stdout.file


def enum(names):
    return Namespace((name, i) for i, name in enumerate(names))

def parse_date(date):
    try:
        date = int(date)
        if date < 0:
            raise ArgumentTypeError('invalid date: "{0}"'.format(date))
        return date
    except ValueError:
        try:
            date = strptime(date, '%Y-%m-%d')
        except ValueError:
            try:
                date = strptime(date, '%Y-%m-%d %H:%M')
            except ValueError:
                raise ArgumentTypeError('invalid date: "{0}"'.format(date))
    return int(strftime('%s', date))

def parse_time(tm):
    if len(tm) == 0:
        raise ArgumentTypeError('invalid time: "{0}"'.format(tm))

    if not tm[-1].isdigit():
        unit = tm[-1].lower()
        tm = tm[:-1]
    else:
        unit = 's'

    try:
        tm = int(tm) * TIME_UNIT[unit]
        if tm < 0:
            raise ArgumentTypeError('invalid time: "{0}"'.format(tm))
        return tm
    except (KeyError, ValueError):
        raise ArgumentTypeError('invalid time: "{0}"'.format(tm))
