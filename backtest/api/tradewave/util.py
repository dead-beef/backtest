from ..base import APIError, Namespace
from backtest.data import DataSource as ds

CURRENCIES = ['btc', 'ltc', 'usd', 'eur']
PAIRS = ['btc_usd', 'ltc_usd', 'ltc_btc', 'btc_eur', 'ltc_eur']
PAIR_CURRENCIES = [tuple(p.split('_')) for p in PAIRS]
EXCHANGES = ['btce', 'bitstamp', 'bitfinex', 'kraken', 'atlasats']
INTERVALS = Namespace(
    _1m=60,
    _5m=5 * 60,
    _10m=10 * 60,
    _15m=15 * 60,
    _30m=30 * 60,
    _1h=60 * 60,
    _2h=2 * 60 * 60,
    _4h=4 * 60 * 60,
    _12h=12 * 60 * 60
)
MAX_PERIOD = 250
DATA = ['open', 'high', 'low', 'close', 'volume', 'trades', 'price']
DATA_INDEX = [
    ds.CANDLE.open, ds.CANDLE.high, ds.CANDLE.low, ds.CANDLE.close,
    ds.CANDLE.close, ds.CANDLE.close, ds.CANDLE.close
]
DATA_INDEX = Namespace((data, index) for data, index in zip(DATA, DATA_INDEX))


class TradewaveDataError(APIError):
    pass

class TradewaveFundsError(APIError):
    pass

class TradewaveInvalidOrderError(APIError):
    pass
