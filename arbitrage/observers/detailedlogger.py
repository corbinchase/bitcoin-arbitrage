import logging
from observers.observer import Observer


class DetailedLogger(Observer):
    # print("5.0 detailedLogger.py")
    def opportunity(self, profit, volume, buyprice, kask, sellprice, kbid, perc,
                    weighted_buyprice, weighted_sellprice):
        print("5.1 DetailedLogger.py, opportunity")
        logging.info("profit: %f USD with volume: %f BTC - buy at %.4f (%s) sell at %.4f (%s) ~%.2f%%" \
        	% (profit, volume, buyprice, kask, sellprice, kbid, perc))