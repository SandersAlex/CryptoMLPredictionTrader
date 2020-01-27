import urllib.parse
import time
import hmac
import hashlib
from decimal import Decimal
import json
import requests

BUY_ORDERBOOK = 'buy'
SELL_ORDERBOOK = 'sell'
BOTH_ORDERBOOK = 'both'

PUBLIC_SET = ['getmarkets', 'getcurrencies', 'getticker', 'getmarketsummaries', 'getorderbook',
              'getmarkethistory']

MARKET_SET = ['getopenorders', 'cancel', 'sellmarket', 'selllimit', 'buymarket', 'buylimit']

ACCOUNT_SET = ['getbalances', 'getbalance', 'getdepositaddress', 'withdraw', 'getorder', 'getorderhistory',
               'getwithdrawalhistory', 'getdeposithistory']

class Bittrex3(object):
    def __init__(self, api_key, api_secret):
        self.api_key = str(api_key) if api_key is not None else ''
        self.api_secret = str(api_secret) if api_secret is not None else ''
        self.public_set = set(PUBLIC_SET)
        self.market_set = set(MARKET_SET)
        self.account_set = set(ACCOUNT_SET)

    # all below methods uses api_query to do ALL types of queries related to Bittrex
    # Queries Bittrex with given method and options
    # method: str
    # options: dictionary for the str:method you are calling with
    # return: dictionary: JSON response from Bittrex
    def api_query(self, method, options=None):
        if not options:
            options = {}
        nonce = str(int(time.time() * 1000))
        base_url = 'https://bittrex.com/api/v1.1/%s/'
        request_url = ''

        if method in self.public_set:
            request_url = (base_url % 'public') + method + '?'
        elif method in self.market_set:
            request_url = (base_url % 'market') + method + '?apikey=' + self.api_key + "&nonce=" + nonce + '&'
        elif method in self.account_set:
            request_url = (base_url % 'account') + method + '?apikey=' + self.api_key + "&nonce=" + nonce + '&'

        request_url += urllib.parse.urlencode(options)

        signature = hmac.new(self.api_secret.encode(), request_url.encode(), hashlib.sha512).hexdigest()

        headers = {"apisign": signature}

        sresponse = requests.get(request_url, headers=headers).content.decode('utf-8')
        return json.loads(sresponse, parse_float=Decimal, parse_int=Decimal)

    # return avaliable market in JSON
    def get_markets(self):
        return self.api_query('getmarkets')

    # return Supported currencies info in JSON
    def get_currencies(self):
        return self.api_query('getcurrencies')

    # return current tick values for a market as JSON
    def get_ticker(self, market):
        return self.api_query('getticker', {'market': market})

    # return last 24 hour summary of all active exchanges in JSON
    def get_market_summaries(self):
        return self.api_query('getmarketsummaries')

    # return the orderbook for a given market in JSON
    def get_orderbook(self, market, depth_type, depth=20):
        return self.api_query('getorderbook', {'market': market, 'type': depth_type, 'depth': depth})

    # return retrieve the latest trades that have occurred for a specific market in JSON
    def get_market_history(self, market, count):
        return self.api_query('getmarkethistory', {'market': market, 'count': count})

    #  return JSON: used to place a buy order in a specific market
    def buy_market(self, market, quantity, rate):
        return self.api_query('buymarket', {'market': market, 'quantity': quantity, 'rate': rate})

    # buy
    def buy_limit(self, market, quantity, rate):
        return self.api_query('buylimit', {'market': market, 'quantity': quantity, 'rate': rate})

    # return JSON: used to place a sell order in a specific market
    def sell_market(self, market, quantity, rate):
        return self.api_query('sellmarket', {'market': market, 'quantity': quantity, 'rate': rate})

    # sell
    def sell_limit(self, market, quantity, rate):
        return self.api_query('selllimit', {'market': market, 'quantity': quantity, 'rate': rate})

    #uuid: uuid of buy or sell order
    def cancel(self, uuid):
        return self.api_query('cancel', {'uuid': uuid})

    def get_open_orders(self, market):
        return self.api_query('getopenorders', {'market': market})

    #get all balances
    def get_balances(self):
        return self.api_query('getbalances', {})

    def get_balance(self, currency):
        return self.api_query('getbalance', {'currency': currency})

    def get_deposit_address(self, currency):
        return self.api_query('getdepositaddress', {'currency': currency})

    def withdraw(self, currency, quantity, address):
        return self.api_query('withdraw', {'currency': currency, 'quantity': quantity, 'address': address})

    def get_order(self, uuid):
        return self.api_query('getorder', {'uuid': uuid})

    def get_order_history(self, market=""):
        return self.api_query('getorderhistory', {"market": market})

    def get_withdrawal_history(self, currency=""):
        return self.api_query('getwithdrawalhistory', {"currency": currency})

    def get_deposit_history(self, currency=""):
        return self.api_query('getdeposithistory', {"currency": currency})
