from itertools import izip

def ma_title(period):
    _24h = 2.0 * intervals._12h
    if period > _24h:
        return 'ma%.1fd' % (period * info.interval / _24h)
    return 'ma%.1fh' % (period * info.interval / intervals._1h)

def initialize():
    storage.pair = None
    for pair, value in pairs.items():
        if info.primary_pair == value:
            storage.pair = pair
    if storage.pair is None:
        log('Error: unknown pair: {0}'.format(info.primary_pair))
        raise Stop()
    storage.pair = storage.pair.split('_')

    storage.ma = [4, 8, 16]
    storage.max_ma_width = 10.0
    storage.min_price_diff = 0.5

    storage.ma_title = [
        ma_title(period) for period in storage.ma
    ]

def tick():
    price = data[info.primary_pair].close
    ma = [data[info.primary_pair].ma(period) for period in storage.ma]
    max_ma, min_ma = max(ma), min(ma)
    ma_width = max_ma - min_ma

    buy_ = False
    sell_ = False

    if ma_width < storage.max_ma_width:
        if price - max_ma > storage.min_price_diff:
            sell_ = True
        elif min_ma - price > storage.min_price_diff:
            buy_ = True

    plot('buy', int(buy_), secondary=True)
    plot('sell', int(sell_), secondary=True)
    plot('ma_width', ma_width, secondary=True)

    if buy_ and sell_:
        log('buy and sell')
        buy_ = False
        sell_ = False

    try:
        if buy_:
            buy(info.primary_pair)
        elif sell_:
            sell(info.primary_pair)
    except TradewaveFundsError:
        pass

    for title, value in izip(storage.ma_title, ma):
        plot(title, value)
