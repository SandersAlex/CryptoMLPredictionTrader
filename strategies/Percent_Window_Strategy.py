import Utils as utils
import sys
sys.path.append('../../')


class PercentStrat:
    satoshi_50k = 0.0005

    def __init__(self, api, buy_min_percent, buy_max_percent, buy_desired_1h_change, total_slots, data_ticks_to_save):
        self.api = api
        self.buy_min_percent = buy_min_percent
        self.buy_max_percent = buy_max_percent
        self.buy_desired_1h_change = buy_desired_1h_change
        self.total_slots = total_slots
        self.data_ticks_to_save = data_ticks_to_save

        self.bittrex_coins = utils.get_updated_bittrex_coins()
        self.coinmarketcap_coins = utils.get_updated_coinmarketcap_coins()

        self.historical_coin_data = {}

        self.refresh_held_pending_history()

        self.held_coins = utils.file_to_json("cryptoCoinsData/currentlyHeldCoins.json")
        self.pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")
        self.history_coins = utils.file_to_json("cryptoCoinsData/heldCoinsHighestPriceRecorded.json")

    def percent_buy_strat(self, total_bitcoin):
        symbol_1h_change_pairs = utils.get_coinmarketcap_1hr_change(self.coinmarketcap_coins)
        slots_open = self.total_slots - len(self.held_coins) - len(self.pending_orders['Buying']) - len(
            self.pending_orders['Selling'])

        if slots_open <= 0:
            utils.print_and_write_to_logfile("0 slots open")
            return

        # slots_open = 1;
        bitcoin_to_use = float(total_bitcoin / slots_open * 0.990)

        if bitcoin_to_use < self.satoshi_50k:
            utils.print_and_write_to_logfile("Order less than 50k satoshi (~$2). Attempted to use: $" + str(
                utils.bitcoin_to_USD(bitcoin_to_use)) + ", BTC: " + str(bitcoin_to_use))
            return

        for hist_coin in self.history_coins:
            bitcoin_to_use = float(total_bitcoin / slots_open * 0.990)
            coin_price = float(self.bittrex_coins[hist_coin]['Last'])
            # update highest price recorded while held
            if hist_coin in self.held_coins:
                highest_recorded_price = float(self.history_coins[hist_coin])
                if coin_price > highest_recorded_price:
                    self.history_coins[hist_coin] = coin_price
                    utils.json_to_file(self.history_coins, "cryptoCoinsData/heldCoinsHighestPriceRecorded.json")

            elif float(self.history_coins[hist_coin])*1.1 < coin_price:
                coins_pending_buy = [market for market in self.pending_orders['Buying']]
                coins_pending_sell = [market for market in self.pending_orders['Selling']]

                if hist_coin not in coins_pending_buy and hist_coin not in coins_pending_sell:
                    amount = bitcoin_to_use / coin_price
                    if amount > 0:
                        coin_to_buy = utils.get_second_market_coin(hist_coin)
                        coin_1h_change = float(symbol_1h_change_pairs[coin_to_buy])
                        percent_change_24h = utils.get_percent_change_24h(self.bittrex_coins[hist_coin])
                        utils.buy(self.api, hist_coin, amount, coin_price, percent_change_24h, 0, coin_1h_change)

                        slots_open = self.total_slots - len(self.held_coins) - len(self.pending_orders['Buying']) - len(
                            self.pending_orders['Selling'])
                        bitcoin_to_use = float(total_bitcoin / slots_open * 0.990)

        for coin in self.bittrex_coins:
            percent_change_24h = utils.get_percent_change_24h(self.bittrex_coins[coin])
            if self.buy_min_percent <= percent_change_24h <= self.buy_max_percent:
                rank = utils.get_ranks(self.coinmarketcap_coins)
                if utils.get_second_market_coin(coin) in rank:
                    coin_rank = rank[utils.get_second_market_coin(coin)]
                else:
                    coin_rank = 0;
                coin_volume = self.bittrex_coins[coin]['Volume']
                if float(coin_rank) > 50 and coin not in self.history_coins and coin_volume > 200:
                    market = self.bittrex_coins[coin]['MarketName']
                    if market.startswith('ETH'):
                        break
                    if market.startswith('BTC'):
                        coin_to_buy = utils.get_second_market_coin(market)
                        coin_1h_change = float(symbol_1h_change_pairs[coin_to_buy])

                        coins_pending_buy = [market for market in self.pending_orders['Buying']]
                        coins_pending_sell = [market for market in self.pending_orders['Selling']]

                        if market not in self.held_coins and market not in coins_pending_buy and market not in \
                                coins_pending_sell and coin_1h_change > self.buy_desired_1h_change:

                            coin_price = float(self.bittrex_coins[coin]['Last'])
                            amount = bitcoin_to_use / coin_price
                            if amount > 0:
                                buy_request = utils.buy(self.api, market, amount, coin_price, percent_change_24h, 0, coin_1h_change)
                                if buy_request['success']:
                                    utils.print_and_write_to_logfile(
                                        "Buy order of " + str(amount) + " " + market + " requested")
                                    self.refresh_held_pending()
                                else:
                                    utils.print_and_write_to_logfile(buy_request['message'])

    def percent_sell_strat(self):
        held_markets = [market for market in self.held_coins]
        for coin_market in held_markets:
            current_high = self.history_coins[coin_market]
            coin_price = float(self.bittrex_coins[coin_market]['Last'])
            if coin_price < current_high * 0.97:
                coin_to_sell = utils.get_second_market_coin(coin_market)

                balance = self.api.get_balance(coin_to_sell)
                amount = 0;
                if balance['success']:
                    if balance['result']['Available'] is not None:
                        amount = float(balance['result']['Available'])
                    if amount > 0:
                        utils.sell(self.api, amount, coin_market, self.bittrex_coins)
                else:
                    utils.print_and_write_to_logfile("Could not retrieve balance: " + balance['message'])

    def refresh_held_pending_history(self):
        self.held_coins = utils.file_to_json("cryptoCoinsData/currentlyHeldCoins.json")
        self.pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")
        self.history_coins = utils.file_to_json("cryptoCoinsData/heldCoinsHighestPriceRecorded.json")

    def update_bittrex_coins(self):
        self.bittrex_coins = utils.get_updated_bittrex_coins()

    def update_coinmarketcap_coins(self):
        self.coinmarketcap_coins = utils.get_updated_coinmarketcap_coins()
