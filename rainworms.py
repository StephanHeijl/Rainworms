import copy
import random
from collections import defaultdict
from enum import Enum, auto
from typing import List, Tuple, Union, Optional, Type, Generator, Any, Dict
from warnings import warn
from operator import itemgetter

class TurnPhase(Enum):
    ROLL_OR_TAKE = auto()
    TAKE_STONE = auto()
    ROLL_DICE = auto()
    PICK_DICE_SET = auto()
    SELECT_A_STONE = auto()


class PlayerActionType(Enum):
    ROLL_DICE = auto()
    TAKE_STONE = auto()
    TAKE_STONE_WITH_VALUE = auto()
    STEAL_STONE_WITH_VALUE = auto()
    PICK_DICE_SET_WITH_FACE = auto()
    RETURN = auto()


class PlayerAction:
    """ The PlayerAction class is used to represent the actions a player can take. """
    def __init__(self, action_type: PlayerActionType, argument: Any):
        self.action_type = action_type
        self.argument = argument

    def __deepcopy__(self, _memo):
        return PlayerAction(self.action_type, self.argument)

    def __eq__(self, other):
        """ Returns True if the action is equal to the other action. """
        return self.action_type == other.action_type and self.argument == other.argument

    def __str__(self):
        """ Returns a string representation of the action based on its type. """
        if self.action_type == PlayerActionType.ROLL_DICE:
            return "Roll the dice."
        if self.action_type == PlayerActionType.TAKE_STONE_WITH_VALUE:
            return f"Take a stone with value {self.argument}."
        if self.action_type == PlayerActionType.STEAL_STONE_WITH_VALUE:
            return f"Steal a stone from another player with value {self.argument}."
        if self.action_type == PlayerActionType.PICK_DICE_SET_WITH_FACE:
            if self.argument.count is None:
                return f"Pick a set of dice with face {self.argument.face}."
            else:
                return f"Pick a set of {self.argument.count} dice with face {self.argument.face}."
        else:
            return f"{self.action_type} -> {self.argument}"


class Stone:
    """ Stones are taken by players if they roll a number that is equal to or higher than the stone's value.
    At the end of the game, the player with the stones with the highest number of worms wins. """
    def __init__(self, number: int, worms: int):
        self.number = number
        self.worms = worms

    def __deepcopy__(self, _memo):
        return Stone(self.number, self.worms)

    def take(self):
        pass

    def __lt__(self, other):
        return self.number < other.number

    def __str__(self):
        return f"[{self.number}]({self.worms})"


class DieFace:
    def __init__(self, name: str, type_name: str, value: int):
        """ Create a new die face. """
        self.name: str = name
        self.type_name: str = type_name
        self.value: int = value
        self.hash: int = ord(self.name[0])

    def __deepcopy__(self, _memo):
        """ Deep copy of a DieFace. """
        return DieFace(self.name, self.type_name, self.value)

    def __eq__(self, other):
        """ Two DieFaces are equal if they have the same name. """
        try:
            return self.name == other.name
        except Exception:
            return False

    def __hash__(self) -> int:
        """ Returns an int to make the DieFace hashable"""
        return self.hash

    def __str__(self) -> str:
        """ Returns a string representation of the DieFace. """
        return self.name

    def __repr__(self) -> str:
        """ Returns a string representation of the DieFace. """
        return self.name

    def __lt__(self, other):
        """ Returns True if the DieFace is less than the other DieFace. """
        return self.hash < other.hash


class DiceSet:
    def __init__(self, face: DieFace, count: Optional[int]):
        """ Create a new dice set. """
        self.face = face
        self.count = count

    def __eq__(self, other):
        return self.face == other.face and \
               (self.count == other.count or self.count is None or other.count is None)

    def __deepcopy__(self, _memo):
        return DieFace(self.face, self.count)


class Die:
    """ A Die can have one of the following faces: 1, 2, 3, 4, 5 or Worm. Dice can be rolled or reset to None. """
    faces: List[DieFace] = [
        DieFace("⚀", "1", 1),
        DieFace("⚁", "2", 2),
        DieFace("⚂", "3", 3),
        DieFace("⚃", "4", 4),
        DieFace("⚄", "5", 5),
        DieFace("Worm", "W", 5)
    ]

    def __init__(self, face: DieFace = None):
        self.face: DieFace = face

    def __deepcopy__(self, _memo):
        return Die(self.face)

    def roll(self):
        self.face = random.choice(self.faces)

    def reset(self):
        self.face = None
        return self

    @classmethod
    def get_face_by_typed_name(cls, typed_name: str) -> Optional[DieFace]:
        for face in Die.faces:
            if face.type_name == typed_name:
                return face
        return None


class Player:
    def __init__(self, n: int, stones: List[Stone] = None,
                 selected_dice: List[Die] = None, name: str = None, rolled_dice: List[Die] = None):
        """ Create a new player. Only the player number is required, all other parameters are optional. 
        They are used to reconstruct a player from a previous game. 
        
        :param n: The player number.
        :param stones: The stones the player has.
        :param selected_dice: The dice the player has selected.
        :param name: The player's name.
        :param rolled_dice: The dice the player has rolled.
        """
        self.player_n: int = n
        self.stones: List[Stone] = stones if stones is not None else []
        self.selected_dice: List[Die] = selected_dice if selected_dice is not None else []
        self.name = name if name is not None else "NoName"
        self.rolled_dice: List[Die] = rolled_dice if rolled_dice is not None else []

    def __deepcopy__(self, memo):
        """ Overwrites the normal deepcopy method to increase copying speed. """
        return Player(
            copy.copy(self.player_n),
            copy.deepcopy(self.stones, memo),
            copy.deepcopy(self.selected_dice, memo),
            self.name,
            copy.deepcopy(self.rolled_dice, memo)
        )

    def __str__(self):
        top_stone = self.check_top_stone()
        summary_str = f"Player {self.player_n} has a score of {self.get_score()}, " \
                      f"with stones {[stone.number for stone in self.stones]}."
        if top_stone:
            summary_str += f"The top stone is {top_stone.number}"

        return summary_str

    def give_dice_back(self):
        """ Returns all selected dice to the bank. """
        self.selected_dice = []
        self.rolled_dice = []
        sd = [self.selected_dice.pop(0) for _d in range(len(self.selected_dice))]
        rd = [self.rolled_dice.pop(0) for _d in range(len(self.rolled_dice))]

    def get_score(self) -> int:
        return sum([stone.worms for stone in self.stones])

    def check_top_stone(self) -> Optional[Stone]:
        """ Checks what the stone at the top of the player's stack is. """
        try:
            return self.stones[-1]
        except IndexError:
            return None

    def give_stone(self, stone: Stone):
        """ Give this player a stone. """
        self.stones.append(stone)

    def take_top_stone(self) -> Optional[Stone]:
        """ Take the top stone from the player's stack. """
        try:
            return self.stones.pop()
        except IndexError:
            return None

    def roll_dice(self, dice: List[Die]) -> List[Die]:
        """ Have the player roll the dice. """
        for die in dice:
            die.roll()
        return dice

    def check_may_continue_with_dice(self, dice: List[Die], game) -> bool:
        """ Checks if the player may continue with the dice they rolled.
        Returns True if the player may continue. If not, the player automatically loses the turn. """
        possible_selections = Utils.possible_player_selections(
            self.selected_dice, dice
        )
        if not possible_selections:
            self.lose_turn(game)
            return False
        return True

    def select_dice(self, dice: List[Die], selected_face: DieFace):
        """ Select the dice with the given face. """
        for die in self.selected_dice:
            if die.face == selected_face:
                raise ValueError("You already have this face.")
        selected_dice = []
        for d, die in enumerate(dice):
            if die.face == selected_face:
                selected_dice.append(d)
        if not selected_dice:
            raise ValueError(f"Invalid selection, no dice with face {selected_face}")
        for d in selected_dice[::-1]:
            self.selected_dice.append(dice.pop(d))

    def lose_turn(self, game):
        """ The player loses the turn, this means that the player has to give the top stone back to the bank. """
        top_stone = self.take_top_stone()
        if top_stone:
            game.return_stone_to_bank(top_stone)


class Utils:
    @staticmethod
    def count_faces(dice: List[Die]) -> List[Tuple[DieFace, int]]:
        """ Counts the number of times each face appears in the given list of dice. """
        counts: defaultdict = defaultdict(int)
        for die in dice:
            counts[die.face] += 1
        return list(sorted(counts.items(), key=itemgetter(0)))

    @staticmethod
    def count_score(dice: List[Die]) -> int:
        """ Utility function to count the score of a list of dice. """
        return sum([die.face.value for die in dice if die.face is not None])

    @staticmethod
    def possible_player_selections(selected_dice: List[Die], rolled_dice: List[Die]) -> Dict[DieFace, int]:
        """ Returns a dictionary with the number of times each face appears in the given list of dice. 
        This is used to give the player a list of possible selections.
        """
        selected_faces = Utils.count_faces(selected_dice)
        rolled_faces = Utils.count_faces(rolled_dice)
        possible_selections = set([f for f, n in rolled_faces]) - set([f for f, n in selected_faces])
        return {
            face: n for face, n in rolled_faces
            if face in possible_selections
        }

    @staticmethod
    def are_selected_dice_valid(selected_dice: List[Die]) -> bool:
        """ Checks if the selected dice are a valid combination. 
        The list of selected dice must contain at least one Worm. """
        for die in selected_dice:
            if die.face == DieFace("Worm", "W", 5):
                return True
        return False


class RainWorms():
    """ RainWorms is a relatuvely simple game, where the player rolls the dice and then selects 
    the dice they want to keep. They then roll again until they can either select a stone with a corresponding 
    value or they can't and have to give the top stone back to the bank. The most valuable stone in the bank is
    flipped when a player loses a turn. This continues until all stones are gone or flipped. """
    def __init__(self, n_players=4, number_of_dice=8, setup=True, stones=None, turned_stones=None, players=None,
                 dice=None, player_turn=None):
        self.stones: List[Stone] = stones if stones is not None else []
        self.turned_stones: List[Stone] = turned_stones if turned_stones is not None else []
        self.players: List[Player] = players if players is not None else []
        self.dice: List[Die] = dice if dice is not None else []
        self.number_of_dice = number_of_dice
        self.n_players = n_players
        self.player_turn = player_turn if player_turn is not None else 0
        if setup:
            self.setup_game()

    def __deepcopy__(self, memo):
        """ Overwrites the normal deepcopy method to increase copying speed. """
        return RainWorms(
            n_players=copy.copy(self.n_players),
            number_of_dice=copy.copy(self.number_of_dice),
            setup=False,
            stones=copy.deepcopy(self.stones, memo),
            turned_stones=copy.deepcopy(self.turned_stones, memo),
            players=copy.deepcopy(self.players, memo),
            dice=copy.deepcopy(self.dice, memo),
            player_turn=copy.copy(self.player_turn),
        )


    def copy_game(self, other_game):
        self.stones = copy.deepcopy(other_game.stones)
        self.turned_stones = copy.deepcopy(other_game.turned_stones)
        self.players = copy.deepcopy(other_game.players)
        self.dice = copy.deepcopy(other_game.dice)
        self.player_turn = copy.copy(other_game.player_turn)
        self.number_of_dice = copy.copy(other_game.number_of_dice)
        self.n_players = copy.copy(other_game.n_players)

    def is_stone_available(self, number: int) -> Union[Type[Stone], bool]:
        for stone in self.stones:
            if stone.number == number:
                return Stone
        return False

    def setup_game(self):
        pairs = [
            (21, 1),
            (22, 1),
            (23, 1),
            (24, 1),
            (25, 2),
            (26, 2),
            (27, 2),
            (28, 2),
            (29, 3),
            (30, 3),
            (31, 3),
            (32, 3),
            (33, 4),
            (34, 4),
            (35, 4),
            (36, 4)
        ]
        for number, worms in pairs:
            self.stones.append(
                Stone(number, worms)
            )

        for i in range(self.n_players):
            self.players.append(Player(n=i + 1))

    def get_fresh_dice(self):
        # Get the dice
        self.dice = [Die() for _ in range(self.number_of_dice)]

    def return_stone_to_bank(self, stone: Stone):
        self.stones.append(stone)
        self.stones.sort()
        if stone.number < max(self.stones).number:
            # Remove the top stone from the bank
            self.turned_stones.append(self.stones.pop())

    def take_stone_from_bank(self, number: int) -> Stone:
        for s, stone in enumerate(self.stones):
            if stone.number == number:
                return self.stones.pop(s)
                return self.stones.pop(s)
        raise LookupError("Stone is not in bank")

    def __str__(self) -> str:
        summary_string = f"There are {self.n_players} in the game.\n"
        for player in self.players:
            summary_string += str(player) + "\n"
        summary_string += f"The following stones are still available: \n"
        summary_string += ", ".join([str(stone) for stone in self.stones]) + "\n"
        summary_string += f"It is player {self.player_turn + 1}'s turn. \n"
        return summary_string

    def step(self):
        # Return player's dice
        self.players[self.player_turn].give_dice_back()
        self.get_fresh_dice()
        self.player_turn = (self.player_turn + 1) % self.n_players

    def get_other_player_stones(self) -> List[Tuple[Player, Optional[Stone]]]:
        return [(p, p.check_top_stone()) for pn, p in enumerate(self.players) if pn != self.player_turn]

    def steal_stone_from_other_player(self, selection: int) -> Optional[Stone]:
        for player, stone in self.get_other_player_stones():
            if stone is not None and stone.number == selection:
                return player.take_top_stone()
        raise LookupError("Player does not possess this stone.")

    def do_a_roll(self, player: Player) -> Generator[List[PlayerAction], PlayerAction, bool]:
        """ Generator that rolls the dice and returns whether the turn ends. """
        # Try continuously until a valid option is selected.
        assert None not in [die.face for die in getattr(player, "rolled_dice", [])]
        if player.rolled_dice:
            rolled_dice = player.rolled_dice
            rd_source = "Player"
        else:
            rolled_dice = player.roll_dice(self.dice)
            assert None not in [die.face for die in rolled_dice]
            rd_source = "Roll"

        counted_faces = Utils.count_faces(rolled_dice)
        if None in [face for face, count in counted_faces]:
            raise ValueError(f"{rd_source} Rolled a None?")

        assert rolled_dice is not None
        player.rolled_dice = rolled_dice

        # End the turn if the player cannot continue
        if not player.check_may_continue_with_dice(rolled_dice, self):
            return True
        while 1:
            try:
                possible_actions = [
                    PlayerAction(PlayerActionType.PICK_DICE_SET_WITH_FACE, DiceSet(face, count))
                    for face, count in counted_faces
                ]
                action: PlayerAction = yield possible_actions
                if action in possible_actions:
                    selected_face = action.argument.face
                    assert selected_face is not None
                    player.select_dice(rolled_dice, selected_face)
                    return False
                else:
                    warn(f"Invalid selection: '{action.argument}'.")
            except (ValueError, AssertionError) as e:
                warn(f"Error: '{e}'.")

    def get_possible_steal_take_actions(self, player: Player) -> List[PlayerAction]:
        possible_take_actions = [
            PlayerAction(PlayerActionType.TAKE_STONE_WITH_VALUE, stone.number) for stone in self.stones
            if stone.number <= Utils.count_score(player.selected_dice)
        ]
        possible_steal_actions = [
            PlayerAction(PlayerActionType.STEAL_STONE_WITH_VALUE, stone.number)
            for _p, stone in self.get_other_player_stones() if stone is not None and
                                                               stone.number == Utils.count_score(player.selected_dice)
        ]
        return possible_take_actions + possible_steal_actions

    def take_a_stone(self, player: Player) -> Generator[List[PlayerAction], PlayerAction, bool]:
        # Try continuously until a valid option is selected.
        while 1:
            possible_actions = self.get_possible_steal_take_actions(player)
            if not possible_actions:
                return False

            action: PlayerAction = yield possible_actions
            try:
                assert action in possible_actions

                if action.action_type == PlayerActionType.TAKE_STONE_WITH_VALUE:
                    stone_value = int(action.argument)
                    if stone_value <= Utils.count_score(player.selected_dice):
                        selected_stone = self.take_stone_from_bank(stone_value)
                        player.give_stone(selected_stone)
                        return True
                    else:
                        warn(f"Invalid stone selection from bank: '{stone_value}', score too low.")
                elif action.action_type == PlayerActionType.STEAL_STONE_WITH_VALUE:
                    taken_stone = self.steal_stone_from_other_player(int(action.argument))
                    if taken_stone is not None:
                        player.give_stone(taken_stone)
                        return True
                    else:
                        warn("Invalid selection, cannot steal another player's stone.")
                else:
                    warn(f"Invalid selection: '{action.argument}'.")
            except (ValueError, AssertionError) as e:
                print(e)
                warn(f"Error: '{e}'.")

    def wrap_do_a_roll_interactive(self, player) -> bool:
        assert None not in [die.face for die in getattr(player, "rolled_dice", [])]
        roll_generator = self.do_a_roll(player)
        possible_actions = next(roll_generator)
        while 1:
            print("\n".join([str(a) for a in possible_actions]))
            selection = input("Select a set of dice: ")
            selected_face = Die.get_face_by_typed_name(selection)
            assert selected_face is not None
            action = PlayerAction(
                PlayerActionType.PICK_DICE_SET_WITH_FACE, DiceSet(selected_face, None)
            )
            if action not in possible_actions:
                print("Not a valid action.")
                continue
            try:
                possible_actions = roll_generator.send(action)
            except StopIteration as return_value:
                return return_value.value

    def wrap_take_a_stone_interactive(self, player) -> bool:
        take_generator = self.take_a_stone(player)
        possible_actions = next(take_generator)
        while 1:
            action: Optional[PlayerAction] = None

            while 1:
                selection = input("Select stone with value: ")
                bank_stone_values = [stone.number for stone in self.stones]
                player_stone_values = [stone.number for _, stone in self.get_other_player_stones() if stone is not None]
                try:
                    selected_value = int(selection)
                except (TypeError, ValueError) as e:
                    warn(f"Invalid selection '{selection}', {e}")
                    continue

                if selected_value in bank_stone_values:
                    action = PlayerAction(PlayerActionType.TAKE_STONE_WITH_VALUE, selected_value)
                    break
                elif selected_value in player_stone_values:
                    action = PlayerAction(PlayerActionType.STEAL_STONE_WITH_VALUE, selected_value)
                    break
                else:
                    warn(f"Invalid selection '{selection}', stone cannot be taken.")

            assert action in possible_actions
            try:
                possible_actions = take_generator.send(action)
            except StopIteration as return_value:
                return return_value.value

    def start_interactive(self):
        print("Enter 1-5 or W to select dice.")
        while 1:
            print(f"It is player {self.player_turn + 1}'s turn.")
            turn_end = False
            while not turn_end:
                player = self.players[self.player_turn]
                print(f"You have {Utils.count_faces(player.selected_dice)}, "
                      f"total score: {Utils.count_score(player.selected_dice)}")

                print("Do you want to roll or take a stone?")
                while 1:
                    take_or_roll = input(">")
                    if take_or_roll == "take":
                        turn_end = self.wrap_take_a_stone_interactive(player)
                        if turn_end:
                            break
                        else:
                            print("Did not take a stone, asking again.")
                    elif take_or_roll == "roll":
                        turn_end = self.wrap_do_a_roll_interactive(player)
                        break
                    else:
                        print("Invalid selection, try 'roll' or 'take'.")

                print(f"You have {Utils.count_faces(player.selected_dice)}, "
                      f"total score: {Utils.count_score(player.selected_dice)}")
                print("*" * 80)

            self.step()
            if not self.stones:
                break

    def start_session(self) -> Generator[Tuple[Player, Generator[List[PlayerAction], PlayerAction, int]], None, List[int]]:
        """ Starts a game session as a generator, that yields the current Player and a turn generator. """
        while 1:
            player = self.players[self.player_turn]
            turn_generator = self.start_turn(player)
            yield player, turn_generator
            self.step()
            if not self.stones:
                break
        return [player.get_score() for player in self.players]

    def start_turn(self, player, turn_phase: Optional[TurnPhase] = None) -> Generator[List[PlayerAction], PlayerAction, int]:
        """ Turn_phase allows starting the turn in a different phase."""
        assert None not in [die.face for die in getattr(player, "rolled_dice", list())]
        if turn_phase:
            #print("Created turn in phase: ", turn_phase)
            pass
        turn_end = False
        while not turn_end:
            if turn_phase is None or turn_phase == TurnPhase.ROLL_OR_TAKE:
                possible_actions = [PlayerAction(PlayerActionType.ROLL_DICE, None)]
                # Only add the take action if there are stones that can be taken.
                if self.get_possible_steal_take_actions(player):
                    possible_actions.append(PlayerAction(PlayerActionType.TAKE_STONE, None))

                selection: PlayerAction = yield possible_actions
                if selection.action_type == PlayerActionType.ROLL_DICE:
                    turn_phase = TurnPhase.ROLL_DICE
                else:
                    turn_phase = TurnPhase.TAKE_STONE

            roll_generator = None
            action = None
            if turn_phase == TurnPhase.ROLL_DICE:
                assert None not in [die.face for die in getattr(player, "rolled_dice", list())]
                roll_generator = self.do_a_roll(player)
                try:
                    possible_actions = next(roll_generator)
                except StopIteration as return_value:
                    if return_value.value:
                        break

                # Remove faces the player cannot pick
                possible_actions = [
                    action for action in possible_actions
                    if action.argument.face not in [d.face for d in player.selected_dice]
                ]
                action = yield possible_actions
                turn_phase = TurnPhase.PICK_DICE_SET

            if turn_phase == TurnPhase.PICK_DICE_SET:
                if action is None:
                    action = yield []
                if roll_generator is None:
                    assert None not in [die.face for die in getattr(player, "rolled_dice", [])]
                    roll_generator = self.do_a_roll(player)
                    next(roll_generator)

                try:
                    possible_actions = roll_generator.send(action)
                except StopIteration as return_value:
                    turn_end = return_value.value

            take_generator = None
            action = None
            if turn_phase == turn_phase.TAKE_STONE:
                take_generator = self.take_a_stone(player)
                try:
                    possible_actions = next(take_generator)
                except StopIteration as return_value:
                    warn("You tried to take a stone, while you could not, this should not be possible.")
                    turn_end = True
                    continue

                action = yield possible_actions
                turn_phase = TurnPhase.SELECT_A_STONE

            if turn_phase == TurnPhase.SELECT_A_STONE:
                if take_generator is None:
                    take_generator = self.take_a_stone(player)
                    try:
                        next(take_generator)
                    except StopIteration:
                        warn("You tried to select a stone, while you could not, this should not be possible.")
                        turn_end = True
                        continue

                if action is None:
                    action = yield []
                try:
                    possible_actions = take_generator.send(action)
                except StopIteration as return_value:
                    turn_end = return_value.value
                    break

            # Reset turn phase
            turn_phase = None

        return player.get_score()


if __name__ == "__main__":
    game = RainWorms()
    print(game)
    game.start_interactive()
