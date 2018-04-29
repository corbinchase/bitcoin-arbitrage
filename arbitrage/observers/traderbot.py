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
        # may not need exchanges
        if type(exchanges) == str:
            exchanges = ast.literal_eval(exchanges)
        # self.clients = exchanges
        self.exchanges = exchanges
        print("observer, traderbot, TraderBot self.exchanges (the exchnages) : ", self.exchanges)
        self.fc = FiatConverter()
        self.trade_wait = 120  # in seconds
        self.last_trade = 0
        self.potential_trades = []
        self.pair = []
        self.ask_market = []
        self.bid_market = []
        self.base_coin = {}
        self.quote_coin = {}
        self.volume = 0
        self.deposit_address = {}
        self.sellprice = ''
        self.buyprice = ''

    def begin_opportunity_finder(self, depths):
        self.potential_trades = []

    def end_opportunity_finder(self):
        if not self.potential_trades:
            return
        print("traderbot.py, end_opportunity_finder: self.potenital_trades: {}".format(self.potential_trades))
        self.potential_trades.sort(key=lambda x: x[0])

        # Execute only the best (more profitable)
        self.execute_trade(*self.potential_trades[0][1:])
        # trade has been submitted, ensure executes sucessfully
        successful_execution = self.confirm_trade_execution()
        if successful_execution:
            print("sucessful execution :)")
        return successful_execution

    # transfer funds from ask market to bid market
    def withdraw_funds(self):
        if self.deposit_address and self.base_coin and self.volume:
            try:
                self.ask_market.withdraw(self.base_coin, self.volume, self.deposit_address['address'], tag=self.deposit_address['tag'])
            except:
                e = sys.exc_info()[0]
                logging.warning("traderbot.py, withdraw_funds: Error: %s" % e)

            # self.ask_market.withdraw(self.base_coin, self.volume, self.deposit_address)
            #  .withdraw(code, amount, address, tag=None, params={})

    def withdrawal_completed(self):
        bid_market_base_coin = self.bid_market.fetchBalance()['free'][self.base_coin]
        if bid_market_base_coin >= self.volume:
            logging.warning("traderbot, withdrawal has been completed!!!")
            return True
        else:
            return False

    # to sell base funds and recieve quota to complete arbitrage transaction
    # TODO: stopped right here
    def execute_base_sale(self):
        try:
            print("traderbot.py, execute_base_sale, self.base_coin: {}; volume: {}; sellprice: {}".format(next(iter(self.base_coin.keys())),
                                                                                                          self.volume, self.sellprice))
            self.bid_market.createLimitSellOrder(next(iter(self.base_coin.keys())), self.volume, self.sellprice)
        except:
            e = sys.exc_info()[0]
            print("traderbot.py, execute_base_sale: Error: %s" % e)

    def confirm_trade_execution(self):
        # fetchOrder, fetchOrders, fetchClosedOrders
        successful_execution = None
        if (self.ask_market.has['fetchOpenOrders']):
            order = self.ask_market.fetchOpenOrders(symbol=self.pair)     # since=undefined, limit=undefined, params={}
            if not order:
                logging.warning("traderbot, confirm_trade_exeuction, order == empty; order has successfully completed or order retrieval didn't work")
            else:
                try:
                    while order['status'] == 'open':
                        time.sleep(self.trade_wait)
                        order = self.ask_market.fetchOpenOrders(symbol=self.pair)
                        logging.warning("traderbot, confirm_trade_exeuction, order is still open, order: {}".format(order))
                    if (self.ask_market.has['fetchClosedOrders']):
                        order = self.ask_market.fetchClosedOrders(symbol=self.pair)
                        if order['status'] == 'canceled':
                            logging.warning("traderbot, confirm_trade_exeuction, order has been canceled: {}".format(order))
                        if order['status'] == 'closed':
                            logging.warning("!!!!!traderbot, confirm_trade_exeuction, order has been closed!!!!!!!!: {}".format(order))
                            successful_execution = True
                except:
                    e = sys.exc_info()[0]
                    print("traderbot.py, confirm_trade_exeuction: Error: %s" % e)
        return successful_execution
        # self.ask_market.fetchOrder()

    def get_min_tradeable_volume(self, buyprice, arb_coin, quote_coin):
        # min1 = next(iter(arb_coin.values()[0])) / ((1 + config.balance_margin) * buyprice)  # set by maxme - (output: min1 = 0)
        min1 = next(iter(quote_coin.values())) / ((1 + config.balance_margin) * buyprice)   # calcualte max vol purchase with available quote_coin
        # min2 = next(iter(quote_coin.values())) / (1 + config.balance_margin)

        # check if quote_coin is BTC; if not BTC, identify converstion of BTC and quote_coin; calculate buyprice in terms of BTC; ensure min2 <
        if next(iter(quote_coin.keys())) == 'BTC':
            min2 = config.max_tx_volume / buyprice  # calcualte max volume to purchase from BTC
            # print("min2: {}".format(min2))
        else:
            # TODO: if not BTC base, convert and ensure not trading above BTC max_tx_ volume threshold in config file
            logging.warning("quote_coin is not BTC - have not configured maximum volume purchases from non-BTC base. Check: traderbot.py, "
                            "get_min_tradeable_volume")
        # print("buyprice {}, arb_coin {}, quote_coin {}; min1: {}; min2: {}".format(buyprice, arb_coin, quote_coin, min1, min2))   # buyprice

        return min(min1, min2)

    # set self.ask_market_balance & self.bid_market_balance to
    def update_balance(self, pair):
        pair = pair.split('/')
        k1 = pair[0]
        k2 = pair[1]

        # retrieving avialable base coin and arbitragin coin from ask market
        self.base_coin[k1] = self.ask_market.fetchBalance()['free'][k1]
        self.quote_coin[k2] = self.bid_market.fetchBalance()['free'][k2]

        print("ask_market market: {} available quote coin: {}".format(self.ask_market, self.quote_coin))
        print("bid_market market: {} starting base coin (do not want to sell this?): {}".format(self.bid_market, self.base_coin))

    def opportunity(self, profit, volume, buyprice, kask, sellprice, kbid, perc, weighted_buyprice, weighted_sellprice, pair, ask_market, bid_market):
        self.pair = pair
        self.ask_market = ask_market
        self.bid_market = bid_market
        self.sellprice = sellprice
        self.buyprice = buyprice

        print("traderbot, ask_market: {}".format(ask_market))
        print("traderbot, bid_market: {}".format(bid_market))

        # print("traderbot.py, opportunity: profit: {}, volume: {} , buyprice: {}, kask: {}, sellprice: {}, kbid: {}, perc: {}, weighted_buyprice: {}, "
        #       "weighted_sellprice: {}, self.exchanges: {}".format(profit, volume, buyprice, kask, sellprice, kbid, perc,
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

        print("traderbot, opportunity: kask coin: {}, price: {}; kbid coin: {}, price: {}".format(next(iter(self.base_coin.keys())),
                                                                                                  next(iter(self.base_coin.values())),
              next(iter(self.quote_coin.keys())), next(iter(self.quote_coin.values()))))

        max_volume = self.get_min_tradeable_volume(buyprice, self.base_coin, self.quote_coin)

        print("traderbot, opportunity: volume {}; max_volume {} config.max_tx_volume {}".format(volume, max_volume, config.max_tx_volume))

        volume = min(volume, max_volume)

        if volume < config.min_tx_volume:
            logging.warn("traderbot, opportunity - Can't automate this trade, minimum volume transaction"+
                         " not reached %f/%f" % (volume, config.min_tx_volume))
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
        logging.info("Buy {} of {} at exchange @{} and sell @{}".format(volume, self.base_coin, kask, kbid))

        deposit_address = self.get_wallet_address()
        import pdb; pdb.set_trace()
        # TODO: take network congestion into account
        if deposit_address:
            create_buy_order(self.pair, buyprice, volume)
            # self.exchanges[kask].buy(volume, buyprice)
            # self.exchanges[kbid].sell(volume, sellprice)

    # get address from bid market & confirm we are capable of transfering funds
    def get_wallet_address(self):
        # reset self.deposit_address to ensure no carryover from last trades
        self.deposit_address = {}
        temp_deposit_address = {}
        # print("market.has: {}".format(self.bid_market.has))
        if self.bid_market.has['fetchDepositAddress']:
            try:
                print("traderbot.py, get_wallet_address, trying to set self.deposit_address, coin: {}".format(next(iter(self.base_coin.keys()))))
                print("traderbot.py, get_wallet_address, self.deposit_address: {}".format(self.bid_market.fetchDepositAddress('BTC')))
                print("traderbot.py, get_wallet_address, self.deposit_address: {}".format(self.bid_market.fetchDepositAddress(next(iter(
                    self.base_coin.keys())))['address']))
                # print("traderbot.py, get_wallet_address, self.deposit_address: {}".format(self.bid_market.fetchDepositAddress()))
                self.deposit_address = self.bid_market.fetchDepositAddress(next(iter(self.base_coin.keys())))
                temp_deposit_address = self.deposit_address
            except:
                try:
                    print("traderbot.py, get_wallet_address, no available address, trying to create one")
                    self.bid_market.createDepositAddress(next(iter(self.base_coin.keys())))
                    time.sleep(10)
                    self.deposit_address = self.bid_market.fetchDepositAddress(next(iter(self.base_coin.keys())))
                    print("traderbot.py, get_wallet_address, no available address self.deposit_address: {}".format(self.deposit_address))
                except:
                    print("traderbot.py, get_wallet_address, no available address & unable to create one")
                    import sys
                    e = sys.exc_info()[0]
                    print("traderbot.py, get_wallet_address: Error: %s" % e)
        return temp_deposit_address

# TODO: accept market order type (and limit?) ?
def create_buy_order(self, pair, buyprice, volume):
    import pdb; pdb.set_trace()
    volume = 5  # test STEEM volume to purchase
    try:
        # self.ask_market.createOrder(pair, 'limit', 'buy', buyprice, volume)
        # createOrder (symbol, type, side, amount[, price[, params]])
        # createLimitBuyOrder (symbol, amount, price[, params])
        self.ask_market.createLimitBuyOrder(next(iter(self.base_coin.keys())), volume, buyprice)
    except:
        e = sys.exc_info()[0]
        print("traderbot.py, create_buy_order: Error: %s" % e)
        pdb.set_trace()

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
