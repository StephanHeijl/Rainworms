from rainworms import *
import random

class Bot():
    def __init__(self):
        self.game: RainWorms = None

    @staticmethod
    def in_roll_take_phase(possible_actions: List[PlayerAction]) -> bool:
        return any([
            action for action in possible_actions
            if action.action_type == PlayerActionType.ROLL_DICE
        ])

    @staticmethod
    def in_take_steal_phase(possible_actions: List[PlayerAction]) -> bool:
        return any([
            action for action in possible_actions
            if action.action_type == PlayerActionType.TAKE_STONE_WITH_VALUE
               or action.action_type == PlayerActionType.STEAL_STONE_WITH_VALUE
        ])

    @staticmethod
    def in_pick_dice_phase(possible_actions: List[PlayerAction]) -> bool:
        return any([
            action for action in possible_actions
            if action.action_type == PlayerActionType.PICK_DICE_SET_WITH_FACE
        ])

    def select_action(self, player: Player, possible_actions: List[PlayerAction]):
        raise NotImplementedError

    def game_loop(self, game, player: Player, turn):
        self.game = game
        possible_actions = next(turn)
        while 1:
            action = self.select_action(player, possible_actions)
            try:
                possible_actions = turn.send(action)
            except StopIteration:
                break


class RandomBot(Bot):
    def __init__(self):
        super(RandomBot, self).__init__()
        self.name = f"RandomBot"

    def select_action(self, player: Player, possible_actions: List[PlayerAction]):
        return random.choice(possible_actions)


class GreedyBot(Bot):
    """ This bot tries to take the highest scoring set of dice every time, and will always take the highest stone it can.
     It will start looking to take stones after a set threshold number of rolls. """
    def __init__(self, take_stone_threshold):
        super(GreedyBot, self).__init__()
        self.name = f"GreedyBot_{take_stone_threshold}"
        self.take_stone_threshold = take_stone_threshold

    @staticmethod
    def key_dice_set_actions(action: PlayerAction) -> int:
        number = action.argument.face.value
        is_worm = int(action.argument.face.name == "Worm")
        return number + is_worm

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


class GreedyStealingBot(GreedyBot):
    """ This is GreedyBot, except it tries to take the highest stone that it can steal. """
    def __init__(self, take_stone_threshold):
        super(GreedyStealingBot, self).__init__()
        self.name = f"GreedyStealingBot_{take_stone_threshold}"
        self.take_stone_threshold = take_stone_threshold

    @staticmethod
    def key_pick_stone(action: PlayerAction) -> int:
        score = action.argument
        # Add 20 points if this is a stealable stone.
        if action.action_type == PlayerActionType.STEAL_STONE_WITH_VALUE:
            score += 20
        return score