import logging
from observers.observer import Observer


class Logger(Observer):
    def opportunity(self, profit, volume, buyprice, kask, sellprice, kbid, perc,
                    weighted_buyprice, weighted_sellprice, pair, ask_market, bid_market):
        logging.info("profit: %f USD with volume: %f BTC - buy from %s sell to %s ~%.2f%%" \
        	% (profit, volume, kask, kbid, perc))
