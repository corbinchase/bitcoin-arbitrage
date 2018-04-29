import logging
from observers.observer import Observer
import config


class DetailedLogger(Observer):
    def opportunity(self, profit, volume, buyprice, kask, sellprice, kbid, perc,
                    weighted_buyprice, weighted_sellprice, pair, ask_market, bid_market):
        # print("DetailedLogger.py, opportunity")
        logging.info("detailedlogger.py, profit: %f BTC (triple check) with theoretical volume: %f %s - buy at %.9f (%s) sell at %.9f (%s) ~%.2f%%" %
                     (profit, volume, pair.split('/')[0], buyprice, kask, sellprice, kbid, perc))
