import itertools
from copy import deepcopy

from bots import *
from propagate_scores import *


class TreeBot(Bot):
    def __init__(self, select_action_method):
        super(TreeBot, self).__init__()
        self.name = f"TreeBotRelative"
        self.select_action_method = select_action_method
        self.tree = nx.DiGraph()
        self.n_sims = 5

    def get_score(self, game, player):
        return player.get_score()

    def sim_action(self, G: nx.DiGraph, game, player, paction, action_i: int, turn, parent_node, level=0):
        try:
            possible_actions = turn.send(paction)
            turn_phase = self.get_turn_phase(possible_actions)
            for current_paction, paction in enumerate(possible_actions):
                # Duplicate game state
                player_copy = deepcopy(player)
                game_copy = deepcopy(game)
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
        except StopIteration:
            score = self.get_score(game, player)
            if score > 0:
                score_node = f"{G.number_of_nodes()}. !Get a stone with score {score}!"
            else:
                score_node = f"{G.number_of_nodes()}. Lose the turn."
            G.add_node(score_node, score=score)
            G.add_edge(parent_node, score_node)

    def get_turn_phase(self, possible_actions: List[PlayerAction]) -> TurnPhase:
        if self.in_take_steal_phase(possible_actions):
            return TurnPhase.SELECT_A_STONE
        if self.in_roll_take_phase(possible_actions):
            return TurnPhase.ROLL_OR_TAKE
        if self.in_pick_dice_phase(possible_actions):
            return TurnPhase.PICK_DICE_SET

    @staticmethod
    def get_n_possible_actions(possible_actions, n_sims):
        return list(itertools.chain(*[copy.deepcopy(possible_actions) for _ in range(n_sims)]))

    def game_loop(self, game, player: Player, turn):
        self.game = game
        possible_actions = next(turn)

        # Number of simulations
        possible_actions = self.get_n_possible_actions(possible_actions, self.n_sims)
        round = 0

        while 1:
            # print(f"Starting new round with {len(possible_actions)} possible actions.")
            G = nx.DiGraph()
            G.add_node("0. START")

            # If we can take only one action, just do that.
            if len(possible_actions) == self.n_sims:
                action = possible_actions[0]
                try:
                    possible_actions = turn.send(action)
                except StopIteration:
                    break
                possible_actions = self.get_n_possible_actions(possible_actions, self.n_sims)
                round += 1
                continue

            # Otherwise, start simulating
            for pa, paction in enumerate(possible_actions):
                # print(f"Starting a simulation with start action {pa}, {str(paction)}")
                # Duplicate game state
                parent_node = f"{G.number_of_nodes()}. {str(paction)}"
                G.add_node(parent_node, action_i=pa)
                G.add_node(parent_node, action_i=pa)
                G.add_edge("0. START", parent_node)

                player_copy = deepcopy(player)
                assert None not in [die.face for die in getattr(player_copy, "rolled_dice")]
                game_copy = deepcopy(game)
                turn_copy = game_copy.start_turn(player_copy, turn_phase=self.get_turn_phase(possible_actions))
                # Go to the appropriate `yield` statement
                next(turn_copy)
                self.sim_action(G, game_copy, player_copy, paction, pa, turn_copy, parent_node=parent_node)

            G = propagate_scores(G)
            actions_df = pandas.DataFrame([
                (i % (len(possible_actions) / self.n_sims), G.nodes[out_node]["action_i"], G.nodes[out_node]["score"])
                for i, out_node in enumerate(G.neighbors("0. START"))
            ], columns=["action_type_i", "action_i", "score"])

            actions_df = actions_df.groupby("action_type_i").agg(self.select_action_method).sort_values("score")

            # Select the best action
            selected_action_i = int(actions_df.iloc[-1, 0])

            # if round > 0:
            #     nx.write_gexf(G, "./tree.gexf")
            #     exit()

            # Select the action with the highest score
            action = possible_actions[selected_action_i]
            # print("Final selected action", action)
            try:
                possible_actions = turn.send(action)
            except StopIteration:
                break
            possible_actions = self.get_n_possible_actions(possible_actions, self.n_sims)
            round += 1

    def select_action(self, player: Player, possible_actions: List[PlayerAction]) -> PlayerAction:
        if Bot.in_roll_take_phase(possible_actions):
            # Pick `roll` until we reach a threshold, then pick take a stone if possible.
            if len(Utils.count_faces(player.selected_dice)) < self.take_stone_threshold:
                return PlayerAction(PlayerActionType.ROLL_DICE, None)
            if any([action for action in possible_actions if action.action_type == PlayerActionType.TAKE_STONE]):
                return PlayerAction(PlayerActionType.TAKE_STONE, None)
            return PlayerAction(PlayerActionType.ROLL_DICE, None)

        elif Bot.in_pick_dice_phase(possible_actions):
            possible_actions = sorted(possible_actions, key=self.key_dice_set_actions)
            return possible_actions[-1]

        elif Bot.in_take_steal_phase(possible_actions):
            # Try to pick the highest stone, disregarding stealing or taking from the bank
            sorted_actions = sorted(possible_actions, key=lambda x: x.argument)
            best_stone_action = sorted_actions[-1]
            return best_stone_action

        else:
            # Fall back to a random choice
            return random.choice(possible_actions)
