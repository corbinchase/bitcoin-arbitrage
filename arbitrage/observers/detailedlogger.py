import logging
from observers.observer import Observer
import config


class DetailedLogger(Observer):
    def __init__(self):
        self.__name__ = 'DetailedLogger'

    def opportunity(self, profit, volume, buyprice, kask, sellprice, kbid, perc,
                    weighted_buyprice, weighted_sellprice, pair, ask_market, bid_market):
        # TODO: fix so can handle longer list of pairs
        logging.info("detailedlogger.py, profit: %f %s with theoretical base purchase volume: %f %s - buy at %.9f (%s) sell at %.9f (%s) ~%.2f%%" %
                     (profit, pair.split('/')[1], volume, pair.split('/')[0], buyprice, kask, sellprice, kbid, perc))
