from random import randrange
import pandas as pd

import Utils as utils
import sys
import tensorflow as tf
from sklearn import preprocessing
import numpy as np

sys.path.append('../../')


class MLStrat:
    satoshi_50k = 0.0005

    def __init__(self,api,total_slots):
        self.api = api
        self.total_slots = total_slots
        self.bittrex_coins = utils.get_updated_bittrex_coins()
        self.held_coins = utils.file_to_json("cryptoCoinsData/currentlyHeldCoins.json")
        self.pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")
        self.gatherPeriodLength = 0

    def preprocess_df(self,df):
        # print(df)
        df.dropna(inplace=True)
        sequential_data = []

        for i in df.values:#i:row
            sequential_data.append([np.array(i)])

        return np.array(sequential_data)

    def ml_buy_strat(self, total_bitcoin):
        ratios = ["BTC_data", "LTC_data", "BCH_data", "ETH_data", "EOS_data", "XRP_data"]
        self.held_coins = utils.file_to_json("cryptoCoinsData/currentlyHeldCoins.json")
        self.pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")
        self.history_coins = utils.file_to_json("cryptoCoinsData/mlHeldCoinRecordPrice.json")
        for coin_to_buy in ratios:
            if coin_to_buy == 'BTC_data':
                model = tf.keras.models.load_model("models/CRYPTOCOIN_TRAINED-30-0.836-BTC_data.model");
            if coin_to_buy == 'LTC_data':
                model = tf.keras.models.load_model("models/CRYPTOCOIN_TRAINED-30-0.809-LTC_data.model");
            if coin_to_buy == 'BCH_data':
                model = tf.keras.models.load_model("models/CRYPTOCOIN_TRAINED-30-0.806-BCH_data.model");
            if coin_to_buy == 'ETH_data':
                model = tf.keras.models.load_model("models/CRYPTOCOIN_TRAINED-30-0.841-ETH_data.model");
            if coin_to_buy == 'EOS_data':
                model = tf.keras.models.load_model("models/CRYPTOCOIN_TRAINED-30-0.833-EOS_data.model");
            if coin_to_buy == 'XRP_data':
                model = tf.keras.models.load_model("models/CRYPTOCOIN_TRAINED-30-0.842-XRP_data.model");

            main_df = pd.DataFrame()
            ratios_1 = ["BTC_Test_Data", "LTC_Test_Data", "BCH_Test_Data", "ETH_Test_Data", "EOS_Test_Data", "XRP_Test_Data"]
            for ratio_1 in ratios_1:
                dataset = 'crypto_data/' + ratio_1 + '.csv'
                df = pd.read_csv(dataset,
                                 names=['TIME', 'PRICE', 'VOLUMEDAYTO', 'VOLUME24HOURTO', 'MEDIAN', 'CHANGEPCT24HOUR',
                                        'CHANGEPCTDAY', 'CHANGEPCTHOUR'])  # read in specific file
                df.rename(columns={"PRICE": ratio_1 + "_PRICE", "VOLUMEDAYTO": ratio_1 + "_VOLUMEDAYTO",
                                   "VOLUME24HOURTO": ratio_1 + "_VOLUME24HOURTO", "MEDIAN": ratio_1 + "_MEDIAN",
                                   "CHANGEPCT24HOUR": ratio_1 + "_CHANGEPCT24HOUR", "CHANGEPCTDAY": ratio_1 + "_CHANGEPCTDAY",
                                   "CHANGEPCTHOUR": ratio_1 + "_CHANGEPCTHOUR"}, inplace=True)

                df.set_index("TIME", inplace=True)

                if len(main_df) == 0:
                    main_df = df
                else:
                    main_df = main_df.join(df)

            testData = self.preprocess_df(main_df)
            testData.resize([1,50,42])
            prediction = model.predict([testData])
            print(prediction)

            if prediction[0][1] > 0.9:
                slots_open = self.total_slots - len(self.held_coins) - len(self.pending_orders['Buying']) - len(
                    self.pending_orders['Selling'])
                # slots_open = 1
                bitcoin_to_use = float(total_bitcoin / (slots_open + .25))
                if bitcoin_to_use < self.satoshi_50k:
                    utils.print_and_write_to_logfile("Order less than 50k satoshi (~$2). Attempted to use: $" + str(
                        utils.bitcoin_to_USD(bitcoin_to_use)) + ", BTC: " + str(bitcoin_to_use))
                    return
                coins_pending_buy = [market for market in self.pending_orders['Buying']]
                coins_pending_sell = [market for market in self.pending_orders['Selling']]

                market = 'BTC-'+coin_to_buy[:3]
                if market not in self.held_coins and market not in coins_pending_buy and market not in coins_pending_sell:
                    coin_price = 0
                    if market in self.bittrex_coins and self.bittrex_coins[market]['Last'] is not None:
                        coin_price = float(self.bittrex_coins[market]['Last'])
                    if coin_price != 0:
                        amount = bitcoin_to_use / coin_price
                    else:
                        amount = 0
                    if amount > 0:
                        percent_change_24h = utils.get_percent_change_24h(self.bittrex_coins[market])
                        result = utils.buy(self.api, market, amount, coin_price, percent_change_24h, 0, 0)
                        if result['success']:
                            self.history_coins[market] = coin_price
                            utils.json_to_file(self.history_coins, "cryptoCoinsData/heldCoinsHighestPriceRecorded.json")

                            utils.print_and_write_to_logfile(
                                'Buy order of' + str(amount) + 'of' + market + ' successful')
                        else:
                            utils.print_and_write_to_logfile(
                                'Buy order of' + str(amount) + 'of' + market + ' unsuccessful')

    def ml_sell_strat(self):
        ml_held_markets = utils.file_to_json("cryptoCoinsData/mlHeldCoinRecordPrice.json")
        for market in ml_held_markets:
            cur_price = float(self.bittrex_coins[market[0]]['Last'])
            change = utils.percent_change(market[1], cur_price)

            if change >= 5:
                coin_to_sell = utils.get_second_market_coin(market[0])
                balance = self.api.get_balance(coin_to_sell)
                if balance['success']:
                    amount = float(balance['result']['Available'])
                    utils.sell(self.api, amount, market, self.bittrex_coins)
                    del ml_held_markets[market]
                    utils.json_to_file(ml_held_markets,"cryptoCoinsData/mlHeldCoinRecordPrice.json")
                else:
                    utils.print_and_write_to_logfile("Could not retrieve balance: " + balance['message'])



    def refresh_held_pending(self):
        self.held_coins = utils.file_to_json("cryptoCoinsData/currentlyHeldCoins.json")
        self.pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")
    def update_bittrex_coins(self):
        self.bittrex_coins = utils.get_updated_bittrex_coins()