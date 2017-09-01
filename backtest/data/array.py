from __future__ import division
import numpy as np

from .base import DataSource


class ArrayDataSource(DataSource):
    def __init__(self, data,
                 start_time=None, tick_size=None,
                 data_start_time=None, data_tick_size=None):
        if start_time is None:
            start_time = data_start_time
        if tick_size is None:
            tick_size = data_tick_size

        super(ArrayDataSource, self).__init__(start_time, tick_size)

        if data_start_time is None:
            if self.start_time is None:
                self.start_time = 0
                data_start_time = 0
            else:
                data_start_time = self.start_time

        if data_tick_size is None:
            if self.tick_size is None:
                self.tick_size = 1
                data_tick_size = 1
            else:
                data_tick_size = self.tick_size

        if data_start_time < 0 or data_tick_size <= 0:
            raise ValueError('invalid data: start_time={0} tick_size={1}'
                             .format(data_start_time, data_tick_size))

        rem = data_start_time % data_tick_size
        data_start_time -= rem

        if data_start_time > self.start_time:
            raise ValueError('data start time > start_time: {0} > {1}'
                             .format(data_start_time, self.start_time))

        if self.tick_size % data_tick_size:
            raise ValueError('tick_size ({0}) % data_tick_size ({1}) != 0'
                             .format(self.tick_size, data_tick_size))

        self.tick_multiplier = self.tick_size // data_tick_size
        self.tick_offset = (self.start_time - data_start_time) // data_tick_size
        self.data_start_time = data_start_time
        self.data_tick_size = data_tick_size
        self.data = data

    def __contains__(self, dataset):
        return dataset in self.data

    def datasets(self):
        return self.data.keys()

    def get_max_ticks(self, dataset=None):
        try:
            if dataset is None:
                length = min(len(self.data[dataset])
                             for dataset in self.datasets())
            else:
                length = len(self.data[dataset])
        except (KeyError, ValueError):
            return 0

        return (length - self.tick_offset) // self.tick_multiplier

    def _get_current(self, dataset, tick, interval):
        max_ticks = self.get_max_ticks(dataset)

        if max_ticks == 0:
            raise KeyError('dataset {0} not found'.format(dataset))
        if tick >= max_ticks:
            raise IndexError('tick {0} out of range'.format(tick))

        if interval is None:
            step = self.tick_multiplier
            offset = 0
        else:
            if interval <= 0:
                raise ValueError('invalid interval {0}'.format(interval))
            if interval % self.data_tick_size:
                raise ValueError('interval % data_tick_size != 0: {0} {1}'
                                 .format(self.data_tick_size, interval))
            step = interval // self.data_tick_size
            offset = (tick * self.tick_multiplier) % step

        start = self.tick_offset + tick * self.tick_multiplier

        if start < 0:
            raise IndexError('tick {0} out of range'.format(tick))

        return start, step, offset

    def _merge(self, data, dst):
        dst[self.CANDLE.high] = max(data[:, self.CANDLE.high])
        dst[self.CANDLE.low] = min(data[:, self.CANDLE.low])
        dst[self.CANDLE.open] = data[0, self.CANDLE.open]
        dst[self.CANDLE.close] = data[-1, self.CANDLE.close]

    def get_current(self, tick, dataset, interval=None):
        start, step, offset = self._get_current(dataset, tick, interval)
        start -= offset
        if step == 1:
            return self.data[dataset][start]
        else:
            data = self.data[dataset][start:start + step]
            ret = np.empty(self.CANDLE_SIZE, dtype=data.dtype)
            self._merge(data, ret)
            return ret

    def get_prev(self, tick, length, dataset, interval=None):
        end, step, _ = self._get_current(dataset, tick, interval)
        #end += 1
        start = end - length * step

        if start < 0:
            raise IndexError(
                'interval {0}:{1} (tick={2} length={3}) out of bounds'
                .format(start, end, tick, length)
            )

        if step == 1:
            ret = self.data[dataset][start:end:step]
        else:
            data = self.data[dataset][start:end]
            data = np.split(data, length)
            ret = np.empty((len(data), self.CANDLE_SIZE), dtype=data[0].dtype)
            for i, interval in enumerate(data):
                self._merge(interval, ret[i])

        if len(ret) != length:
            raise IndexError('get_prev {0} {1} {2} out of bounds'
                             .format(tick, length, dataset))

        return ret

    def get_plot(self, dataset, ticks=None):
        max_ticks = self.get_max_ticks(dataset)
        if ticks is None:
            ticks = max_ticks
        if ticks <= 0 or ticks > max_ticks:
            raise ValueError('invalid tick count {0}'.format(ticks))

        start, step, offset = self._get_current(dataset, 0, None)
        start += step - 1 - offset
        end = start + step * ticks

        return self.data[dataset][start:end:step, self.CANDLE.close]


class FileDataSource(ArrayDataSource):
    def __init__(self, path, start_time=None, tick_size=None):
        data_start_time, data_tick_size, data = self.load(path)
        super(FileDataSource, self).__init__(data,
                                             start_time, tick_size,
                                             data_start_time, data_tick_size)

    @staticmethod
    def load(path):
        with np.load(path) as npz:
            info = npz['info']
            data_start_time = info[0]
            data_tick_size = info[1]
            data = dict((k, v) for k, v in npz.items() if k != 'info')
            return data_start_time, data_tick_size, data
