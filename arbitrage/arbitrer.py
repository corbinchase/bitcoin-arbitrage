# Copyright (C) 2013, Maxime Biais <maxime@biais.org>
import ccxt
import asyncio
import time
import logging
# import json
from concurrent.futures import ThreadPoolExecutor, wait
import public_markets
import config
from public_markets import bitstampeur
from public_markets import market
import pprint


class Arbitrer(object):
    def __init__(self, depths=None):
        self.exchanges = []
        self.observers = []
        self.depths = depths
        if depths is None:
            self.depths = {}
        self.pairs = config.pairs
        self.tickers = {}
        self.ask_market = []
        self.bid_market = []
        self.pair = []
        # self.init_markets(config.markets_ccxt)
        self.limit = 10 # number of bid/ask orders to return
        # self.init_observers(config.observers)       # observers configured immediately
        self.max_tx_volume = config.max_tx_volume
        self.threadpool = ThreadPoolExecutor(max_workers=10)
        print("arbitrer.py, __init__, safeguards:: max_tx_volume: {}, min_tx_volume: {},balance_margin: {}, profit_thresh: {}, perc_thresh: {}"
              .format(config.max_tx_volume, config.min_tx_volume, config.balance_margin, config.profit_thresh, config.perc_thresh))


    def init_markets(self, args):
        self.market_names = args.markets
        # print("2. 0 arbitrer.py, init_markets, self.market_names: ", self.market_names)
        for market_name in self.market_names:
            try:
                exchange = eval('ccxt.' + market_name.lower() + '()')
                # print("arbitrer.py, init_markets, available methods (implicit & unified): ", dir(exchange))
                self.exchanges.append(exchange)
                public_api = config.market_api_keys[exchange.id + "_public"]
                secret_api = config.market_api_keys[exchange.id + "_secret"]
                # print("{} public api: {}".format(exchange.id, public_api))
                if public_api.strip() and secret_api.strip():
                    exchange.apiKey = public_api
                    exchange.secret = secret_api
                else:
                    logging.warning("No API key found for market {}".format(exchange))
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
        for observer_name in _observers:
            try:
                exec('import observers.' + observer_name.lower())
                if observer_name == "TraderBot":
                    # exec('from observers.' + observer_name.lower() + ' import ' + observer_name)
                    from observers.traderbot import TraderBot
                    # TODO: make dynamic (current brute force instantiation of TraderBot)
                    observer = TraderBot(self.exchanges)
                    # observer = eval('observers.' + observer_name.lower() + '.' + observer_name + '('+self.exchanges+')')
                else:
                    observer = eval('observers.' + observer_name.lower() + '.' + observer_name + '()')
                self.observers.append(observer)
            except (ImportError, AttributeError) as e:
                print("arbitrer.py, init_observers, failed observer: {}, is invalid: Ignored (you should check your config file), "
                      "error: {}".format(observer_name, e))

    def get_exchange_variable(self):
        return self.exchanges

    # max_vol_ask provides total volume to purchase, mi & mj should be ability to purchase/sell at index of bid/ask dicts
    def get_profit_for(self, mi, mj, kask, kbid, max_spend_ask, max_vol_ask):
        # print("test: kask: {}; kbid: {}".format(kask, kbid))
        assert kask in self.depths, "Depths is missing specified kask {} - need to remediate to continue".format(kask)
        # print("test -- self.depths[kask]['asks'][mi][0]: {}; self.depths[kbid]['bids'][mj][0]: {}".format(self.depths[kask]["asks"][mi][0],
        #                                                                                                   self.depths[kbid]["bids"][mj][0]))
        if self.depths[kask]["asks"][mi][0] >= self.depths[kbid]["bids"][mj][0]:
            # print("No arbitrage opportunity exists: asks[0] >= bids[0]")
            return 0, 0, 0, 0

        max_amount_buy = 0
        for i in range(mi + 1):
            max_amount_buy += self.depths[kask]["asks"][i][1]
        max_amount_sell = 0
        for j in range(mj + 1):
            max_amount_sell += self.depths[kbid]["bids"][j][1]

        # **** max_amount_sell = okay; max_amount_buy = okay
        max_amount = min(max_amount_buy, max_amount_sell, max_vol_ask)   # was self.max_tx_volume
        # print("arbitrer.py, get_profit_for::: max_amount_buy: {}, max_amount_sell: {}, max_amount: {}".format(max_amount_buy, max_amount_sell,
        #                                                                                                       max_amount))
        buy_total = 0
        w_buyprice = 0
        for i in range(mi + 1):
            price = self.depths[kask]["asks"][i][0]
            amount = min(max_amount, buy_total + self.depths[kask]["asks"][i][1]) - buy_total
            if amount <= 0:
                break
            buy_total += amount
            if w_buyprice == 0:
                w_buyprice = price
            else:
                w_buyprice = (w_buyprice * (buy_total - amount) + price * amount) / buy_total

        sell_total = 0
        w_sellprice = 0
        for j in range(mj + 1):
            price = self.depths[kbid]["bids"][j][0]
            amount = min(max_amount, sell_total + self.depths[kbid]["bids"][j][1]) - sell_total
            if amount < 0:
                break
            sell_total += amount
            if w_sellprice == 0 or sell_total == 0:
                w_sellprice = price
            else:
                w_sellprice = (w_sellprice * (sell_total - amount) + price * amount) / sell_total
        # TODO: profit calculated from expected BTC to USD (need to convert BTC/XXX)
        profit = sell_total * w_sellprice - buy_total * w_buyprice
        # profit = wrong (.000217); buy_total = wrong (2590.5911); sell_total = wrong (2590.599); w_buyprince = right; w_sellprice = right;
        # print("!!! max_amount_buy: {:.4f}, max_amount_sell: {:.4f}, max_amount: {:.4f}, profit: {:.4f}, buy_total: {:.4f}, sell_total: {:.4f}, "
        #       "w_buyprice: {:.9f}, w_sellprice: {:.9f}".format(max_amount_buy, max_amount_sell, max_amount, profit, buy_total, sell_total,
        #                                                      w_buyprice, w_sellprice))
        return profit, sell_total, w_buyprice, w_sellprice

    def get_max_depth(self, kask, kbid):
        i = 0
        length_kbid = len(self.depths[kbid]["bids"])
        length_kask = len(self.depths[kask]["asks"])

        # print("arbitrer.py, get_max_depth: kask: {}, kbid: {}".format(kask, kbid))

        print("arbitrer.py, get_max_depth: self.depths[kbid]['bids'][0]:: {};; self.depths[kbid]['bids'][1]: {}; length_kbid: {}, "
              "length_kask: {}".format(self.depths[kbid]["bids"][0], self.depths[kbid]["bids"][1], length_kbid, length_kask))
        max_spend_ask = 0   # in base currency
        max_spend_bid = 0   # in base currency
        max_vol_ask = 0
        max_vol_bid = 0
        temp_spend = 0
        temp_vol = 0
        ###
            # while self.depths[kask]["asks"][i]["price"] < self.depths[kbid]["bids"][0]["price"]:
            #     if i >= len(self.depths[kask]["asks"]) - 1:
            #         break
            #     i += 1
        ###
        # config max = 3
        # max_spend_ask = 1, 2, 4

        if length_kbid != 0 and length_kask != 0:
            # TODO: ensure this is accurate (might be grabbing entire depth, not just up to arbitrage opportunity)
            # maximum volume of coin purchased with avialable base currency (max btc in config file) - # TODO: max avilable balance in base currency
            while self.depths[kask]["asks"][i][0] < self.depths[kbid]["bids"][0][0]:
                max_spend_ask += (self.depths[kask]["asks"][i][0] * self.depths[kask]["asks"][i][1])
                print("max_spend_ask: ", max_spend_ask)
                max_vol_ask += self.depths[kask]["asks"][i][1]
                if max_spend_ask >= self.max_tx_volume:
                    # amount (within self.max_tx_volume
                    print("reached max tx volume (will full as much of last order as possible ) max_spend_ask: {}, max_vol_ask: {}".format(
                        max_spend_ask, max_vol_ask))
                    break
                if i >= length_kask - 1:
                    break
                i += 1
        j = 0
        if length_kbid != 0 and length_kask != 0:
            while self.depths[kask]["asks"][0][0] < self.depths[kbid]["bids"][j][0]:
                max_spend_bid += (self.depths[kbid]["bids"][j][0] * self.depths[kbid]["bids"][j][1])
                max_vol_bid += self.depths[kbid]["bids"][j][1]
                if max_spend_bid >= self.max_tx_volume:           # TODO: do we care if max spend bid is over max transaction limit?
                    print("reached max tx volume will full as much of last order as possible ) max_spend_bid: {}, max_vol_bid: {}"
                          .format(max_spend_bid, max_vol_bid))
                    break
                if j >= length_kbid - 1:
                    break
                j += 1
        print("arbitrer.py, get_max_depth::: max_spend_ask: {}, max_spend_bid: {}, max_vol_ask: {}, max_vol_bid:{} ".format(max_spend_ask,
                                                                                                                            max_spend_bid,
                                                                                                                            max_vol_ask,
                                                                                                                            max_vol_bid))
        return i, j, max_spend_ask, max_vol_ask

    def arbitrage_depth_opportunity(self, kask, kbid):
        maxi, maxj, max_spend_ask, max_vol_ask = self.get_max_depth(kask, kbid)
        print("arbitrer.py, arbitrage_DEPTH_opportunity, maxi (kask): {}; maxj (kbid): {}".format(maxi, maxj))
        ### TODO: #### ensure calculating "best_profit" correctly (currently doesn't take not fully complete orders into account (if next order is
        # 10btc, but can only fill a portion, profit calculated off of entire fill)
        best_profit = 0
        best_i, best_j = (0, 0)
        best_w_buyprice, best_w_sellprice = (0, 0)
        best_volume = 0
        # print("arbitrer, arbitrage_depth_opportunity: \n kask: {}, \n kbid: {}, \n max_spend_ask: {}, \n max_vol_ask: {}".
        #       format(kask, kbid, max_spend_ask, max_vol_ask))
        for i in range(maxi + 1):
            for j in range(maxj + 1):
                #  mi (ask) and mj (bid) - should be length of depth
                profit, volume, w_buyprice, w_sellprice = self.get_profit_for(i, j, kask, kbid, max_spend_ask, max_vol_ask)
                if profit >= 0 and profit >= best_profit:
                    best_profit = profit
                    best_volume = volume
                    best_i, best_j = (i, j)
                    best_w_buyprice, best_w_sellprice = (w_buyprice, w_sellprice)
        print("arbitrage_depth_opportunity, best_i: {}, best_j: {}; best_profit: {}, best_volume: {}"
              .format(best_i, best_j, best_profit, best_volume))
        return best_profit, best_volume, self.depths[kask]["asks"][best_i][0], self.depths[kbid]["bids"][best_j][0], best_w_buyprice, best_w_sellprice

    # setting global bid and ask markets so we can easily send to observers
    def set_ask_and_bid_markets(self, kask, kbid):
        for exchange in self.exchanges:
            # print("KASK: {}; KBID: {}; exchange: {}".format(kask, kbid, exchange))
            if kask == str(exchange.id):
                self.ask_market = exchange
                print("arbitrer.py, set_ask_and_bid_markets; kask -- self.ask_market: {}".format(self.ask_market))
            if kbid == str(exchange.id):
                self.bid_market = exchange
                print("arbitrer.py, set_ask_and_bid_markets; kbid -- self.bid_market: {}".format(self.bid_market))

    def arbitrage_opportunity(self, kask, ask, kbid, bid):
        # perc = (bid["price"] - ask["price"]) / bid["price"] * 100   # original

        self.set_ask_and_bid_markets(kask, kbid)

        perc = (bid[0] - ask[0]) / bid[0] * 100
        profit, volume, buyprice, sellprice, weighted_buyprice, weighted_sellprice = self.arbitrage_depth_opportunity(kask, kbid)

        if volume == 0 or buyprice == 0:
            return
        perc2 = (1 - (volume - (profit / buyprice)) / volume) * 100
        print("arbitrage_opportunity. profit: {}, volume: {}, buyprice: {}, kask: {}, sellprice: {}, kbid: {}, perc2: {}, "
              "weighted_buyprice: {}, weighted_sellprice: {}".format(profit, volume, buyprice, kask, sellprice, kbid, perc2, weighted_buyprice,
                                                                     weighted_sellprice))
        pair = self.pair
        for observer in self.observers:
            print("arbiter.py, arbitrage_opportunity, pair: {}".format(pair))
            observer.opportunity(
                profit, volume, buyprice, kask, sellprice, kbid,
                perc2, weighted_buyprice, weighted_sellprice, pair, self.ask_market, self.bid_market)

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
            # TODO: get list of pairs from exchanges ? - or list pair combinations by exchange in config?
            for pair in self.pairs:

                # exmample badass code
                # [i.split('/', 1) for i in pair]
                # map(lambda x: x.split(), pair.split(','))
                # [x for xs in lst for x in xs.split(',')]

                # print("arbitrer.updatedepths, pair.split(/): {}".format(pair.split('/')))

                # TODO: make sure we actually need self.pair (may just need bid_coin & ask_coin)
                self.pair = pair
                try:
                    # self.depths[exchange.id][pair] = exchange.fetch_order_book(pair)
                    self.depths[exchange.id] = exchange.fetch_order_book(pair)
                except Exception as e:
                    logging.log(20, "arbitrer.py, update_depths, Can't get exchange: {}, pair: {}, ticker. Error: ".format(exchange.id, pair,
                                                                                                                           str(e)))
        wait(futures, timeout=20)
        return depths

    def get_tickers(self):
        # print("arbitrer.py, tickers, self.exchanges: ", self.exchanges)
        for exchange in self.exchanges:
            # self.market_ticker = market.Market(exchange) ########### need to uncomment this out to access Market
            for pair in config.pairs:
                try:
                    # all tickers at once: print("!!!TICKERS: ", exchange.fetch_tickers())
                    self.tickers[pair] = exchange.fetch_ticker(pair)
                    # print("arbitrer.py, get_tickers: on exchange {}, ticker for pair {} is: {}".format(exchange, pair, self.tickers[pair]))
                except Exception as e:
                    logging.log(20, "arbitrer.py, get_tickers, Can't get exchange: {}, pair: {}, ticker. Error: ".format(exchange.id, pair, str(e)))
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
        # print("arbitrer.py, tick")
        for observer in self.observers:
            # print("arbitrer.py, tick, observer: ", observer)
            observer.begin_opportunity_finder(self.depths)
        # self.depths is structured okay here
        for kmarket1 in self.depths:
            # print("arbitrage.py, tick, kmarket1: ", kmarket1)       # loop 1, kmarket1 = binance;
            for kmarket2 in self.depths:
                # print("arbitrage.py, tick, nested for loop - kmarket1: ", kmarket1)       # loop 1, kmarket1 = binance;
                # print("arbitrage.py, tick, kmarket2: ", kmarket2)       # output is "binance", "poloniex", "binance"
                # print("arbitrage.py, tick, self.depths[kmarket2]", self.depths[kmarket2])
                # print("arbitrage.py, tick, self.depths: ", self.depths)
                if kmarket1 == kmarket2:  # same market; Continue == jumps to next for loop
                    continue
                #   something is wrong with market1 & market2 - redundany in bid/ask books
                market1 = self.depths[kmarket1]     # loop1, market1 (bids[0]): [0.0003283, 51.32], [0.0003275, 61.06]; loop1 market2 (bids[0]): [0.00030564, 50.0]
                market2 = self.depths[kmarket2]
                # print("arbitrer.py, tick, !!!!! at end of nested for loop")
                # print("arbitrer.py, tick, market1 {}; \n \n market 2 {}".format(market1, market2))
                # TODO: bid/ask is marketX['bid'][0][0]; depth is marketX['bid'][0][1]; ensure this logic is solid - otherwise could switch bid/ask
                #  markets
                print("kmarket1: {}, kmarket2: {}".format(kmarket1, kmarket2))
                if market1["asks"] and market2["bids"] and len(market1["asks"]) > 0 and len(market2["bids"]) > 0:
                    if float(market1["asks"][0][0]) < float(market2["bids"][0][0]):
                        print("&& market1['asks'][0]: {} \n&& market2['bids][0]: {}".format(market1["asks"][0][0], market2["bids"][0][0]))
                        self.arbitrage_opportunity(kmarket1, market1["asks"][0], kmarket2, market2["bids"][0])

        # identify opportunites, execute trades, execute transfer of funds
        for observer in self.observers:
            # close identification of opportunity and execute trade
            successful_execution = observer.end_opportunity_finder()
            if successful_execution:
                observer.withdraw_funds()
                # TODO: check that exact balance has been sucessfully added (not just that balance >= volume)
                while not observer.withdrawal_completed():
                    print("arbitrer.py, tick, withdrawal not complete, waiting 20 seconds")
                    time.sleep(20)
                observer.execute_base_sale() # execute sale of transfered funds
            else:
                logging.warning("arbitrer.py, tick, not successful execution")

    def loop(self):
        while True:
            self.update_depths()
            self.get_tickers()
            self.tick()
            time.sleep(config.refresh_rate)
