import Utils as utils
import sys
sys.path.append('../../')


class HodlStrat:
    satoshi_50k = 0.0005

    def __init__(self, api, markets_desired_gain, total_slots):
        self.api = api
        self.markets_desired_gain = markets_desired_gain
        self.total_slots = total_slots

        self.bittrex_coins = utils.get_updated_bittrex_coins()

        self.held_coins = utils.file_to_json("cryptoCoinsData/currentlyHeldCoins.json")
        self.pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")

    def hodl_buy_strat(self, total_bitcoin):
        slots_open = self.total_slots - len(self.held_coins) - len(self.pending_orders['Buying']) - len(
            self.pending_orders['Selling'])
        # slots_open=1;
        bitcoin_to_use = float(total_bitcoin / (slots_open + .25))
        failed_pairs = []

        for market_gain_pair in self.markets_desired_gain:
            market = market_gain_pair[0]
            desired_gain = market_gain_pair[1]

            coins_pending_buy = [market for market in self.pending_orders['Buying']]
            coins_pending_sell = [market for market in self.pending_orders['Selling']]

            if market not in self.held_coins and market not in coins_pending_buy and market not in coins_pending_sell:

                if self.bittrex_coins[market]['Last'] is not None:
                    coin_price = float(self.bittrex_coins[market]['Last'])
                if coin_price != 0:
                    amount = bitcoin_to_use / coin_price
                else:
                    amount = 0

                if amount > 0:
                    percent_change_24h = utils.get_percent_change_24h(self.bittrex_coins[market])
                    result = utils.buy(self.api, market, amount, coin_price, percent_change_24h, desired_gain, 0)
                    if result['success']:
                        utils.print_and_write_to_logfile('Buy order of' + str(amount) + 'of' + market + 'successful')
                    else:
                        failed_pairs.append(market_gain_pair)
                        utils.print_and_write_to_logfile('Buy order of' + str(amount) + 'of' + market + 'unsuccessful')

        self.markets_desired_gain = failed_pairs

    def hodl_sell_strat(self):
        for market in self.held_coins:
            cur_price = float(self.bittrex_coins[market]['Last'])
            bought_price = self.held_coins[market]['price_bought']
            change = utils.percent_change(bought_price, cur_price)

            desired_gain = self.held_coins[market]['desired_gain']

            if change >= desired_gain:
                coin_to_sell = utils.get_second_market_coin(market)
                balance = self.api.get_balance(coin_to_sell)
                if balance['success']:
                    amount = float(balance['result']['Available'])
                    utils.sell(self.api, amount, market, self.bittrex_coins)
                else:
                    utils.print_and_write_to_logfile("Could not retrieve balance: " + balance['message'])

    def refresh_held_pending(self):
        self.held_coins = utils.file_to_json("cryptoCoinsData/currentlyHeldCoins.json")
        self.pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")

    def update_bittrex_coins(self):
        self.bittrex_coins = utils.get_updated_bittrex_coins()