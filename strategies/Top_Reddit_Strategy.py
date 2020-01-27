import Utils as utils
import sys

sys.path.append('../../')


class BuyLowSellHighStrat:
    satoshi_50k = 0.0005

    def __init__(self, api, desired_gain, desired_low_point, total_slots):
        self.api = api
        self.desired_gain = desired_gain
        self.desired_low_point = desired_low_point
        self.total_slots = total_slots


        self.count_until_reddit_strat = 0

        self.bittrex_coins = utils.get_updated_bittrex_coins()

        self.held_coins = utils.file_to_json("cryptoCoinsData/currentlyHeldCoins.json")
        self.pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")
        self.fill_low_bars()
    def fill_low_bars(self):
        coin_low_bars = {}
        for market in self.bittrex_coins:
            coin_low_bars[market] = self.desired_low_point
        utils.json_to_file(coin_low_bars, 'cryptoCoinsData/keltnerLowerBound.json')

    def low_high_buy_strat(self, total_bitcoin):

        top_reddit_coins = utils.file_to_json('cryptoCoinsData/coinRedditDataTopTen.json')
        markets_to_ignore = ['BTC-ETH', 'BTC-BTC']

        for rank in range(len(top_reddit_coins)):
            market = top_reddit_coins[str(rank)]['market']
            if market not in markets_to_ignore:
                slots_open = self.total_slots - len(self.held_coins) - len(self.pending_orders['Buying']) - len(
                    self.pending_orders['Selling'])
                bitcoin_to_use = float(total_bitcoin / (slots_open + .25))
                coins_pending_buy = [market for market in self.pending_orders['Buying']]
                coins_pending_sell = [market for market in self.pending_orders['Selling']]

                if market not in self.held_coins and market not in coins_pending_buy and market not in coins_pending_sell:
                        percent_change_24h = utils.get_percent_change_24h(self.bittrex_coins[market])
                        coin_low_bars = utils.file_to_json('cryptoCoinsData/keltnerLowerBound.json')
                        low_bar = coin_low_bars[market]

                        if percent_change_24h <= self.desired_low_point and percent_change_24h <= low_bar:
                            coin_low_bars[market] = low_bar - 10
                            utils.json_to_file(coin_low_bars, 'cryptoCoinsData/keltnerLowerBound.json')

                        elif low_bar != self.desired_low_point and percent_change_24h > low_bar + 10:
                            self.update_bittrex_coins()

                            if self.bittrex_coins[market]['Last'] is not None:
                                coin_price = float(self.bittrex_coins[market]['Last'])
                            if coin_price != 0:
                                amount = bitcoin_to_use / coin_price
                            else:
                                amount = 0
                            if amount > 0:
                                print(amount)
                                result = utils.buy(self.api, market, amount, coin_price, percent_change_24h,
                                                   self.desired_gain, 0)
                                if not result['success']:
                                    utils.print_and_write_to_logfile("Failed to make buy order " + market)
                                else:
                                    utils.print_and_write_to_logfile("Attempting buy order of " + str(amount) + " of " + market)
    def low_high_sell_strat(self):
        for market in self.held_coins:
            cur_price = float(self.bittrex_coins[market]['Last'])
            bought_price = self.held_coins[market]['price_bought']
            change = utils.percent_change(bought_price, cur_price)

            desired_gain = self.held_coins[market]['desired_gain']
            high_bar = self.held_coins[market]['high_bar']

            if change >= desired_gain and change >= high_bar:
                self.held_coins[market]['high_bar'] = high_bar + 10
                utils.json_to_file(self.held_coins, 'cryptoCoinsData/currentlyHeldCoins.json')
            elif high_bar != desired_gain and change < high_bar - 10:
                coin_to_sell = utils.get_second_market_coin(market)
                balance = self.api.get_balance(coin_to_sell)
                if balance['success']:
                    amount = float(balance['result']['Available'])
                    self.update_bittrex_coins()
                    utils.sell(self.api, amount, market, self.bittrex_coins)
                else:
                    utils.print_and_write_to_logfile("Could not retrieve balance: " + balance['message'])

    def refresh_held_pending(self):
        self.held_coins = utils.file_to_json("cryptoCoinsData/currentlyHeldCoins.json")
        self.pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")
    def update_bittrex_coins(self):
        self.bittrex_coins = utils.get_updated_bittrex_coins()
