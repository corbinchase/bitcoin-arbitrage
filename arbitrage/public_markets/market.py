import time
import urllib.request
import urllib.error
import urllib.parse
import logging
import sys
import config
from fiatconverter import FiatConverter
from utils import log_exception

class Market(object):
    def __init__(self, currency):
        # print("I HAVE INSTANTIATED MARKET.PY, self:", self.depth, "; CURRENCY: ", currency)
        self.name = self.__class__.__name__
        self.currency = currency
        self.depth_updated = 0
        self.update_rate = 60
        # self.depth = {'asks': [{'price': 0, 'amount': 0}], 'bids': [
        #     {'price': 0, 'amount': 0}]}
        self.fc = FiatConverter()
        self.fc.update()
        print("Market.py, __init completed")

    # def get_depth(self):
    #     timediff = time.time() - self.depth_updated
    #     if timediff > self.update_rate:
    #         print("3.1 market.py, get_depth, timediff: {}, self.update_rate: {};  ".format(timediff, self.update_rate))
    #         self.ask_update_depth()
    #     timediff = time.time() - self.depth_updated
    #     print("!!!!!! market.py, get_depth, time.time(): {}; self.depth.updated(): {}, config.market_expiration_time: {}".format(time.time(),
    #                                                                                             self.depth_updated, config.market_expiration_time))
    #     if timediff > config.market_expiration_time:
    #         print("3.2 market.py, get_depth, timediff > config.market_expiration_time")
    #         logging.warning('Market: %s order book is expired' % self.name)
    #         # TODO: Issues is with setting self.depth here - self.depth should be set in __init__
    #         self.depth = {'asks': [{'price': 0, 'amount': 0}], 'bids': [
    #             {'price': 0, 'amount': 0}]}
    #         print("3.3 market.py, get_depth, timediff > config.market_expiration_time; self.depth: ", self.depth)
    #     return self.depth

    def convert_to_usd(self):
        # print("arbitrage, public_markets, market.py, convert_to_usd()")
        if self.currency == "USD":
            print("arbitrage, public_markets, convert_to_usd, self.currency = USD")
            return
        for direction in ("asks", "bids"):
            for order in self.depth[direction]:
                # print("arbitrage, public_markets, market.py, convert_to_usd(), for loop nested")
                order["price"] = self.fc.convert(order["price"], self.currency, "USD")

    # def ask_update_depth(self):
    #     print("4.0 arbitrage, public_markets, market.py, ask_update_depth()")
    #     try:
    #         # TODO: Market' object has no attribute 'depth' (occurs here)
    #         import pdb; pdb.set_trace()
    #         print("market.py, ask_update_depth, after 1st pdb")
    #         self.update_depth()
    #         print("market.py, ask_update_depth, self.update_depth just finished")
    #         self.convert_to_usd()
    #         self.depth_updated = time.time()
    #     except (urllib.error.HTTPError, urllib.error.URLError) as e:
    #         logging.error("4.1 arbitrage, public_markets, market.py, ask_update_depth HTTPError, can't update market: %s" % self.name)
    #         log_exception(logging.DEBUG)
    #     except Exception as e:
    #         logging.error("4.2 arbitrage, public_markets, market.py, ask_update_depth(); Can't update market: %s - %s" % (self.name, str(e)))
    #         log_exception(logging.DEBUG)

    def get_ticker(self):
        # print("!!!!!!!!!!!!!!3.0 market.py, get_ticker")
        depth = self.get_depth()
        # print("3.0 market.py, get_ticker, depth: ", depth)
        res = {'ask': 0, 'bid': 0}
        if len(depth['asks']) > 0 and len(depth["bids"]) > 0:
            res = {'ask': depth['asks'][0],
                   'bid': depth['bids'][0]}
        return res

    ## Abstract methods
    def update_depth(self):
        # import pdb; pdb.set_trace()
        # print("arbitrage, market.py, update_depth, passing (self): ", self)
        pass

    def buy(self, price, amount):
        pass

    def sell(self, price, amount):
        pass