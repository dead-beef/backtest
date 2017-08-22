def initialize():
    storage.buy = True

def tick():
    if storage.buy:
        storage.buy = False
        try:
            buy(info.primary_pair)
        except TradewaveFundsError:
            pass
