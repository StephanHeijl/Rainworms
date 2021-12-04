import matplotlib.pyplot as plt
import seaborn as sns
import pandas

from bots import *
from tree_bot import TreeBot
from tree_bot_relative import TreeBotRelative
from monte_carlo_tree_bot_relative import MCTreeBotRelative
from collections import defaultdict
from tqdm import tqdm
from multiprocessing import Pool, Manager
import time


def play_game(n):
    bots = {
        1: GreedyBot(3),
        2: TreeBotRelative("max"),
        3: MCTreeBotRelative("max", n_random_actions=1, n_sims=10),
        #4: MCTreeBotRelative("max", 1),
        # 3: GreedyNiceBot(3),
        # 4: GreedyNiceBot(3),
        #3: GreedyStealingBot(3),
        #4: GreedyStealingBot(3)
    }
    results = {}
    bot_names = [bot.name for bot in bots.values()]
    for i, bot in bots.items():
        if bot_names.count(bot.name) > 1:
            bot.name = bot.name + "_" + str(i)
    game = RainWorms(len(bots))
    bot_idx_mapping = []

    session = game.start_session()
    player, turn = next(session)
    while 1:
        player_n = player.player_n
        if player_n not in bot_idx_mapping:
            bot_idx_mapping.append(player_n)

        bot = bots[player_n]
        bot.game_loop(game, player, turn)
        try:
            player, turn = next(session)
        except StopIteration as return_value:

            for player_n, score in enumerate(return_value.value):
                bot_idx = bot_idx_mapping[player_n]
                results[bots[bot_idx].name] = score
            break
    return results


if __name__ == "__main__":
    n_games = 100
    pool_size = 1

    if pool_size > 1:
        pool = Pool(pool_size)
        # Play the games in parallel
        print("Started playing")
        start_time = time.time()
        results = pool.imap_unordered(play_game, range(n_games), chunksize=1)
        results = list(tqdm(results, total=n_games))
        pool.close()
        total_time = time.time() - start_time
    else:
        start_time = time.time()
        results = []
        for i in tqdm(range(n_games)):
            results.append(play_game(i))
        total_time = time.time() - start_time

    print(f"Played {n_games} in {total_time:.3f}s, {n_games/total_time:.1f} games per second.")

    results_df = pandas.DataFrame.from_dict(results)
    stats = results_df.agg(["mean", "std"]).T
    print(stats)
    results_df = results_df.melt()
    results_df.columns = ["BotName", "Score"]
    g = sns.FacetGrid(results_df, col="BotName", col_wrap=3)
    g.map(sns.histplot, "Score", binwidth=1, stat="probability")
    #g.refline(x=means.values)
    for i, ax in enumerate(g.axes):
        ax.axvline(stats.iloc[i, 0], ls='--', c="red")

    plt.show(block=True)

