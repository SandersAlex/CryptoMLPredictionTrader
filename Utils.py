import sys
sys.path.append('../../')
from forex_python.bitcoin import BtcConverter
from Bittrex3 import Bittrex3
from datetime import datetime
from collections import deque
import urllib
import json
import re
import traceback
import praw
import ftplib
from textblob import TextBlob


def file_to_json(filename):
    try:
        file = open(filename, 'r')
        contents = str(file.read())
        posts = json.loads(contents)
        file.close()
        return posts
    except FileNotFoundError:
        print("No such file: " + filename)
        exit(1)

def json_to_file(json_obj, filename):
    try:
        file = open(filename, 'w')
        json.dump(json_obj, file, sort_keys=True, indent=4, separators=(',', ': '))
        file.close()
    except FileNotFoundError:
        print("No such file: " + filename)
        exit(1)

def get_percent_change_24h(coin):
    if(coin['PrevDay'] != 0):
        return (coin['Last'] - coin['PrevDay']) * 100 / coin['PrevDay'];
    return 0

def get_coinmarketcap_1hr_change(coinmarketcap_coins):
    # coinmarketcap_coins = query_url("https://api.coinmarketcap.com/v1/ticker/?limit=2000")
    d = {}
    for coin in coinmarketcap_coins:
        d[coin['symbol']] = coin['percent_change_1h']
    return d

def get_ranks(coinmarketcap_coins):
    # coinmarketcap_coins = query_url("https://api.coinmarketcap.com/v1/ticker/?limit=2000")
    d = {}
    for coin in coinmarketcap_coins:
        d[coin['symbol']] = coin['rank']
    return d

def get_updated_coinmarketcap_coins():
    return query_url("https://api.coinmarketcap.com/v1/ticker/?limit=2000")

def bitcoin_to_USD(bitcoin_amount):
    b = BtcConverter()
    latest_price = b.get_latest_price('USD')
    return latest_price * bitcoin_amount

def get_api():
    with open("cryptoCoinsData/"+"apiKeySecret.json") as secrets_file:
        secrets = json.load(secrets_file)
        secrets_file.close()
    return Bittrex3(secrets['key'], secrets['secret'])

def query_url(url_addr):
    with urllib.request.urlopen(url_addr) as url:
        return json.loads(url.read().decode())

def clear_and_write_to_file(filename, text):
    open(filename, 'w').close()

    with open(filename, 'a', encoding="utf-8") as myfile:
        myfile.write(text)

def print_and_write_to_logfile(log_text):
    if log_text is not None:
        print(log_text + '\n')

        with open('cryptoLogs/logs.txt', 'a') as myfile:
            myfile.write(log_text + '\n\n')

def get_total_bitcoin(api):
    result = api.get_balance('BTC')
    if result['success']:
        return float(result['result']['Available'])
    else:
        print_and_write_to_logfile("Bitcoin Balance Request Unsuccessful")
        return 0

def get_date_time():
    now = datetime.now()
    return "%s:%s:%s %s/%s/%s" % (now.hour, now.minute, now.second, now.month, now.day, now.year)

def time_stamp_to_date(timstamp):
    return datetime.fromtimestamp(int(timstamp)).strftime('%H:%M:%S %m/%d/%Y')

def get_time_passed_minutes(time_opened):
    now = datetime.now()

    time_offset = datetime.utcnow() - now

    try:
        opened_datetime = datetime.strptime(time_opened, "%Y-%m-%dT%H:%M:%S.%f") - time_offset
    except ValueError:
        opened_datetime = datetime.strptime(time_opened, "%Y-%m-%dT%H:%M:%S") - time_offset

    time_diff = now - opened_datetime

    time_passed = time_diff.total_seconds() / 60

    return time_passed

def get_updated_bittrex_coins():
    bittrex_data = query_url("https://bittrex.com/api/v1.1/public/getmarketsummaries")['result']
    coins = {}
    for coin in bittrex_data:
        key = coin['MarketName']
        coins[key] = coin
    return coins

def get_bittrex_market_names():
    bittrex_data = query_url("https://bittrex.com/api/v1.1/public/getmarkets")['result']
    coins = {}
    for coin in bittrex_data:
        if coin['BaseCurrency'] =='BTC':
            key = coin['MarketCurrency']
            t = {}
            t['full_name'] = coin['MarketCurrencyLong']
            t['mentioned_ids'] = []
            t['mentioned_times'] = []
            t['text'] = []
            t['upvotes'] = []
            t['sentiments'] = []
            coins[key] = t
    return coins

def buy(api, market, amount, coin_price, percent_change_24h, desired_gain, percent_change_1h):
    total_to_spend = bitcoin_to_USD(coin_price * amount)
    total_to_spend += total_to_spend * 0.0025  # include the fee
    buy_order = api.buy_limit(market, amount, coin_price)

    if buy_order['success']:
        pending_orders = file_to_json("cryptoCoinsData/pendingList.json")
        coin_price_usd = bitcoin_to_USD(coin_price)
        time = get_date_time()

        print_and_write_to_logfile("BUYING\n" + market + "\n24h%: " + str(
            percent_change_24h) + "\nUSD: $" + str(coin_price_usd) + "\nBTC: " + str(
            coin_price) + "\nAmount: " + str(amount)
                                   + "\nTotal Paid: $" + str(total_to_spend) + "\n1hr%: " + str(
            percent_change_1h) + "\nTime: " + time)

        t = {}
        t['market'] = market
        t['highest_24h_change'] = percent_change_24h
        t['original_24h_change'] = percent_change_24h
        t['price_bought'] = coin_price
        t['amount'] = amount
        t['total_paid'] = total_to_spend
        t['sell_threshold'] = 5
        t['uuid'] = buy_order['result']['uuid']
        t['desired_gain'] = desired_gain
        t['high_bar'] = desired_gain

        # send to pending
        pending_orders['Buying'][market] = t

        json_to_file(pending_orders, "cryptoCoinsData/pendingList.json")
    else:
        print_and_write_to_logfile(
            "Buy order of " + str(amount) + " " + market + " did not go through: " + buy_order['message'])
    return buy_order

def sell(api, amount, market, bittrex_coins):
    coin_info = bittrex_coins[market]
    cur_coin_price = float(coin_info['Last'])

    sell_order = api.sell_limit(market, amount, cur_coin_price)
    cur_24h_change = get_percent_change_24h(coin_info)

    held_coins = file_to_json("cryptoCoinsData/currentlyHeldCoins.json")
    pending_orders = file_to_json("cryptoCoinsData/pendingList.json")

    if sell_order['success']:
        selling_for = bitcoin_to_USD(cur_coin_price * amount)
        selling_for -= selling_for * 0.0025  # adding the fee for selling

        net_gain_loss = selling_for - float(held_coins[market]['total_paid'])
        cur_coin_price_usd = bitcoin_to_USD(cur_coin_price)
        cur_date_time = get_date_time()

        print_and_write_to_logfile(
            "SELLING\n" + market + "\nUSD: $" + "\n24h%: " + str(cur_24h_change) + str(cur_coin_price_usd) + "\nBTC: " + str(
                cur_coin_price) + "\nAmount: " + str(amount)
            + "\nTotal Sold For: $" + str(selling_for) + "\nNet Gain/Loss: " + str(
                net_gain_loss) + "\nTime: " + str(cur_date_time))

        t = {}
        t['market'] = market
        t['cur_coin_price'] = cur_coin_price
        t['cur_coin_price_usd'] = cur_coin_price_usd
        t['amount'] = amount
        t['cur_24h_change'] = cur_24h_change
        t['sold_for'] = selling_for
        t['cur_24h_change'] = cur_24h_change
        t['sold_for'] = selling_for
        t['cur_date_time'] = cur_date_time
        t['cur_24h_change'] = cur_24h_change
        t['uuid'] = sell_order['result']['uuid']
        t['gain'] = net_gain_loss

        pending_orders['Selling'][market] = t
        json_to_file(pending_orders, "cryptoCoinsData/pendingList.json")
    else:
        print_and_write_to_logfile("Sell order did not go through: " + sell_order['message'])

def percent_change(bought_price, cur_price):
    return 100 * (cur_price - bought_price) / bought_price

def init_global_return():
    global_return = file_to_json('cryptoCoinsData/netGainInvested.json')
    global_return['Invested'] = 0.0
    global_return['Gain'] = 0.0
    json_to_file(global_return, 'cryptoCoinsData/netGainInvested.json')

def delete_entry_from_json(fileName, key):
    temp = file_to_json(fileName)
    if key in temp:
        del temp[key]
        json_to_file(temp, fileName)

        global_return = file_to_json('cryptoCoinsData/netGainInvested.json')
        global_return['Invested'] = 0.0
        global_return['Gain'] = 0.0
        json_to_file(global_return, 'cryptoCoinsData/netGainInvested.json')

def get_first_market_coin(market):
    m = re.search('([A-z0-9]+)-([A-z0-9]+)', market)
    return m.group(1)


def get_second_market_coin(market):
    m = re.search('([A-z0-9]+)-([A-z0-9]+)', market)
    return m.group(2)

def update_market_historical_list(market, historical_coin_data, bittrex_coins, num_ticks):
    if market not in historical_coin_data:
        new_list = deque([])
    else:
        new_list = historical_coin_data[market]
    new_list.append(bittrex_coins[market]['Last'])
    if len(new_list) > num_ticks:
        new_list.popleft()
    return new_list

def update_historical_coin_data(historical_coin_data, bittrex_coins, data_ticks_to_save):
    for market in bittrex_coins:
        if market.startswith('BTC'):
            historical_coin_data[market] = update_market_historical_list(market, historical_coin_data, bittrex_coins, data_ticks_to_save)
        if market.startswith("ETC"):
            break
    return historical_coin_data

def send_to_ftp_server(filename):
    try:
        with open("cryptoCoinsData/ftp_server_info.json") as server_file:
            info = json.load(server_file)
            server_file.close()

        session = ftplib.FTP(info['ip'], info['user'], info['pass'])
        file = open(filename, 'rb')
        session.storbinary('STOR public_html/' + filename, file)
        file.close()
        session.quit()
    except:
        print("No ftp info on file")



def get_reddit_api():
    with open("cryptoCoinsData/apiKeySecretReddit.json") as secrets_file:
        reddit_secrets = json.load(secrets_file)
        secrets_file.close()

    reddit = praw.Reddit(client_id=reddit_secrets["client_id"], client_secret=reddit_secrets["client_secret"],
                         password=reddit_secrets["password"], user_agent=reddit_secrets["user_agent"],
                         username=reddit_secrets["username"])

    return reddit
def get_sentiment(s):
    sentiment = TextBlob(s)
    return sentiment.sentiment.polarity