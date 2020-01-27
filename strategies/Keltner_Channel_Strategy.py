import Utils as utils
import sys
sys.path.append('../../')


class KeltnerStrat:
    def __init__(self, api, keltner_period, keltner_multiplier, keltner_slots, lowest_rank):
        self.api = api
        self.keltner_period = keltner_period
        self.keltner_multiplier = keltner_multiplier
        self.keltner_slots = keltner_slots
        self.lowest_rank = lowest_rank

        # get keltner coins
        self.keltner_coins = utils.file_to_json("cryptoCoinsData/keltnerStratCoins.json")
        # not util:
        self.coinmarketcap_coins = self.update_coinmarketcap_coins()
        #
        self.bittrex_coins = self.update_bittrex_coins(self.coinmarketcap_coins)

        self.held_coins = utils.file_to_json("cryptoCoinsData/currentlyHeldCoins.json")
        self.pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")

        self.reset_keltner_coins()

        self.ten_second_count = 0

    def update_coinmarketcap_coins(self):
        return utils.get_ranks(utils.get_updated_coinmarketcap_coins())
    def update_bittrex_coins(self, coinmarketcap_coins):
        bittrex_data = utils.query_url("https://bittrex.com/api/v1.1/public/getmarketsummaries")['result']
        coins = {}
        for coin in bittrex_data:
            symbol = utils.get_second_market_coin(coin['MarketName'])
            if symbol in coinmarketcap_coins:
                coin_rank = int(coinmarketcap_coins[symbol])
                if coin_rank <= self.lowest_rank:
                    key = coin['MarketName']
                    coins[key] = coin
        return coins
    def reset_keltner_coins(self):
        self.keltner_coins = utils.file_to_json("cryptoCoinsData/keltnerStratCoins.json")
        for coin in self.keltner_coins:
            self.keltner_coins[coin]['price_data_minutes'] = []
            self.keltner_coins[coin]['price_data_seconds'] = []
            self.keltner_coins[coin]['tr_data'] = []
            self.keltner_coins[coin]['atr_data'] = []
            self.keltner_coins[coin]['ema_data'] = []
            self.keltner_coins[coin]['upper_band_data'] = []
            self.keltner_coins[coin]['middle_band_data'] = []
            self.keltner_coins[coin]['lower_band_data'] = []
        utils.json_to_file(self.keltner_coins, "cryptoCoinsData/keltnerStratCoins.json")

    def refresh_held_pending(self):
        self.held_coins = utils.file_to_json("cryptoCoinsData/currentlyHeldCoins.json")
        self.pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")

    def update_highest_price(self, market, highest_price_history, cur_price):
        if market not in highest_price_history:
            highest_price_history[market] = cur_price
        else:
            if highest_price_history[market] < cur_price:
                highest_price_history[market] = cur_price
        return highest_price_history

    def update_keltner_coins(self):
        highest_price_history = utils.file_to_json('cryptoCoinsData/heldCoinsHighestPriceRecorded.json')

        for market in self.keltner_coins:
            if market in self.bittrex_coins:
                bittrex_coin = self.bittrex_coins[market]
                cur_price = bittrex_coin['Last']
                self.keltner_coins[market]['price_data_seconds'].append(cur_price)

                highest_price_history = self.update_highest_price(market, highest_price_history, cur_price)

                if self.ten_second_count > 5:
                    self.keltner_coins[market]['price_data_minutes'].append(cur_price)
                    self.update_atr(market)
                    self.update_ema(market)
                    self.update_bands(market)
                    self.keltner_coins[market]['price_data_seconds'] =\
                        self.keltner_coins[market]['price_data_seconds'][-6:]

                    if len(self.keltner_coins[market]['price_data_minutes']) == self.keltner_period:
                        self.keltner_coins[market]['price_data_minutes'].pop(0)
        if self.ten_second_count > 5:
            self.ten_second_count = 0
        else:
            self.ten_second_count += 1

        utils.json_to_file(highest_price_history, 'cryptoCoinsData/heldCoinsHighestPriceRecorded.json')
        utils.json_to_file(self.keltner_coins, "cryptoCoinsData/keltnerStratCoins.json")

    def update_atr(self, market):
        if market in self.keltner_coins:

            keltner_coin = self.keltner_coins[market]

            price_data_minutes = keltner_coin['price_data_minutes']

            tr_data = keltner_coin['tr_data']

            cur_price = self.keltner_coins[market]['price_data_seconds'][-1]

            if len(price_data_minutes) == self.keltner_period:

                period_low = min(price_data_minutes)
                period_high = max(price_data_minutes)

                cur_tr = max([period_high - period_low, abs(period_high - cur_price), abs(period_low - cur_price)])

                if len(tr_data) == self.keltner_period:
                    atr_data = keltner_coin['atr_data']
                    if len(atr_data) == 0:
                        atr_data.append(sum(tr_data) / self.keltner_period)
                    else:
                        last_atr = atr_data[-1]

                        cur_atr = (last_atr * (self.keltner_period - 1) + cur_tr) / self.keltner_period

                        if len(atr_data) == self.keltner_period:
                            atr_data.pop(0)
                        atr_data.append(cur_atr)

                    keltner_coin['tr_data'].pop(0)

                keltner_coin['tr_data'].append(cur_tr)

    def update_ema(self, market):
        if market in self.keltner_coins:
            keltner_coin = self.keltner_coins[market]

            price_data_minutes = keltner_coin['price_data_minutes']

            if len(price_data_minutes) == self.keltner_period:

                cur_price = price_data_minutes[-1]
                ema_data = keltner_coin["ema_data"]

                if len(ema_data) == 0:
                    cur_ema = sum(price_data_minutes) / self.keltner_period

                else:
                    prev_ema = ema_data[-1]
                    multiplier = 2 / (self.keltner_period + 1) + prev_ema
                    cur_ema = (cur_price - prev_ema) * multiplier + prev_ema

                if len(ema_data) == self.keltner_period:
                    keltner_coin['ema_data'].pop(0)

                keltner_coin['ema_data'].append(cur_ema)

    def update_bands(self, market):
        if market in self.keltner_coins and len(self.keltner_coins[market]['atr_data']) == self.keltner_period:
            keltner_coin = self.keltner_coins[market]
            cur_ema = keltner_coin['ema_data'][-1]
            cur_atr = keltner_coin['atr_data'][-1]

            upper_band = cur_ema + cur_atr * self.keltner_multiplier
            middle_band = cur_ema
            lower_band = cur_ema - cur_atr * self.keltner_multiplier

            self.keltner_coins[market]['upper_band_data'].append(upper_band)
            self.keltner_coins[market]['middle_band_data'].append(middle_band)
            self.keltner_coins[market]['lower_band_data'].append(lower_band)
            if len(self.keltner_coins[market]['upper_band_data']) > self.keltner_period:
                self.keltner_coins[market]['upper_band_data'].pop(0)
                self.keltner_coins[market]['middle_band_data'].pop(0)
                self.keltner_coins[market]['lower_band_data'].pop(0)

    def get_upper_band(self, market):
        if market in self.keltner_coins and len(self.keltner_coins[market]['atr_data']) == self.keltner_period:
            keltner_coin = self.keltner_coins[market]
            if len(keltner_coin['upper_band']) > 0:
                return keltner_coin['upper_band'][-1]
        return -1

    def get_middle_band(self, market):
        if market in self.keltner_coins and len(self.keltner_coins[market]['atr_data']) == self.keltner_period:
            keltner_coin = self.keltner_coins[market]
            if len(keltner_coin['middle_band']) > 0:
                return keltner_coin['middle_band'][-1]
        return -1

    def get_lower_band(self, market):
        if market in self.keltner_coins and len(self.keltner_coins[market]['atr_data']) == self.keltner_period:
            keltner_coin = self.keltner_coins[market]
            if len(keltner_coin['lower_band']) > 0:
                return keltner_coin['lower_band'][-1]
        return -1

    def upward_cross(self, market, upper_middle_or_lower_data):
        cur_price = self.keltner_coins[market]['price_data_seconds'][-1]
        last_price = self.keltner_coins[market]['price_data_seconds'][-2]

        cur_band = self.keltner_coins[market][upper_middle_or_lower_data][-1]

        if last_price < cur_band < cur_price:
            return True
        return False

    def downward_cross(self, market, upper_middle_or_lower_data):
        cur_price = self.keltner_coins[market]['price_data_seconds'][-1]
        last_price = self.keltner_coins[market]['price_data_seconds'][-2]

        cur_band = self.keltner_coins[market][upper_middle_or_lower_data][-1]

        if cur_price < cur_band < last_price:
            return True
        return False



    def keltner_buy_strat(self, total_bitcoin):
        if len(self.keltner_coins['BTC-ETH']['upper_band_data']) > self.keltner_period:
            keltner_slots_open = self.keltner_slots - len(self.held_coins) - len(self.pending_orders['Buying']) - len(
                self.pending_orders['Selling'])

            for coin in self.keltner_coins:
                market = self.bittrex_coins[coin]['MarketName']
                lower_band_data = self.keltner_coins[market]['lower_band_data']
                if len(lower_band_data) == self.keltner_period:
                    coins_pending_buy = [market for market in self.pending_orders['Buying']]
                    coins_pending_sell = [market for market in self.pending_orders['Selling']]

                    if market not in self.held_coins and market not in coins_pending_buy and market not in coins_pending_sell:

                        cur_price = self.bittrex_coins[coin]['Last']
                        if self.upward_cross(market, 'lower_band_data'):
                            bitcoin_to_use = float(total_bitcoin / (keltner_slots_open + .25))
                            amount = bitcoin_to_use / cur_price
                            percent_change_24h = utils.get_percent_change_24h(coin)

                            utils.buy(self.api, market, amount, cur_price, percent_change_24h, 0)

                            keltner_slots_open = self.total_slots - len(self.held_coins) - len(
                                self.pending_orders['Buying']) - len(
                                self.pending_orders['Selling'])

    def keltner_sell_strat(self):
        if len(self.keltner_coins['BTC-ETH']['upper_band_data']) > self.keltner_period:
            for coin in self.keltner_coins:
                market = self.bittrex_coins[coin]['MarketName']
                lower_band_data = self.keltner_coins[market]['lower_band_data']

                if len(lower_band_data) == self.keltner_period:
                    market = self.bittrex_coins[coin]['MarketName']
                    coins_pending_buy = [market for market in self.pending_orders['Buying']]
                    coins_pending_sell = [market for market in self.pending_orders['Selling']]

                    highest_price_history = utils.file_to_json('cryptoCoinsData/heldCoinsHighestPriceRecorded.json')
                    if market not in coins_pending_buy and market not in coins_pending_sell and market in self.held_coins:

                        cur_price = price_data_seconds[-1]
                        price_data_seconds = self.keltner_coins[market]['price_data_seconds']

                        deviation = self.get_deviation_of_last_x(5, price_data_seconds)

                        highest_coin_price = highest_price_history[market]

                        if self.downward_cross(market, 'upper_band_data') or cur_price <= highest_coin_price - 2*deviation:
                            coin_to_sell = utils.get_second_market_coin(market)
                            balance = self.api.get_balance(coin_to_sell)
                            if balance['success']:
                                amount = float(balance['result']['Available'])
                                utils.sell(self.api, amount, market, self.bittrex_coins)
                            else:
                                utils.print_and_write_to_logfile("Could not retrieve balance: " + balance['message'])

    def get_deviation_of_last_x(self, x, array):
        deviation = 0
        for i in range(x):
            last_p = array[-(x+1) + i]
            cur_p = array[-x + i]
            deviation += (abs(cur_p - last_p))
        return deviation/x

    # populate Keltner data
    def add_bittrex_coins_to_keltner_coins(self, coinmarketcap_coins):
        self.keltner_coins = {}
        # get rank of all coins
        self.coinmarketcap_coins = self.update_coinmarketcap_coins()
        self.bittrex_coins = self.update_bittrex_coins(self.coinmarketcap_coins)
        for market in self.bittrex_coins:
            if market.startswith('BTC'):
                symbol = utils.get_second_market_coin(market)
                if symbol in coinmarketcap_coins:
                    coin_rank = int(coinmarketcap_coins[symbol])
                    if coin_rank <= self.lowest_rank:
                        t = {}
                        t['market'] = market
                        t['price_data_seconds'] = []
                        t['price_data_minutes'] = []
                        t['tr_data'] = []
                        t['atr_data'] = []
                        t['ema_data'] = []
                        t['upper_band_data'] = []
                        t['middle_band_data'] = []
                        t['lower_band_data'] = []

                        self.keltner_coins[market] = t

            utils.json_to_file(self.keltner_coins, "cryptoCoinsData/keltnerStratCoins.json")


