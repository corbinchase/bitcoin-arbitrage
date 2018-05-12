import logging
import config
import time
import ast
from observers.observer import Observer
from observers.emailer import send_email
from fiatconverter import FiatConverter
import sys


class TraderBot(Observer):
    def __init__(self, exchanges):
        self.__name__ = 'TraderBot'
        # may not need exchanges
        if type(exchanges) == str:
            exchanges = ast.literal_eval(exchanges)
        # self.clients = exchanges
        self.exchanges = exchanges
        # print("observer, traderbot, TraderBot self.exchanges (the exchnages) : ", self.exchanges)
        self.fc = FiatConverter()
        self.trade_wait = 20  # in seconds
        self.last_trade = 0
        self.potential_trades = []
        self.current_pair = ''
        self.ask_market = []
        self.bid_market = []
        self.base_coin = {}
        self.quote_coin = {}
        self.volume = 0
        self.deposit_address = {}
        self.sellprice = 0
        self.buyprice = 0
        self.trade_fee = 0
        self.withdraw_fee = 0

    def begin_opportunity_finder(self, depths):
        self.potential_trades = []

    def end_opportunity_finder(self, ask_market):
        if not self.potential_trades:
            return
        print("traderbot.py, end_opportunity_finder: self.potenital_trades: {}".format(self.potential_trades))
        self.potential_trades.sort(key=lambda x: x[0])
        print("traderbot.py, end_opportunity_finder: (after lambda sort) self.potenital_trades: {}".format(self.potential_trades))

        # Execute only the best (more profitable)
        self.execute_trade(*self.potential_trades[0][1:])
        # trade has been submitted, ensure executes sucessfully
        print("TRADE EXECUTED, WAIT self.trade_wait (10) SECONDS AND THEN START CONFIRMATION SEQUENCE")
        time.sleep(self.trade_wait/2)
        if self.confirm_trade_execution(ask_market):
            pre_trade_base_volume = next(iter(self.base_coin.values()))
            pre_trade_quote_volume = next(iter(self.quote_coin.values()))
            self.update_balance(self.current_pair)
            if pre_trade_base_volume < next(iter(self.base_coin.values())) and pre_trade_quote_volume > next(iter(self.quote_coin.values())):
                print("traderbot.py, end_opportunity_finder: sucessful execution :)")
                return True
            else:
                print("traderbot.py, end_opportunity_finder: unsuccessful order")
        else:
            return False

    def complete_arbitrage(self, market):
        return self.confirm_trade_execution(market)

    # transfer funds from ask market to bid market
    ### STOPPED HERE###
    def withdraw_funds(self):
        if self.deposit_address and next(iter(self.base_coin.keys())) and self.volume:
            # TODO: pull only the latest trade volume, not complete balance
            # try:
            self.update_balance(self.current_pair)
            if next(iter(self.base_coin.values())):
                if 'tag' in self.deposit_address:
                    self.ask_market.withdraw(next(iter(self.base_coin.keys())), next(iter(self.base_coin.values())),
                                             self.deposit_address['address'], tag=self.deposit_address['tag'])
                else:
                    self.ask_market.withdraw(next(iter(self.base_coin.keys())), next(iter(self.base_coin.values())),
                                             self.deposit_address['address'])
            else:
                logging.warning("base coin value is unable to be found or is 0; expecting roughly: {}".format(self.volume))
            # except:
            #     e = sys.exc_info()[0]
            #     logging.warning("traderbot.py, withdraw_funds: Error: %s" % e)

            # self.ask_market.withdraw(next(iter(self.base_coin.keys())), self.volume, self.deposit_address)
            #  .withdraw(code, amount, address, tag=None, params={})

    def withdraw_completed(self):
        bid_market_base_coin = self.bid_market.fetchBalance()['free'][next(iter(self.base_coin.keys()))]
        if self.withdraw_fee > 0:
            # TODO: does not take trade fee into account (need to sum: trading fees + withdrawal fee + previous balance) [and make sure only
            # pulling fees for this partiuclar trade, not other open / closed trades
            # if bid_market_base_coin >= self.volume - int(self.withdraw_fee):
            if bid_market_base_coin > 0:
                logging.warning("traderbot, withdrawal has been completed!!!")
                return True
            else:
                return False
        else:
            if bid_market_base_coin > 0:
                logging.warning("traderbot, bid_market_base_coin is larger than 0; (unable to take withdrawal fee from {} into account)".format(
                    self.ask_market.id))
                return True
            else:
                logging.warning("traderbot, withdrawal_completed; DOES NOT APPEAR THAT WITHDRAW WAS COMPLETED ")
                return False

    # to sell base funds and recieve quota to complete arbitrage transaction

    def execute_base_sale(self):
        try:
            # TODO: check if current market price is higheer than expected arb opportunity; if it is, sell at market (or just below market value)
            sell_volume = self.bid_market.fetchBalance()['free'][next(iter(self.base_coin.keys()))]
            print("traderbot.py, execute_base_sale, self.base_coin: {}; volume: {}; sellprice: {}".format(next(iter(self.base_coin.keys())),
                                                                                                          sell_volume, self.sellprice))
            # TODO: sell only what has been traded, not entire balance
            self.bid_market.createLimitSellOrder(next(iter(self.base_coin.keys())), sell_volume, self.sellprice)
        except:
            e = sys.exc_info()[0]
            print("traderbot.py, execute_base_sale: Error: %s" % e)

    def confirm_trade_execution(self, market):
        open_orders = market.fetchOpenOrders(symbol=self.current_pair)     # since=undefined, limit=undefined, params={}
        if not open_orders:
            return True
        logging.warning("open orders issue in confirm_trade_execution")

        print("traderbot, confirm_trade_exeuction, order: {} on market: {}".format(open_orders, market))

        while open_orders:
            # Try to find one and only one order with the pair that we're looking for. WANRING - errors out if not exactly one match.
            relevant_orders = [d for d in open_orders if d.get('symbol') == self.current_pair]  # FIXME: could use any() / all() operating on list
            # assert len(relevant_orders) == 1, 'There is {} orders with pair {} in open orders. Expected count is 1.'.format(len(
            #     relevant_orders), self.current_pair)
            # Extract the order of interest, check its status.
            order_to_check = relevant_orders[0].copy()
            status = order_to_check.get('status')
            assert status is not None, 'Pair data missing required field (key): {}'.format(status)
            print("in while loop")
            # Figure out what we should do.
            if status == 'open':
                print("traderbot, confirm_trade_exeuction, order is still open, waiting 120 seconds for order: {}".format(open_orders))
                time.sleep(10)  # waiting 10 seconds
                open_orders = market.fetchOpenOrders(symbol=self.current_pair)
                continue
            elif status == 'closed':    # order successfully was open, closed, and trade completed
                return True
            elif status == 'canceled':
                return False  # FIXME - figure out what we want to do here.
            else:
                raise ValueError('Encountered unsupported status: {}. Currently only support "open", "closed", "canceled".'.format(status))


        # fetchOrder, fetchOrders, fetchClosedOrders
        # successful_execution = False
        # if market.has['fetchOpenOrders']:
        #     # try:
        #     open_orders = market.fetchOpenOrders(symbol=self.current_pair)     # since=undefined, limit=undefined, params={}
        #     print("traderbot, confirm_trade_exeuction, order: {} on market: {}".format(open_orders, market))
        #
        # #     while order['status'] == 'open':TypeError: list indices must be integers or slices, not str
        #     while open_orders['status'] == 'open':
        #         print("traderbot, confirm_trade_exeuction, order is still open, waiting 120 seconds for order: {}".format(open_orders))
        #         time.sleep(self.trade_wait)     # waiting 30 seconds
        #         open_order = market.fetchOpenOrders(symbol=self.current_pair)
        #
        #     if market.has['fetchClosedOrders'] or market.has['fetchClosedOrders'] == 'emulated':
        #         closed_orders = market.fetchClosedOrders(symbol=self.current_pair)
        #         if closed_orders['status'] == 'canceled':
        #             logging.warning("traderbot, confirm_trade_exeuction, order has been canceled: {}".format(closed_orders))
        #         if closed_orders['status'] == 'closed':
        #             logging.warning("!!!traderbot, confirm_trade_exeuction, order_closed has been successfully closed!: {}".format(closed_orders))
        #             successful_execution = True
        #     else:
        #         print("traderbot, confirm_trade_exeuction, order is NOT open, but market {} does not have 'fetchClosedOrders' attribute; "
        #               "setting successful_execution = True".format(market.id))
        #         successful_execution = True
        #     # except:
        #     #     e = sys.exc_info()[0]
        #     #     print("traderbot.py, confirm_trade_exeuction, can't get Order (or something else failed): Error: %s" % e)
        #
        #
        # else:
        #     # TODO: if no "fetchOpenOrders", check if base coin new balance == old balance + volume - fee
        #     logging.warning("traderbot.py, confirm_trade_exeuction, MARKET {} DOES NOT HAVE 'fetchOpenOrders' attribute - check mannually to "
        #                     "see if trade executed".format(market.id))
        # return successful_execution

    def get_min_tradeable_volume(self, buyprice, base_coin, quote_coin):
        # min1 = next(iter(arb_coin.values()[0])) / ((1 + config.balance_margin) * buyprice)  # set by maxme - (output: min1 = 0)
        min1 = next(iter(quote_coin.values())) / ((1 + config.balance_margin) * buyprice)   # calcualte max vol purchase with available quote_coin
        # min2 = next(iter(quote_coin.values())) / (1 + config.balance_margin)
        # print("min1: {:.9f}; next(iter(quote_coin.values())): {:.9f}; buyprice: {}".format(min1, next(iter(quote_coin.values())), buyprice))
        # .5 ETH/BAT
        # 10 BAT at 2 BAT/ETH
        # 5 ETH
        min2 = config.max_tx_volume / buyprice  # max quote coin to spend
        # TODO: set different thresholds for different currencies (vs. USD?)
        # logging.warning("traderbot.py, get_min_tradeable_volume: quote_coin is not BTC - have not configured maximum volume purchases from "
        #                 "non-BTC base. Check: config file. Still proceeding")
        print("buyprice {}, base_coin {}, quote_coin {}; min1: {}; min2: {}".format(buyprice, base_coin, quote_coin, min1, min2))

        return min(min1, min2)

    def get_wait_time(self, pair):
        if pair.split('/')[1] == 'BTC' or pair.split('/')[1] == 'btc':
            # TODO: check avg network congestion through API
            return 2400     # return took 10 minutes for STRAT / BTC to complete; setting to 40 minutes
        else:
            return 600      # return 10 minutes for non-BTC quote trades

    # set self.ask_market_balance & self.bid_market_balance to
    def update_balance(self, pair):
        # pair = [i.split('/') for i in pair]        # returns [['BAT', 'ETH']]
        base_coin = pair.split('/')[0]     # == BAT
        quote_coin = pair.split('/')[1]    # == ETH
        # "[base/quote]"
        # "BAT/ETH"

        # asking market = LIqui because ask price < bid price on binance = buying market

        # retrieving avialable base coin from ask market
        self.base_coin[base_coin] = self.ask_market.fetchBalance()['free'][base_coin]
        # retrieving avialable quote coin from ask market
        self.quote_coin[quote_coin] = self.ask_market.fetchBalance()['free'][quote_coin]
        # TODO: store bid_market - starting base coin so don't auto-sell everything later (sell depending on arbitrage opportunity created for that
        #  transaction

        print("ask_market: {}; available base coin {} ask_market: {}; available quote coin {} ask_market: {}"
              .format(self.ask_market.id, base_coin, self.base_coin[base_coin], quote_coin, self.quote_coin[quote_coin]))

        if next(iter(self.quote_coin.values())) == 0:
            logging.warning("Available quote coin: {:.9f}; self.quote_coin dict: {}".format(next(iter(self.quote_coin.values())), self.quote_coin))

    def opportunity(self, profit, volume, buyprice, kask, sellprice, kbid, perc, weighted_buyprice, weighted_sellprice, pair, ask_market, bid_market):
        # this is where self.current_pair is set for the first time
        self.current_pair = pair
        self.ask_market = ask_market
        self.bid_market = bid_market
        self.sellprice = sellprice
        self.buyprice = buyprice

        # print("traderbot, ask_market: {}".format(ask_market))
        # print("traderbot, bid_market: {}".format(bid_market))

        # print("traderbot.py, opportunity: profit: {}, volume: {} , buyprice: {}, kask: {}, sellprice: {}, kbid: {}, perc: {}, weighted_buyprice:
        # {}, weighted_sellprice: {}, self.exchanges: {}".format(profit, volume, buyprice, kask, sellprice, kbid, perc,
        #                                                         weighted_buyprice, weighted_sellprice, self.exchanges[0].id))
        if profit < config.profit_thresh:
            logging.verbose("[TraderBot] Profit lower than thresholds. Profit: {}; config.profit_thresh: {}".format(profit, config.profit_thresh))
            return
        if perc < config.perc_thresh:
            logging.verbose("[TraderBot] Profit percentage lower than threshold. Perc: {}; config.perc_thresh: {}".format(perc, config.perc_thresh))
            return
        # if not any([kask in c.id for c in self.exchanges]):
        if not kask == self.ask_market.id:
            logging.warn("observers, traderbot.py, opportunity (kask not in client) [TraderBot] Can't automate this trade, client not available: "
                         "%s" % kask)
            return

        # if not any([kbid in c.id for c in self.exchanges]):
        if not kbid == self.bid_market.id:
            logging.warn("observers, traderbot.py, opportunity (kbid not in client) [TraderBot] Can't automate this trade, client not available: "
                         "%s" % kbid)
            return

        # Update client balance
        self.update_balance(pair)
        print("traderbot, opportunity: buying base coin: {}, buy price: {:.9f}; selling base coin for: {}"
              .format(next(iter(self.base_coin.keys())), self.buyprice, self.sellprice))

        max_volume = self.get_min_tradeable_volume(buyprice, self.base_coin, self.quote_coin)
        print("traderbot, opportunity: volume {}; max_volume {}; {} config.max_tx_volume is {}"
              .format(volume, max_volume, next(iter(self.quote_coin.keys())), config.max_tx_volume))
        volume = min(volume, max_volume)

        if volume < config.min_tx_volume:
            logging.warn("traderbot, opportunity - Can't automate this trade, minimum volume transaction"+
                         " not reached volume: %f < config.min_tx_volume: %f" % (volume, config.min_tx_volume))
            # value = next(iter(self.base_coin.values()))  # doesn't destroy underlying dict
            logging.warn("Balance on %s: %f USD - Balance on %s: %f BTC"
                         % (kask, next(iter(self.base_coin.values())), kbid, next(iter(self.quote_coin.values()))))
            return
        current_time = time.time()
        if current_time - self.last_trade < self.trade_wait:
            logging.warn("traderbot, opportunity - [TraderBot] Can't automate this trade, last trade " +
                         "occured %.2f seconds ago" % (current_time - self.last_trade))
            return

        print("self.potential_trades.append, profit: {}, volume: {}, self.ask_market: {}, self.bid_market: {}, weighted_buyprice: {}, "
              "weighted_sellprice: {}, buyprice: {}, "
              "sellprice: {}".format(profit, volume, self.ask_market, self.bid_market, weighted_buyprice, weighted_sellprice, buyprice, sellprice))

        self.potential_trades.append([profit, volume, self.ask_market, self.bid_market, weighted_buyprice, weighted_sellprice, buyprice, sellprice])
        # self.potential_trades.append([profit, volume, kask, kbid, weighted_buyprice, weighted_sellprice, buyprice, sellprice]) # maxme

    def watch_balances(self):
        pass

    def execute_trade(self, volume, kask, kbid, weighted_buyprice, weighted_sellprice, buyprice, sellprice):
        self.last_trade = time.time()
        self.volume = volume
        try:
            self.withdraw_fee = self.ask_market.fetch_currencies()[next(iter(self.base_coin))]['fee']       # TODO: confirm fee = withdrawal fee
        except:
            logging.warning("no withdrawal_fee can be found for: {}".format(self.ask_market.id))
        logging.info(" Buy {} of {} at exchange {} and sell {}".format(volume, next(iter(self.base_coin)), kask.id, kbid.id))

        # deposit_address = self.get_wallet_address()
        # TODO: take network congestion into account
        # TODO: [WARNING] traderbot.py, withdraw_funds: Error: <class 'KeyError'> - response when coin not available for withdrawal on exchange
        if self.get_wallet_address():
            print("if self.get_wallet_address was passed, self.deposit_address: {}".format(self.deposit_address))
            self.create_buy_order(buyprice, volume)
            # self.exchanges[kask].buy(volume, buyprice)
            # self.exchanges[kbid].sell(volume, sellprice)
        else:
            print("traderbot.py, execute trade, no deposit address")

    # get address from bid market & confirm we are capable of transfering funds
    def get_wallet_address(self):
        # reset self.deposit_address to ensure no carryover from last trades
        self.deposit_address = {}
        # print("market.has: {}".format(self.bid_market.has))
        if self.bid_market.has['fetchDepositAddress']:
            try:
                self.deposit_address['address'] = self.bid_market.fetchDepositAddress(next(iter(self.base_coin.keys())))
                print("traderbot.py, get_wallet_address, self.deposit_address: {}".format(self.deposit_address))
                return True
            except:
                try:
                    print("traderbot.py, get_wallet_address, no available address, trying to create one")
                    if self.bid_market.has['createDepositAddress']:
                        self.bid_market.createDepositAddress(next(iter(self.base_coin.keys())))
                        print("traderbot.py, get_wallet_address, no available address, trying to create one - waiting 60 seconds to fetch created "
                              "address")
                        time.sleep(60)
                        self.deposit_address = self.bid_market.fetchDepositAddress(next(iter(self.base_coin.keys())))
                    # trying one more time
                    else:
                        print("traderbot.py, get_wallet_address, waiting 30 seconds before trying final time")
                        time.sleep(30)
                        self.deposit_address = self.bid_market.fetchDepositAddress(next(iter(self.base_coin.keys())))
                        print("traderbot.py, get_wallet_address, no available address self.deposit_address: {}".format(self.deposit_address))
                    if self.deposit_address:
                        print("self.deposit_address: {}".format(self.deposit_address))
                        return True
                    else:
                        return False
                except:
                    print("traderbot.py, get_wallet_address, no available address & unable to create one")
                    import sys
                    e = sys.exc_info()[0]
                    print("traderbot.py, get_wallet_address: Error: %s" % e)
                    return False
        else:
            print("market: {} doesn't have an address for coin: {}".format(self.bid_market.id, next(iter(self.base_coin.keys()))))
            return False


    # TODO: accept market order type (and limit?) ?
    def create_buy_order(self, buyprice, volume):
        import pdb; pdb.set_trace()
        print("4.0 traderbot.py, create_buy_order")
        # TODO: add try/except phrase back in - was removed so that ccxt errors could print
        # try:
            # self.ask_market.createOrder(pair, 'limit', 'buy', buyprice, volume)
            # createOrder (symbol, type, side, amount[, price[, params]])
            # createLimitBuyOrder (symbol, amount, price[, params])
        print("traderbot.py, create_buy_order on {}; buy {} amount of {} at price: {}".format(self.ask_market.id, volume, self.base_coin, buyprice))
        order_result = self.ask_market.createLimitBuyOrder(self.current_pair, volume, buyprice)

        print("traderbot.py, create_buy_order, have createdLimitBuyOrder on {}; order result: {}".format(self.ask_market.id, order_result))
        # except:
        # e = sys.exc_info()[0]
        # logging.warning("traderbot.py, create_buy_order on {} did not work: Error: {}".format(self.ask_market.id, dir(e)))

    def set_trade_fee(self, order_result):
        self.trade_fee = 0
        if order_result['trades']['cost']:
            try:
                self.trade_fee = sum([(fee.get('cost')) for fee in order_result['trades'] if fee.get('cost') is not None])

                for fee in order_result['trades']['cost']:
                    self.trade_fee += fee
                    print("self.trade_fee: {}".format(self.trade_fee))
            except:
                logging.warning("traderbot.py, set_trade_fee; unable to determine 'cost' of trade")
        elif order_result['trades']['fee']:
            try:
                for fee in order_result['trades']['fee']:
                    self.trade_fee += fee
                    print("self.trade_fee: {}".format(self.trade_fee))
            except:
                logging.warning("traderbot.py, set_trade_fee; unable to determine 'fee' of trade")
        else:
            logging.warning("traderbot.py, set_trade_fee; unable to determine 'fee' or 'cost' of trade")

    # createOrder (symbol, type, side, amount[, price[, params]])
    #     {
    #     'symbol':    'ETH/BTC',                 // symbol (base = ETH = to purchase, Quote = BTC = to sell
    #     'type':      'limit',                   // order type, 'market', 'limit' or undefined/None/null
    #     'side':      'buy',                     // direction of the trade, 'buy' or 'sell'
    #     'price':      0.06917684,               // float price in quote currency
    #     'amount':     1.5,                      // amount of base currency    (what is purchased)
    # # },

    # If you buy a currency pair, you buy the base currency and implicitly sell the quoted currency. The bid (buy price) represents how much of the
    # quote currency you need to get one unit of the base currency. Conversely, when you sell the currency pair, you sell the base currency and
    # receive the quote currency. The ask (sell price) for the currency pair represents how much you will get in the quote currency for selling
    # one unit of base currency

