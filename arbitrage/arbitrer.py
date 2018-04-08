# Copyright (C) 2013, Maxime Biais <maxime@biais.org>
import ccxt
import asyncio
import time
import logging
# import json
from concurrent.futures import ThreadPoolExecutor, wait
import observers
import public_markets
import config
from public_markets import bitstampeur
from public_markets import market
import pprint


############################ USE "SELF.XXX" for methods, and "self.YYY" for variables used in the class ############################
class Arbitrer(object):
    def __init__(self):
        self.exchanges = []
        self.observers = []
        self.depths = {}
        self.pairs = config.pairs
        self.tickers = {}
        # self.init_markets(config.markets_ccxt)
        self.limit = 5 # number of bid/ask orders to return
        self.init_observers(config.observers)
        self.max_tx_volume = config.max_tx_volume
        self.threadpool = ThreadPoolExecutor(max_workers=10)


    def init_markets(self, args):
        self.market_names = args.markets
        print("2. 0 arbitrer.py, init_markets, self.market_names: ", self.market_names)
        for market_name in self.market_names:
            try:
                exchange = eval('ccxt.' + market_name.lower() + '()')
                # print("arbitrer.py, init_markets, available methods (implicit & unified): ", dir(exchange))
                self.exchanges.append(exchange)
                public_api = config.market_api_keys[exchange.id + "_public"]
                secret_api = config.market_api_keys[exchange.id + "_secret"]
                print("{} public api: {}".format(exchange.id, public_api))
                if public_api.strip() and secret_api.strip():
                    exchange.apiKey = public_api
                    exchange.secret = secret_api
                else:
                    logging.warning("arbitrer.py, init_markets, !!! no API key found for market {}".format(exchange))
            except (ImportError, AttributeError) as e:
                print("ERROR (arbitrer.py, init_markets): Market name {} is invalid. ERROR: {}".format(market_name, e))
        # print("2.1 arbitrer.py, init_markets, initalized all markets, self.exchanges: ", self.exchanges)
        return self.exchanges


    # TODO: Original code
    #     for market_name in markets:
    #         try:
    #             print("7.0 arbitrer.py, init_markets, public_markets:" + market_name.lower())
    #             exec('import public_markets.'+market_name.lower(), globals())
    #             market = eval('public_markets.' + market_name.lower() + '.' + market_name + '()')
    #             self.exchanges.append(market)
    #         except (ImportError, AttributeError) as e:
    #             print("ERROR (arbitrer.py, init_markets): Market name {} is invalid: Ignored (you should check your config file). {}".format(
    #                 market_name, e))

    def init_observers(self, _observers):
        self.observer_names = _observers
        for observer_name in _observers:
            # print("4.0 arbitrer.py, init_observers, self.observers_names: ", self.observer_names)
            try:
                exec('import observers.' + observer_name.lower())
                observer = eval('observers.' + observer_name.lower() + '.' +
                                observer_name + '()')
                self.observers.append(observer)
            except (ImportError, AttributeError) as e:
                print("arbitrer.py, init_observers, failed observer init: ", e)
                print("%s observer name is invalid: Ignored (you should check your config file)" % observer_name)

    def get_profit_for(self, mi, mj, kask, kbid):
        print("arbitrer.py, get_profit_for()")
        if self.depths[kask]["asks"][mi][0] >= self.depths[kbid]["bids"][mj][0]:
            return 0, 0, 0, 0
        max_amount_buy = 0
        for i in range(mi + 1):
            max_amount_buy += self.depths[kask]["asks"][i][1]
        max_amount_sell = 0
        for j in range(mj + 1):
            max_amount_sell += self.depths[kbid]["bids"][j][1]
        max_amount = min(max_amount_buy, max_amount_sell, self.max_tx_volume)

        buy_total = 0
        w_buyprice = 0
        for i in range(mi + 1):
            price = self.depths[kask]["asks"][i][0]
            amount = min(max_amount, buy_total + self.depths[
                kask]["asks"][i][1]) - buy_total
            if amount <= 0:
                break
            buy_total += amount
            if w_buyprice == 0:
                w_buyprice = price
            else:
                w_buyprice = (w_buyprice * (
                        buy_total - amount) + price * amount) / buy_total

        sell_total = 0
        w_sellprice = 0
        for j in range(mj + 1):
            price = self.depths[kbid]["bids"][j][0]
            amount = min(max_amount, sell_total + self.depths[
                kbid]["bids"][j][1]) - sell_total
            if amount < 0:
                break
            sell_total += amount
            if w_sellprice == 0 or sell_total == 0:
                w_sellprice = price
            else:
                w_sellprice = (w_sellprice * (
                        sell_total - amount) + price * amount) / sell_total

        profit = sell_total * w_sellprice - buy_total * w_buyprice
        return profit, sell_total, w_buyprice, w_sellprice

    def get_max_depth(self, kask, kbid):
        print("arbitrer.py, get_max_depth: kask: {}, kbid: {}".format(kask, kbid))
        i = 0
        if len(self.depths[kbid]["bids"][1]) != 0 and len(self.depths[kask]["asks"][1]) != 0:
            while self.depths[kask]["asks"][i][0] < self.depths[kbid]["bids"][0][0]:
                if i >= len(self.depths[kask]["asks"][1]) - 1:
                    break
                i += 1
        j = 0
        if len(self.depths[kask]["asks"][1]) != 0 and len(self.depths[kbid]["bids"][1]) != 0:
            while self.depths[kask]["asks"][0][0] < self.depths[kbid]["bids"][j][0]:
                if j >= len(self.depths[kbid]["bids"][1]) - 1:
                    break
                j += 1
        return i, j

    def arbitrage_depth_opportunity(self, kask, kbid):
        print("arbitrer.py, arbitrage_DEPTH_opportunity, kask: {}, kbid: {}".format(kask, kbid))
        maxi, maxj = self.get_max_depth(kask, kbid)
        best_profit = 0
        best_i, best_j = (0, 0)
        best_w_buyprice, best_w_sellprice = (0, 0)
        best_volume = 0
        for i in range(maxi + 1):
            for j in range(maxj + 1):
                profit, volume, w_buyprice, w_sellprice = self.get_profit_for(
                    i, j, kask, kbid)
                if profit >= 0 and profit >= best_profit:
                    best_profit = profit
                    best_volume = volume
                    best_i, best_j = (i, j)
                    best_w_buyprice, best_w_sellprice = (
                        w_buyprice, w_sellprice)
        return best_profit, best_volume, \
               self.depths[kask]["asks"][best_i][0], \
               self.depths[kbid]["bids"][best_j][0], \
               best_w_buyprice, best_w_sellprice

    def arbitrage_opportunity(self, kask, ask, kbid, bid):
        # perc = (bid["price"] - ask["price"]) / bid["price"] * 100   # original
        print("arbitrer.py, arbitrage_opportunity, kask: {}, ask: {}, kbid: {}, bid: {}".format(kask, ask, kbid, bid))
        perc = (bid[0] - ask[0]) / bid[0] * 100
        profit, volume, buyprice, sellprice, weighted_buyprice, weighted_sellprice = self.arbitrage_depth_opportunity(kask, kbid)
        if volume == 0 or buyprice == 0:
            return
        perc2 = (1 - (volume - (profit / buyprice)) / volume) * 100
        for observer in self.observers:
            observer.opportunity(
                profit, volume, buyprice, kask, sellprice, kbid,
                perc2, weighted_buyprice, weighted_sellprice)

    # def __get_market_depth(self, exchange, depths):
    #     # Corbin writing here_____
    #     for pair in self.pairs:
    #         self.depths[exchange.id] = exchange.fetch_order_book(pair, self.limit)
    #     # print("arbiter.py, __get_market_depth - out of for loop, depths[binance]: ", depths['binance'])
    #     # depths[market.name] = market.get_depth() #OG

    def update_depths(self):
        depths = {}
        futures = []
        for exchange in self.exchanges:
            # TODO: threadpool -- this is where the error starts - future error: Future at 0x102230908 state=finished raised AttributeError
            # futures.append(self.threadpool.submit(self.__get_market_depth, market, depths))       # TODO: re-introduce threading
            # self.__get_market_depth(exchange, depths)
            self.depths[exchange.id] = exchange.fetch_order_book(config.base_pair)
            print("arbitrer.py, update_depths, len(self.depths): ", len(self.depths))
        wait(futures, timeout=20)
        return depths

    def get_tickers(self):
        print("arbitrer.py, tickers, self.exchanges: ", self.exchanges)
        for exchange in self.exchanges:
            # self.market_ticker = market.Market(exchange) ########### need to uncomment this out to access Market
            for pair in config.pairs:
                try:
                    # all tickers at once: print("!!!TICKERS: ", exchange.fetch_tickers())
                    self.tickers[pair] = exchange.fetch_ticker(pair)
                    print("on exchange {}, ticker for pair {} is: {}".format(exchange, pair, self.tickers[pair]))
                except Exception as e:
                    logging.warning("arbitrer.py, get_tickers, Can't get exchange: {}, pair: {}, ticker. Error: ".format(exchange.id, pair, str(e)))
            # logging.verbose("ticker: " + exchange.id + " - " + str(exchange.get_ticker()))
            # logging.verbose("ticker: " + market.fetchTicker())
            # logging.verbose("ticker: " + market().keys())

    def replay_history(self, directory):
        import os
        import json
        files = os.listdir(directory)
        files.sort()
        for f in files:
            depths = json.load(open(directory + '/' + f, 'r'))
            self.depths = {}
            for market in self.market_names:
                if market in depths:
                    self.depths[market] = depths[market]
            self.tick()

    def tick(self):
        print("arbitrer.py, tick")
        for observer in self.observers:
            observer.begin_opportunity_finder(self.depths)

        for kmarket1 in self.depths:
            print("kmarket1: ", kmarket1)
            for kmarket2 in self.depths:
                print("kmarket2", kmarket2)
                if kmarket1 == kmarket2:  # same market
                    print("same market")
                    continue
                market1 = self.depths[kmarket1]
                market2 = self.depths[kmarket2]
                print("arbitrer.py, tick, market1 {}; \n \n market 2 {}".format(market1, market2))
                # TODO: bid/ask is marketX['bid'][0][0]; depth is marketX['bid'][0][1]
                if market1["asks"] and market2["bids"] and len(market1["asks"]) > 0 and len(market2["bids"]) > 0:
                    print("arbitrer.py, tick, len(market 1['asks']): {}; len(market 2['bids']): {}".format(len(market1["asks"]),len(market2["bids"])))
                    # if float(market1["asks"][0]['price']) < float(market2["bids"][0]['price']): ## original
                    if float(market1["asks"][0][0]) < float(market2["bids"][0][0]):
                        print("!!!arbitrer.py, tick, - passed second if statement ")
                        # passing arbitrage_opportunity adk/bid[0]: [price, depth]
                        self.arbitrage_opportunity(kmarket1, market1["asks"][0], kmarket2, market2["bids"][0])

        for observer in self.observers:
            observer.end_opportunity_finder()

    def loop(self):
        while True:
            print("arbitrer.py, loop, just started loop")

            self.update_depths()
            # self.depths = self.update_depths()
            print("arbitrer.py, loop, len(self.depths):", len(self.depths), "; running self.tickers")
            self.get_tickers()
            print("arbitrer.py, loop, ran self.get_tickers, running self.tick")
            self.tick()
            print("arbitrer.py, loop, ran self.tick, running self.sleep")
            time.sleep(config.refresh_rate)
