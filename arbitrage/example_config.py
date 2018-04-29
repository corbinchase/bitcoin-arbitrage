markets_ccxt = [
    "Binance",
    "Poloniex"
]

pairs = [
    "BTC/USDT"
]

base_pair = "BTC/USDT"

# observers if any
# ["Logger", "DetailedLogger", "TraderBot", "TraderBotSim", "HistoryDumper", "Emailer"]
observers = ["DetailedLogger", "TraderBot", "Emailer"]

market_expiration_time = 120  # in seconds: 2 minutes

refresh_rate = 2

#### Trader Bot Config
# Access to Private APIs

paymium_username = "FIXME"
paymium_password = "FIXME"
paymium_address = "FIXME"  # to deposit btc from markets / wallets

#### Bitstam
bitstamp_username = ""
bitstamp_password = ""

# SafeGuards
max_tx_volume = 1  # in BTC
min_tx_volume = 0.0005  # in BTC
balance_margin = 0.02  # 5%
profit_thresh = 10  # in EUR
perc_thresh = 8  # in %

#### Emailer Observer Config
smtp_host = 'FIXME'
smtp_login = 'FIXME'
smtp_passwd = 'FIXME'
smtp_from = 'FIXME'
smtp_to = 'FIXME'

#### XMPP Observer
xmpp_jid = ""
xmpp_password = ""
xmpp_to = ""

#### API Keys
market_api_keys = {
    "binance_public": "",
    "binance_secret": "",
    "poloniex_public": "",
    "poloniex_secret": ""
}
