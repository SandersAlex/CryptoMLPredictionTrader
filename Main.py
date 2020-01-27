import sys
sys.path.append('../../')

import traceback
import time
import Utils as utils
import strategies.Keltner_Channel_Strategy as KCStrategy
import strategies.Percent_Window_Strategy as PWStrategy
import strategies.Random_Coin_Strategy as RandCStrategy
import strategies.Hold_Until_Strategy as HUStrategy
import strategies.RedditGatherData as RGData
import strategies.Top_Reddit_Strategy as TRStrategy
import strategies.ML_Strategy as MLStrategy
import tensorflow as tf
import requests
import csv



def clean_orders(orders):
    pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")
    for order in orders:
        time_opened = order['Opened']
        time_passed = utils.get_time_passed_minutes(time_opened)

        uuid = order['OrderUuid']
        market = ""

        buying_or_selling = 'Buying' if order['OrderType'] == 'LIMIT_BUY' else 'Selling'

        for pending_market in pending_orders[buying_or_selling]:
            if pending_orders[buying_or_selling][pending_market]['uuid'] == uuid:
                market = pending_market

        if time_passed > time_until_cancel_processing_order_minutes:
            uuid = order['OrderUuid']
            cancel_order = api.cancel(uuid)

            if cancel_order['success']:

                if market in pending_orders[buying_or_selling]:
                    del pending_orders[buying_or_selling][market]

                    utils.json_to_file(pending_orders, "cryptoCoinsData/pendingList.json")
                    utils.print_and_write_to_logfile(
                        "Cancel Order of " + str(order["Quantity"]) + " " + str(order['Exchange']) + " Successful " + utils.get_date_time())
            else:
                utils.print_and_write_to_logfile(
                    "Cancel Order of " + str(order["Quantity"]) + order['Exchange'] + " Unsuccessful: " + cancel_order[
                        'message'] + " " + utils.get_date_time())

def update_pending_orders(orders):
    pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")

    processing_orders = [order['OrderUuid'] for order in orders]

    buy_uuids_markets = [(pending_orders['Buying'][market]['uuid'], market) for market in pending_orders['Buying']]
    for buy_uuids_market in buy_uuids_markets:
        buy_uuid = buy_uuids_market[0]
        if buy_uuid not in processing_orders:
            buy_market = buy_uuids_market[1]

            pending_buy_order = pending_orders['Buying'][buy_market]
            amount = str(pending_buy_order['amount'])
            utils.print_and_write_to_logfile(
                "Buy order: " + amount + " of " + buy_market + " Processed Successfully " + "UUID: "
                + buy_uuid + " " + utils.get_date_time())
            move_to_from_held(buy_market, 'Buying')

            highest_price_list = utils.file_to_json("cryptoCoinsData/heldCoinsHighestPriceRecorded.json")
            highest_price_list[buy_market] = pending_orders['Buying'][buy_market]['price_bought']
            utils.json_to_file(highest_price_list, 'cryptoCoinsData/heldCoinsHighestPriceRecorded.json')

    sell_uuids_markets = [(pending_orders['Selling'][market]['uuid'], market) for market in pending_orders['Selling']]
    for sell_uuids_market in sell_uuids_markets:
        if sell_uuids_market[0] not in processing_orders:
            pending_sell_order = pending_orders['Selling'][sell_uuids_market[1]]
            amount = str(pending_sell_order['amount'])
            utils.print_and_write_to_logfile(
                "Sell order: " + amount + " of " + " " + sell_uuids_market[1] + " Processed Successfully " + "UUID: "
                + sell_uuids_market[0] + " " + utils.get_date_time())
            move_to_from_held(sell_uuids_market[1], 'Selling')

def move_to_from_held(pending_market, buying_or_selling):
    held_coins = utils.file_to_json("cryptoCoinsData/currentlyHeldCoins.json")
    pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")

    global_return = utils.file_to_json('cryptoCoinsData/netGainInvested.json')

    pending_order = pending_orders[buying_or_selling][pending_market]

    if buying_or_selling == 'Buying':
        held_coins[pending_order['market']] = pending_order
        utils.json_to_file(held_coins, 'cryptoCoinsData/currentlyHeldCoins.json')
        global_return['Invested'] += pending_orders['Buying'][pending_market]['total_paid']

    elif buying_or_selling == 'Selling':
        del held_coins[pending_market]
        utils.json_to_file(held_coins, "cryptoCoinsData/currentlyHeldCoins.json")
        global_return['Gain'] += pending_orders['Selling'][pending_market]['gain']

    utils.json_to_file(global_return, 'cryptoCoinsData/netGainInvested.json')
    del pending_orders[buying_or_selling][pending_market]
    utils.json_to_file(pending_orders, "cryptoCoinsData/pendingList.json")


def initialize_reddit_strat():
    reddit_api = utils.get_reddit_api()
    total_slots = 5
    return RGData.RedditStrat(api, reddit_api, total_slots)
def run_reddit_strat():
    rgdata.refresh_held_pending()
    rgdata.update_reddit_coins()
    rgdata.update_bittrex_coins()
    rgdata.store_top_10_data()

def initialize_buy_low_sell_high_strat():
    desired_gain = 20
    desired_low_point = -10

    total_slots = 4
    return TRStrategy.BuyLowSellHighStrat(api, desired_gain, desired_low_point, total_slots)
def run_buy_low_sell_high_strat():
    if trs.count_until_reddit_strat == 0:
        run_reddit_strat()
        trs.count_until_reddit_strat = 360
    trs.count_until_reddit_strat -= 1
    trs.refresh_held_pending()
    trs.update_bittrex_coins()


    if total_bitcoin > satoshi_50k:
        trs.low_high_buy_strat(total_bitcoin)

    trs.low_high_sell_strat()
    time.sleep(10)

def initialize_ML_strat():
    f = open('./crypto_data/BCH_Test_Data.csv', "w+")
    f.close()
    f = open('./crypto_data/BTC_Test_Data.csv', "w+")
    f.close()
    f = open('./crypto_data/EOS_Test_Data.csv', "w+")
    f.close()
    f = open('./crypto_data/ETH_Test_Data.csv', "w+")
    f.close()
    f = open('./crypto_data/LTC_Test_Data.csv', "w+")
    f.close()
    f = open('./crypto_data/XRP_Test_Data.csv', "w+")
    f.close()

    starttime = time.time()
    count = 0;
    while count < 50:
        r = requests.get(
            "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC,ETH,XRP,BCH,EOS,LTC&tsyms=USD&api_key={01b2bb65b77f9f0ec6addff9fd0ec69df69147a46016b559ad067a20e9a84c4d}")
        data = r.json()['DISPLAY']

        for d in data:
            coin = data[d]['USD']
            s = './crypto_data/' + d + '_Test_Data.csv'
            addString = ""
            with open(s, 'a') as fp:
                for key in coin:
                    if key == 'PRICE' or key == 'VOLUMEDAYTO' or key == 'VOLUME24HOURTO' or key == 'MEDIAN' or key == 'CHANGEPCT24HOUR' or key == 'CHANGEPCTDAY' or key == 'CHANGEPCTHOUR':
                        if key == 'CHANGEPCT24HOUR' or key == 'CHANGEPCTDAY' or key == 'CHANGEPCTHOUR':
                            addString = addString + "," + coin[key]
                        else:
                            newstr = coin[key][2:].replace(",", "")
                            addString = addString + "," + newstr

                fp.write(str(int(time.time())) + "," + addString[1:] + '\n')
        count+=1
        # time.sleep(90.0 - ((time.time() - starttime) % 90.0))
        # time.sleep(1)


    total_slots = 5
    return MLStrategy.MLStrat(api,total_slots)


def run_ml_strat():
    r = requests.get(
        "https://min-api.cryptocompare.com/data/pricemultifull?fsyms=BTC,ETH,XRP,BCH,EOS,LTC&tsyms=USD&api_key={01b2bb65b77f9f0ec6addff9fd0ec69df69147a46016b559ad067a20e9a84c4d}")
    data = r.json()['DISPLAY']

    # for all coin_data, delete first row
    for d in data:
        lines = list()
        s = './crypto_data/' + d + '_Test_Data.csv'
        with open(s, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                lines.append(row)
        lines = lines[1:]
        with open(s, 'w') as fp:
            writer = csv.writer(fp)
            writer.writerows(lines)

    for d in data:
        coin = data[d]['USD']
        s = './crypto_data/' + d + '_Test_Data.csv'
        addString = ""
        with open(s, 'a') as fp:
            for key in coin:
                if key == 'PRICE' or key == 'VOLUMEDAYTO' or key == 'VOLUME24HOURTO' or key == 'MEDIAN' or key == 'CHANGEPCT24HOUR' or key == 'CHANGEPCTDAY' or key == 'CHANGEPCTHOUR':
                    if key == 'CHANGEPCT24HOUR' or key == 'CHANGEPCTDAY' or key == 'CHANGEPCTHOUR':
                        addString = addString + "," + coin[key]
                    else:
                        newstr = coin[key][2:].replace(",", "")
                        addString = addString + "," + newstr

            fp.write(str(int(time.time())) + "," + addString[1:] + '\n')
    ml.refresh_held_pending()
    ml.update_bittrex_coins()

    if total_bitcoin > satoshi_50k:
        ml.ml_buy_strat(total_bitcoin)
    else:
        print("INSUFFICIENT FUNDS-ML_STRAT")
    ml.ml_sell_strat()
    time.sleep(10)

def initialize_random_strat():
    total_slots = 5
    return RandCStrategy.RandomStrat(api, total_slots)
def run_random_strat():
    rcs.refresh_held_pending()
    rcs.update_bittrex_coins()

    if total_bitcoin > satoshi_50k:
        rcs.random_buy_strat(total_bitcoin)
    time.sleep(60)



def initialize_hodl_strat():
    markets_desired_gain = [('BTC-LTC', 10), ('BTC-XRP', 5)]
    total_slots = 5
    return HUStrategy.HodlStrat(api, markets_desired_gain, total_slots)
def run_hodl_strat():
    hus.refresh_held_pending()
    hus.update_bittrex_coins()

    if total_bitcoin > satoshi_50k and len(hus.markets_desired_gain) != 0:
        hus.hodl_buy_strat(total_bitcoin)

    hus.hodl_sell_strat()
    time.sleep(60)





def initialize_keltner_strat():
    keltner_period = 10
    keltner_multiplier = 1.5
    keltner_slots = 2
    lowest_rank = 50

    ks_instance = KCStrategy.KeltnerStrat(api, keltner_period, keltner_multiplier, keltner_slots, lowest_rank)
    ks_instance.add_bittrex_coins_to_keltner_coins(ks_instance.coinmarketcap_coins)
    return ks_instance

def run_keltner_strat():
    kcs.refresh_held_pending()
    kcs.coinmarketcap_coins = kcs.update_coinmarketcap_coins()
    kcs.bittrex_coins = kcs.update_bittrex_coins(kcs.coinmarketcap_coins)
    kcs.update_keltner_coins()

    if total_bitcoin > satoshi_50k:
        kcs.keltner_buy_strat(total_bitcoin)

        kcs.keltner_sell_strat()
    time.sleep(10)


def initialize_percent_strat():
    utils.init_global_return()
    buy_min_percent = 30
    buy_max_percent = 1000
    buy_desired_1h_change = 10
    total_slots = 4
    data_ticks_to_save = 180

    return PWStrategy.PercentStrat(api, buy_min_percent, buy_max_percent, buy_desired_1h_change, total_slots, data_ticks_to_save)
def run_percent_strat():
    pws.refresh_held_pending_history()
    pws.update_bittrex_coins()

    pws.historical_coin_data = utils.update_historical_coin_data(pws.historical_coin_data, pws.bittrex_coins, pws.data_ticks_to_save)

    pws.update_coinmarketcap_coins()
    if total_bitcoin > satoshi_50k:
        pws.percent_buy_strat(total_bitcoin)

    pws.percent_sell_strat()
    time.sleep(10)

api = utils.get_api()


time_until_cancel_processing_order_minutes = 5
satoshi_50k = 0.0005

# rcs = initialize_random_strat()
# kcs = initialize_keltner_strat()
# pws = initialize_percent_strat()
# hus = initialize_hodl_strat()

# need to go together
# rgdata = initialize_reddit_strat()
# trs = initialize_buy_low_sell_high_strat()

#
ml = initialize_ML_strat()

utils.print_and_write_to_logfile("\n** Run Start At: " + utils.get_date_time() + " **\n")

while True:
    try:

        total_bitcoin = utils.get_total_bitcoin(api)
        print(str(total_bitcoin));
        orders_query = api.get_open_orders("")

        if orders_query['success']:
            orders = orders_query['result']
            clean_orders(orders)
            update_pending_orders(orders)

        # run_random_strat()
        # run_keltner_strat()
        # run_percent_strat()
        # run_hodl_strat()

        # run_reddit_strat() # dont run this: run by buy low sell high
        # run_buy_low_sell_high_strat()

        run_ml_strat()

        time.sleep(60)

    except Exception as e:
        utils.print_and_write_to_logfile(traceback.format_exc())
