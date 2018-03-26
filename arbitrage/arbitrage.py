# Copyright (C) 2013, Maxime Biais <maxime@biais.org>

import logging
import argparse
import glob
import os
import inspect
import os.path
import sys

import arbitrer
import public_markets

class ArbitrerCLI:
    def __init__(self):
        self.inject_verbose_info()

    def inject_verbose_info(self):
        logging.VERBOSE = 15
        logging.verbose = lambda x: logging.log(logging.VERBOSE, x)
        logging.addLevelName(logging.VERBOSE, "VERBOSE")

    def exec_command(self, args):
        print("2. arbitrage.py, exec_command --> args: ", args.command)
        if "watch" in args.command:
            self.create_arbitrer(args)
            print("2.1 watching these markets: ")
            self.list_markets()
            print("7. Arbitrage.py, exec_command, getting balance, args: ", args)
            self.get_balance(args)
            self.arbitrer.loop()
            print("replay history:")
            self.arbitrer.replay_history(args.replay_history)

        # if "replay-history" in args.command:
        #     self.create_arbitrer(args)
        #     self.arbitrer.replay_history(args.replay_history)
        # if "get-balance" in args.command:
        #     self.get_balance(args)
        # if "list-public-markets" in args.command:
        #     self.list_markets()

    def list_markets(self):
        markets = []
        for filename in glob.glob(os.path.join(public_markets.__path__[0], "*.py")):
            module_name = os.path.basename(filename).replace('.py', '')
            if not module_name.startswith('_'):
                module = __import__("public_markets." + module_name)
                test = eval('public_markets.' + module_name)
                for name, obj in inspect.getmembers(test):
                    if inspect.isclass(obj) and 'Market' in (j.__name__ for j in obj.mro()[1:]):
                        if not obj.__module__.split('.')[-1].startswith('_'):
                            markets.append(obj.__name__)
        markets.sort()
        print("\n".join(markets))
        sys.exit(0)

    def get_balance(self, args):
        print("8.0 arbitrage.py, get_balance, args:", args)
        if not args.markets:
            logging.error("You must use --markets argument to specify markets")
            sys.exit(2)
        pmarkets = args.markets.split(",")
        pmarketsi = []
        for pmarket in pmarkets:
            print("8.1 arbitrage.py, get_balance, pmarket in pmarket:", pmarket)

            # TODO: no private market files for exchanges besides bitstamp and paymium
            exec('import private_markets.' + pmarket.lower())

            # market: private_markets.bitstampusd.PrivateBitstampUSD()
            market = eval('private_markets.' + pmarket.lower() + '.Private' + pmarket + '()')
            print("8.2 arbitrage.py, get_balance, market: ", market)
            pmarketsi.append(market)
        for market in pmarketsi:
            print("7.2 arbitrage.py, get_balance, market:", market)
            print(market)

    # create arbitrer bot with args from execute command, from CLI
    def create_arbitrer(self, args):
        self.arbitrer = arbitrer.Arbitrer()
        print("3. arbitrage.py, create_arbitrer && Arbitrer() has been created; self.arbitrer: ", self.arbitrer)
        if args.observers:
            print("3.1 arbitrage.py, create_arbitrer, args.observers = TRUE")
            self.arbitrer.init_observers(args.observers.split(","))
        if args.markets:
            self.arbitrer.init_markets(args.markets.split(","))
            print("6.0 arbitrage.py, create_arbitrer, args.markets = true; markets have been initiatlized, args.market: ", args.markets)

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
        parser.add_argument("-o", "--observers", type=str,
                            help="observers, example: -oLogger,Emailer")
        # parser.add_argument("-m", "--markets", type=str,
        #                     help="markets, example: -m BitstampEUR,KrakenEUR")
        parser.add_argument("command", nargs='*', default="watch",
                            help='verb: "watch|replay-history|get-balance|list-public-markets"')
        args = parser.parse_args()
        print("1. arbitrage.py, main --> args:", args, "\n 1. init_logger(args): ", self.init_logger(args))
        self.init_logger(args)
        self.exec_command(args)


def main():
    cli = ArbitrerCLI()
    cli.main()


if __name__ == "__main__":
    main()
