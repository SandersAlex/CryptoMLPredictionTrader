import sys

sys.path.append('../../')
import Utils as utils
import re
import operator

class RedditStrat:
    satoshi_50k = 0.0005

    def __init__(self, bittrex_api, reddit_api, total_slots):
        self.bittrex_api = bittrex_api
        self.reddit_api = reddit_api
        self.total_slots = total_slots

        self.bittrex_coins = utils.get_updated_bittrex_coins()
        self.held_coins = utils.file_to_json("cryptoCoinsData/currentlyHeldCoins.json")
        self.pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")

        self.coins_ranked_by_mentions = ('CoinName', 0)
        self.coins_ranked_by_upvotes = ('CoinName', 0)
        self.coins_ranked_by_upvotes_and_sentiment = ('CoinName', 0)

        self.initialize_reddit_coins()
        self.mentioned_words = {}

    def reddit_buy_strat(self, total_bitcoin):
        coin_rank = 0
        coins_to_dismiss = utils.file_to_json('cryptoCoinsData/coinIgnore.json')["coins_to_dismiss"]

        slots_open = self.total_slots - len(self.held_coins) - len(self.pending_orders['Buying']) - len(
            self.pending_orders['Selling'])

        while coin_rank < 5:
            cur_coin = self.rank_by_upvotes()[coin_rank][0]
            if cur_coin not in coins_to_dismiss:
                market = "BTC-" + cur_coin
                coins_pending_buy = [market for market in self.pending_orders['Buying']]
                coins_pending_sell = [market for market in self.pending_orders['Selling']]

                if market not in self.held_coins and market not in coins_pending_buy and market not in \
                        coins_pending_sell:
                    bitcoin_to_use = float(total_bitcoin / (slots_open + .25))

                    if self.bittrex_coins[market]['Last'] is not None:
                        coin_price = float(self.bittrex_coins[market]['Last'])
                    # different
                    if coin_price != 0:
                        amount = bitcoin_to_use / coin_price
                    else:
                        amount = 0


                    # coin_price = float(self.bittrex_coins[market]['Last'])
                    # amount = bitcoin_to_use / coin_price

                    if amount > 0:
                        percent_change_24h = utils.get_percent_change_24h(self.bittrex_coins[market])
                        buy_request = utils.buy(self.api, market, amount, coin_price, percent_change_24h, 0)
                        if buy_request['success']:
                            utils.print_and_write_to_logfile(
                                "Buy order of " + str(amount) + " " + market + " requested")
                        else:
                            utils.print_and_write_to_logfile(buy_request['message'])
            if cur_coin not in coins_to_dismiss:
                coin_rank += 1

    def initialize_reddit_coins(self):
        market_names = utils.get_bittrex_market_names()
        market_names['submissions'] = []
        utils.json_to_file(market_names, 'cryptoCoinsData/coinRedditData.json')

    def add_to_words_coins(self, s, upvotes, created):
        split_words = s.split()
        for word in split_words:
            if word not in self.mentioned_words:
                self.mentioned_words[word] = [(s, upvotes, created)]
            else:
                self.mentioned_words[word].append((s, upvotes, created))

    def update_reddit_coins(self):
        self.mentioned_words = {}
        reddit_coins = utils.file_to_json('cryptoCoinsData/coinRedditData.json')
        for submission in self.reddit_api.subreddit('CryptoCurrency').top('day'):
            if submission not in reddit_coins['submissions']:
                self.add_to_words_coins(submission.title, submission.score, submission.created)

                reddit_coins = self.find_mentions(submission.title, reddit_coins, str(submission), submission.created,
                                                  submission.score)
                for comment in submission.comments:
                    try:
                        reddit_coins = self.find_mentions(comment.body, reddit_coins, str(comment), comment.created,
                                                          comment.score)
                        self.add_to_words_coins(comment.body, comment.score, comment.created)
                    except:
                        pass
            reddit_coins['submissions'].append(str(submission))
        utils.json_to_file(reddit_coins, 'cryptoCoinsData/coinRedditData.json')
        self.rank_by_mentions()
        self.rank_by_upvotes()
        self.rank_by_upvotes_and_sentiment()

    def add_to_reddit_coin(self, reddit_coins, symbol, mentioned_id, mentioned_time, string, upvotes):
        reddit_coins[symbol]['mentioned_ids'].append(mentioned_id)
        reddit_coins[symbol]['mentioned_times'].append(mentioned_time)
        reddit_coins[symbol]['text'].append(string)
        reddit_coins[symbol]['upvotes'].append(upvotes)
        reddit_coins[symbol]['sentiments'].append(utils.get_sentiment(string))
        return reddit_coins


    def find_mentions(self, string, reddit_coins, mentioned_id, mentioned_time, upvotes):
        submissions = reddit_coins['submissions']
        del reddit_coins['submissions']
        coins_with_common_names = utils.file_to_json('cryptoCoinsData/coinIgnore.json')['coins_with_common_names']

        symbols_and_names_map = {}
        for symbol in reddit_coins:
            if symbol not in coins_with_common_names:
                symbols_and_names_map[symbol] = symbol
                full_name = reddit_coins[symbol]['full_name'].lower()
                symbols_and_names_map[full_name] = symbol
        already_seen = set()
        for word in string.split(" "):
            lower_case_word = word.lower()
            if lower_case_word in symbols_and_names_map:
                if lower_case_word not in already_seen and symbols_and_names_map[lower_case_word] not in lower_case_word:
                    reddit_coins = self.add_to_reddit_coin(reddit_coins, symbols_and_names_map[lower_case_word], mentioned_id,
                                                           mentioned_time, string,
                                                           upvotes)
                already_seen.add(lower_case_word)
                already_seen.add(symbols_and_names_map[lower_case_word])
        reddit_coins['submissions'] = submissions
        return reddit_coins

    def rank_by_mentions(self):
        reddit_coins = utils.file_to_json('cryptoCoinsData/coinRedditData.json')
        del reddit_coins['submissions']
        ranked_coins = {}
        for coin in reddit_coins:
            ranked_coins[coin] = len(reddit_coins[coin]['mentioned_ids'])
        sorted_coins = sorted(ranked_coins.items(), key=operator.itemgetter(1), reverse=True)
        self.coins_ranked_by_mentions = sorted_coins

    def rank_by_upvotes_and_sentiment(self):
        reddit_coins = utils.file_to_json('cryptoCoinsData/coinRedditData.json')
        del reddit_coins['submissions']
        ranked_coins = {}

        for coin in reddit_coins:
            upvote_list = reddit_coins[coin]['upvotes']
            sentiment_list = reddit_coins[coin]['sentiments']

            rank = 0
            for i in range(len(upvote_list)):
                rank += upvote_list[i] * sentiment_list[i]
                ranked_coins[coin] = rank

        sorted_coins = sorted(ranked_coins.items(), key=operator.itemgetter(1), reverse=True)
        self.coins_ranked_by_upvotes_and_sentiment = sorted_coins

    def rank_by_upvotes(self):
        reddit_coins = utils.file_to_json('cryptoCoinsData/coinRedditData.json')
        del reddit_coins['submissions']
        ranked_coins = {}
        for coin in reddit_coins:
            ranked_coins[coin] = sum(reddit_coins[coin]['upvotes'])
        sorted_coins = sorted(ranked_coins.items(), key=operator.itemgetter(1), reverse=True)
        self.coins_ranked_by_upvotes = sorted_coins

    def refresh_held_pending(self):
        self.held_coins = utils.file_to_json("cryptoCoinsData/currentlyHeldCoins.json")
        self.pending_orders = utils.file_to_json("cryptoCoinsData/pendingList.json")

    def update_bittrex_coins(self):
        self.bittrex_coins = utils.get_updated_bittrex_coins()

    def sort_comments(self, upvote_list, text_list, time_list):
        tuple_list = []
        for i in range(len(upvote_list)):
            tuple_list.append((upvote_list[i], text_list[i], time_list[i]))
        return sorted(tuple_list, key=lambda tup: tup[0], reverse=True)

    def add_to_top_coins(self, market, top_coins, rank):
        coin_info = self.bittrex_coins[market]
        t = {}
        t['market'] = market
        t['cur_price'] = coin_info['Last']
        t['24h_change'] = utils.get_percent_change_24h(coin_info)

        top_coins[rank] = t

    def store_top_10_data(self):
        most_mentioned = self.coins_ranked_by_mentions
        reddit_coins = utils.file_to_json('cryptoCoinsData/coinRedditData.json')
        count = 10
        out_string = ""
        top_coins = {}
        rank = 0
        for pair in most_mentioned:
            if count <= 0:
                break
            count -= 1
            symbol = pair[0]
            coin_data = reddit_coins[symbol]
            out_string += "*********************** " + symbol + " ***********************" + "\n"

            self.add_to_top_coins("BTC-" + symbol, top_coins, rank)
            rank += 1

            upvote_list = coin_data['upvotes']
            text_list = coin_data['text']
            time_list = coin_data['mentioned_times']

            sorted_comments = self.sort_comments(upvote_list, text_list, time_list)

            for i in range(len(upvote_list)):
                out_string += str(sorted_comments[i][0]) + " : " + utils.time_stamp_to_date(
                    sorted_comments[i][2]) + " : " + sorted_comments[i][1] + "\n\n"
            out_string += "\n\n"
        utils.json_to_file(top_coins, 'cryptoCoinsData/coinRedditDataTopTen.json')
        utils.clear_and_write_to_file('cryptoLogs/redditPeopleData.txt', out_string)