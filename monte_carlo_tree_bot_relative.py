from tree_bot import *
import random


class MCTreeBotRelative(TreeBot):
    """ The exact same as TreeBot, except the score calculation at the end is relative to other players and
     random actions are selected as opposed to all actions being simulated. """

    def __init__(self, select_action_method, n_random_actions, n_sims):
        super(TreeBot, self).__init__()
        self.name = f"MCTreeBotRelative"
        self.select_action_method = select_action_method
        self.n_random_actions = n_random_actions
        self.tree = nx.DiGraph()
        self.n_sims = n_sims

    def get_score(self, game: RainWorms, player: Player):
        relative_scores = []
        pscore = player.get_score()
        for p in game.players:
            if p.player_n != player.player_n:
                relative_scores.append(pscore - p.get_score())
        return sum(relative_scores)

    def sim_action(self, G: nx.DiGraph, game, player, paction, action_i: int, turn, parent_node, level=0):
        try:
            possible_actions = turn.send(paction)
            turn_phase = self.get_turn_phase(possible_actions)
            random_possible_actions = random.sample(possible_actions, min(self.n_random_actions, len(possible_actions)))
            for current_paction, paction in enumerate(random_possible_actions):
                # Duplicate game state
                player_copy = deepcopy(player)
                game_copy = deepcopy(game)
                # assert None not in [die.face for die in getattr(player_copy, "rolled_dice", list())]
                turn_copy = game_copy.start_turn(player_copy, turn_phase=turn_phase)
                # Go to the appropriate `yield` statement
                next(turn_copy)
                new_node = f"{G.number_of_nodes()}. {str(paction)}"
                G.add_node(new_node, action_i=current_paction)
                G.add_edge(parent_node, new_node)
                self.sim_action(
                    G, game_copy, player_copy, paction, current_paction,
                    turn_copy, parent_node=new_node, level=level + 1
                )
                # Return game to pool
                #game_wrapper.in_use = False
        except StopIteration:
            score = self.get_score(game, player)
            if score > 0:
                score_node = f"{G.number_of_nodes()}. !Get a stone with score {score}!"
            else:
                score_node = f"{G.number_of_nodes()}. Lose the turn."
            G.add_node(score_node, score=score)
            G.add_edge(parent_node, score_node)
