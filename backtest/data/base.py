from ..util import enum

class DataSource(object):
    CANDLE_VALUES = ['high', 'low', 'open', 'close']
    CANDLE_SIZE = len(CANDLE_VALUES)
    CANDLE = enum(CANDLE_VALUES)

    CANDLE.mean = CANDLE.high ##

    def __init__(self, start_time=None, tick_size=None):
        if start_time is None or tick_size is None:
            self.start_time = start_time
            self.tick_size = tick_size
        else:
            if start_time < 0 or tick_size <= 0:
                raise ValueError('invalid data: start_time={0} tick_size={1}'
                                 .format(start_time, tick_size))
            rem = start_time % tick_size
            self.start_time = start_time - rem
            self.tick_size = tick_size

    def __contains__(self, dataset):
        raise NotImplementedError()

    def datasets(self):
        raise NotImplementedError()

    def get_max_ticks(self, dataset=None):
        raise NotImplementedError()

    def get_current(self, tick, dataset, interval=None):
        raise NotImplementedError()

    def get_prev(self, tick, length, dataset, interval=None):
        raise NotImplementedError()
