# Copyright (C) 2013, Maxime Biais <maxime@biais.org>

import logging
import argparse
import glob
import os
import inspect
import os.path
import sys
import config
import arbitrer
import pprint
import public_markets

class ArbitrerCLI:
    def __init__(self):
        self.exchanges = []
        self.inject_verbose_info()


    def inject_verbose_info(self):
        logging.VERBOSE = 15
        logging.verbose = lambda x: logging.log(logging.VERBOSE, x)
        logging.addLevelName(logging.VERBOSE, "VERBOSE")

    def exec_command(self, args):
        # print("Arg command: ", args.command)
        if "watch" in args.command:
            self.create_arbitrer(args)
            # self.list_markets()
            # print("7. Arbitrage.py, exec_command, getting balance, args: ", args)
            self.get_balance(args)
            print("arbitrage.py, after get_balance")
            self.arbitrer.loop()
            # print("replay history:")
            self.arbitrer.replay_history(args.replay_history)

        # if "replay-history" in args.command:
        #     self.create_arbitrer(args)
        #     self.arbitrer.replay_history(args.replay_history)
        # if "get-balance" in args.command:
        #     self.get_balance(args)
        # if "list-public-markets" in args.command:
        #     self.list_markets()

    # def list_markets(self):
    #     markets = []
    #     for filename in glob.glob(os.path.join(public_markets.__path__[0], "*.py")):
    #         module_name = os.path.basename(filename).replace('.py', '')
    #         if not module_name.startswith('_'):
    #             module = __import__("public_markets." + module_name)
    #             test = eval('public_markets.' + module_name)
    #             for name, obj in inspect.getmembers(test):
    #                 if inspect.isclass(obj) and 'Market' in (j.__name__ for j in obj.mro()[1:]):
    #                     if not obj.__module__.split('.')[-1].startswith('_'):
    #                         markets.append(obj.__name__)
    #     markets.sort()
    #     print("\n".join(markets))
    #     sys.exit(0)

    def get_balance(self, args):
        # print("8.0 arbitrage.py, get_balance, args:", args)
        if not self.exchanges:
            logging.error("You must use --markets argument to specify markets")
            sys.exit(2)
        for exchange in self.exchanges:
            if exchange.apiKey and exchange.secret:
                bal_avail = exchange.fetchBalance()['free']
                print("arbitrage.py, get_balance: exchange.id: {}; number of coins available for trading:  {}".format(exchange.id, len(bal_avail)))
                # print("arbitrage.py, get_balance: exchange.id: {}; number of coins available for trading:  {}".format(exchange.id, bal_avail))

            else:
                print("No {} API credentials can be found. Check the config.py file".format(exchange.id))


        # pmarkets = self.exchanges
        # pmarketsi = []
        # for pmarket in pmarkets:
        #     try:
        #         print("8.1 arbitrage.py, get_balance, pmarket.id in pmarket:", pmarket.id)
        #         # # api = eval(= config.market_api_keys[pmarket.id]
        #         # # print("api: ", api)
        #         # # if api:
        #         #     balance = pmarket.fetchBalance()
        #         #     print("BALANCE: ", balance)
        #         # # else:
        #         #     print("API for {} exchange missing. Check config.py file".format(pmarket.id))
        #     except (ImportError, AttributeError) as e:
        #         print("ERROR (arbitrer.py, init_markets): Market object {} is invalid: Ignored (you should check your config file). {}".format(
        #             pmarket, e))


            # config.market_api_keys

            # exec('import private_markets.' + pmarket.lower())
            # market: private_markets.bitstampusd.PrivateBitstampUSD()
            # TODO: use exchange-specific API to retrieve available balance
            # market = eval('private_markets.' + pmarket.lower() + '.Private' + pmarket + '()')
            # pmarketsi.append(market)
        # for market in pmarketsi:
        #     # print(market)

    # create arbitrer bot with args from execute command, from CLI
    def create_arbitrer(self, args):
        self.arbitrer = arbitrer.Arbitrer()
        if args.markets:
            self.exchanges = self.arbitrer.init_markets(args)
        print("args.observers: ", args.observers)
        if args.observers:
            # print("arbitrage.py, crate_arbitrer, -- passed if statement")
            try:
                # print("arbitrage.py, crate_arbitrer, args.observers:" + args.observers.split(","))
                self.arbitrer.init_observers(args.observers.split(","))
            # Sending init_observers a list of args.observers (from config)
            except AttributeError as e:
                print("No listed observers in command line argument - pulling observers from config file")
                self.arbitrer.init_observers(args.observers)

    def init_logger(self, args):
        level = logging.INFO
        if args.verbose:
            level = logging.VERBOSE
        if args.debug:
            level = logging.DEBUG
        logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s',
                            level=level)

    def main(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("-d", "--debug", help="debug verbose mode",
                            action="store_true")
        parser.add_argument("-v", "--verbose", help="info verbose mode",
                            action="store_true")
        parser.add_argument("-o", "--observers", type=str, help="observers, example: -oLogger,Emailer", default=config.observers)
        parser.add_argument("-m", "--markets", type=str,
                            help="list markets to arbitrage; example: -m BitstampEUR,KrakenEUR. Leave empty to pull markets from config.py file",
                            default=config.markets_ccxt)
        parser.add_argument("command", nargs='*', default="watch",
                            help='verb: "watch|replay-history|get-balance|list-public-markets"')
        args = parser.parse_args()
        print("Args: ", args)
        # self.init_logger(args)
        self.init_logger(args)
        self.exec_command(args)


def main():
    cli = ArbitrerCLI()
    cli.main()


if __name__ == "__main__":
    main()