import urllib.request
import urllib.error
import urllib.parse
import json
import logging
from public_markets.market import Market


class Bitfinex(Market):
    def __init__(self, currency, code):
        super().__init__(currency)
        self.code = code
        self.update_rate = 20

    def update_depth(self):
        res = urllib.request.urlopen(
            'https://api.bitfinex.com/v1/book/' + self.code)
        jsonstr = res.read().decode('utf8')
        try:
            depth = json.loads(jsonstr)
        except Exception:
            logging.error("%s - Can't parse json: %s" % (self.name, jsonstr))
        self.depth = self.format_depth(depth)

    def sort_and_format(self, l, reverse=False):
        l.sort(key=lambda x: float(x["price"]), reverse=reverse)
        r = []
        for i in l:
            r.append({'price': float(i['price']),
                      'amount': float(i['amount'])})
        return r

    def format_depth(self, depth):
        bids = self.sort_and_format(depth['bids'], True)
        asks = self.sort_and_format(depth['asks'], False)
        return {'asks': asks, 'bids': bids}
