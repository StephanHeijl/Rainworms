from tree_bot import *


class TreeBotRelative(TreeBot):
    """ The exact same as TreeBot, except the score calculation at the end is relative to other players. """
    def get_score(self, game: RainWorms, player: Player):
        relative_scores = []
        pscore = player.get_score()
        for p in game.players:
            if p.player_n != player.player_n:
                relative_scores.append(pscore - p.get_score())
        return sum(relative_scores)
