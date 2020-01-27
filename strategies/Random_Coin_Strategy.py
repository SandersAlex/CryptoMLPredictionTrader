from random import randrange

import Utils as utils
import sys
sys.path.append('../../')


class RandomStrat:
    satoshi_50k = 0.0005


    def __init__(self,api, total_slots):
        self.api = api
        self.total_slots = total_slots
        self.bittrex_coins = utils.get_updated_bittrex_coins()
        self.held_coins = utils.file_to_json("cryptoCoinsData/currentlyHeldCoins.json")
        self.pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")

    def buy(self, market, total_bitcoin):
        coins_pending_buy = [market for market in self.pending_orders['Buying']]
        coins_pending_sell = [market for market in self.pending_orders['Selling']]

        print("total bitcoin: " + str(total_bitcoin))


        if market not in self.held_coins and market not in coins_pending_buy and market not in coins_pending_sell:
            slots_open = self.total_slots - len(self.held_coins) - len(self.pending_orders['Buying']) - len(
                self.pending_orders['Selling'])
            # slots_open = 1;
            bitcoin_to_use = float(total_bitcoin / (slots_open + .25))
            if self.bittrex_coins[market]['Last'] is not None:
                coin_price = float(self.bittrex_coins[market]['Last'])
            if coin_price!= 0:
                amount = bitcoin_to_use / coin_price
            else:
                amount = 0
            if amount > 0:
                percent_change_24h = utils.get_percent_change_24h(self.bittrex_coins[market])
                if(total_bitcoin > 0.001):
                    result = utils.buy(self.api, market, amount, coin_price, percent_change_24h, 0, 0)
                if result['success']:
                    utils.print_and_write_to_logfile('Buy order of' + str(amount) + 'of' + market + 'successful')
                    return True
                else:
                    utils.print_and_write_to_logfile('Buy order of' + str(amount) + 'of' + market + 'Unsuccessful')
                    return False
        return False



    def random_buy_strat(self, total_bitcoin):
        bittrex_markets = [market for market in self.bittrex_coins]
        i = 0
        established_markets = ['BTC-ETH', 'BTC-LTC', 'BTC-BTC', 'BTC-NEO', 'BTC-OMG', 'BTC-ARK', 'BTC-XRP', 'BTC-GNT']
        while i < self.total_slots:
            rand_coin = bittrex_markets[randrange(len(bittrex_markets))]
            if not rand_coin.startswith('ETH') and not rand_coin.startswith('USDT') and rand_coin not in established_markets:
                result = self.buy(rand_coin, total_bitcoin)
                if result:
                    i += 1





    def refresh_held_pending(self):
        self.held_coins = utils.file_to_json("cryptoCoinsData/currentlyHeldCoins.json")
        self.pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")
    def update_bittrex_coins(self):
        self.bittrex_coins = utils.get_updated_bittrex_coins()