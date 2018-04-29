import sys
sys.path.append('../')
import unittest

from arbitrage import arbitrer
# self.depths[kbid]["bids"]) == "[[0.0002695, 18.36], [0.0002689, 664.45], [0.0002683, 116.64], ...."

# depths1 = {
#     'BitstampEUR':
#     {'asks': [{'amount': 4, 'price': 32.8},
#               {'amount': 8, 'price': 32.9},
#               {'amount': 2, 'price': 33.0},
#               {'amount': 3, 'price': 33.6}],
#      'bids': [{'amount': 2, 'price': 31.8},
#               {'amount': 4, 'price': 31.6},
#               {'amount': 6, 'price': 31.4},
#               {'amount': 2, 'price': 30}]},
#     'KrakenEUR':
#     {'asks': [{'amount': 1, 'price': 34.2},
#               {'amount': 2, 'price': 34.3},
#               {'amount': 3, 'price': 34.5},
#               {'amount': 3, 'price': 35.0}],
#      'bids': [{'amount': 2, 'price': 33.2},
#               {'amount': 3, 'price': 33.1},
#               {'amount': 5, 'price': 32.6},
#               {'amount': 10, 'price': 32.3}]}}
#
# depths2 = {
#     'BitstampEUR':
#     {'asks': [{'amount': 4, 'price': 32.8},
#               {'amount': 8, 'price': 32.9},
#               {'amount': 2, 'price': 33.0},
#               {'amount': 3, 'price': 33.6}]},
#     'KrakenEUR':
#     {'bids': [{'amount': 2, 'price': 33.2},
#               {'amount': 3, 'price': 33.1},
#               {'amount': 5, 'price': 32.6},
#               {'amount': 10, 'price': 32.3}]}}
#
# depths3 = {
#     'BitstampEUR':
#     {'asks': [{'amount': 1, 'price': 34.2},
#               {'amount': 2, 'price': 34.3},
#               {'amount': 3, 'price': 34.5},
#               {'amount': 3, 'price': 35.0}]},
#     'KrakenEUR':
#     {'bids': [{'amount': 2, 'price': 33.2},
#               {'amount': 3, 'price': 33.1},
#               {'amount': 5, 'price': 32.6},
#               {'amount': 10, 'price': 32.3}]}}

TEST_MARKETS = {
    'market2': {
        'bids': [
            [3.3, 5],
            [3.2, 15],
            [3.1, 403],
            [3.0, 238],
            [2.9, 48],
            [2.8, 21],
            [2.7, 48],
            [2.6, 40],
            [2.5, 10],
            [2.4, 92],
            [2.3, 138],
            [2.2, 86],
            [2.1, 9],
            [2.0, 298],
            [1.9, 76],
            [1.8, 6],
            [1.7, 297]
        ],
        'asks': [
            [3.3, 516],
            [3.4, 664],
            [3.5, 48],
            [3.6, 105],
            [3.7, 42],
            [3.8, 128],
            [3.9, 22],
            [4.0, 68],
            [4.1, 112],
            [4.2, 39],
            [4.3, 122],
            [4.4, 54],
            [4.5, 24],
            [4.6, 127],
            [4.7, 8],
            [4.8, 14],
            [4.9, 60]
        ],
        'timestamp': 1523762310324,
        'datetime': '2018-04-15T03:18:30.324Z'
    },
    'market1': {
        'bids': [
            [2.9, 17],
            [2.8, 1],
            [2.7, 8],
            [2.6, 51],
            [2.5, 5],
            [2.4, 3],
            [2.3, 18],
            [2.2, 1],
            [2.1, 16],
            [2.0, 5],
            [1.9, 9],
            [1.8, 34],
            [1.7, 1],
            [1.6, 4],
            [1.5, 3],
            [1.4, 45],
            [1.3, 6],
            [1.2, 71],
            [1.1, 23],
            [1.0, 700],
            [0.9, 1026]],
        'asks': [
            [2.9, 58],
            [3.0, 3],
            [3.1, 20],
            [3.2, 60],
            [3.3, 51],
            [3.4, 3],
            [3.5, 33],
            [3.6, 465],
            [3.7, 8],
            [3.8, 50],
            [3.9, 42],
            [4.0, 40],
            [4.1, 15],
            [4.2, 26],
            [4.3, 50],
            [4.4, 8],
            [4.5, 19],
            [4.6, 9],
            [4.7, 50],
            [4.8, 50],
            [4.9, 3]],
        'timestamp': 1523762310570,
        'datetime': '2018-04-15T03:18:31.570Z'
    },
}


class TestArbitrage(unittest.TestCase):
    def setUp(self):
        self.arbitrer = arbitrer.Arbitrer(depths=TEST_MARKETS)  # dict of form {'market_1': {}, 'market_2': {}} where 'market_x' is a kask
        self.arbitrer.max_tx_volume = 10000
        self.depths = TEST_MARKETS  # dict of form {'market_1': {}, 'market_2': {}} where 'market_x' is a kask
        # print("self.depths:", self.depths)

    def test_getprofit1(self):
        # self.arbitrer.depths = depths2
        maxi, maxj = 26, 21
        # for i in range(maxi - 1):
        #     for j in range(maxj - 1):
        profit, vol, wb, ws = self.arbitrer.get_profit_for(0, 0, 'market1', 'market2', 1000, 1000)  # mi, mj, kask, kbid,
        print("arbitrage_test, test_getprofit1, profit: {}, vol: {}, wb: {}, ws: {}".format(profit, vol, wb, ws))
        # max_spend_ask, max_vol_ask
        # when i=0 and j=0:: max_amount_buy: 58.0000, max_amount_sell: 5.0000, max_amount: 5.0000, profit: 2.0000, buy_total: 5.0000,
            # sell_total: 5.0000, w_buyprice: 2.900000000, w_sellprice: 3.300000000

        # assert(80 == int(profit * 100))
        # assert(vol == 2)

    # def test_getprofit2(self):
    #     # self.arbitrer.depths = depths2
    #     profit, vol, wb, ws = self.arbitrer.get_profit_for(2, 1, 'market1', 'market2', 1000, 1000)
    #     assert(159 == int(profit * 100))
    #     assert(vol == 5)
    #
    # def test_getprofit3(self):
    #     # self.arbitrer.depths = depths3
    #     profit, vol, wb, ws = self.arbitrer.get_profit_for(2, 1, 'market1', 'market2', 1000, 1000)
    #     assert(profit == 0)
    #     assert(vol == 0)


if __name__ == '__main__':
    unittest.main()
