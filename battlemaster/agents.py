from poke_env.player import Player, BattleOrder
from poke_env.environment import Battle, Move

from .clarion_adapter import MindAdapter


class BattleMasterPlayer(Player):

    def __init__(self, mind: MindAdapter, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mind = mind

    def choose_move(self, battle: Battle) -> BattleOrder:
        perception = self._mind.perceive(battle)
        chosen_move = self._mind.choose_action()

        self.logger.info(f'I see {perception}')

        if chosen_move is not None:
            self.logger.info(f"I'm choosing {chosen_move}")
            return self._select_move(battle, chosen_move)

        self.logger.info("I couldn't decide on an action. I'm picking a random action")
        return self.choose_random_move(battle)

    def _select_move(self, battle: Battle, move_name: str) -> BattleOrder:
        move_names = [move.id for move in battle.available_moves]
        if move_name not in move_names:
            self.logger.warning(f"Attempted to choose {move_name}, but it's not one of the available moves: {move_names}. Choosing a random action instead.")
            return self.choose_random_move(battle)

        move_to_choose = [move for move in battle.available_moves if move.id == move_name][0]
        return self.create_order(move_to_choose)


class MaxDamagePlayer(Player):
    def choose_move(self, battle: Battle):

        if battle.available_moves:
            move_score_tuples = [(move, self._calculate_score(battle, move)) for move in battle.available_moves]
            self.logger.info(f"My available moves (and scores) are {[(move.id, score) for move, score in move_score_tuples]}")
            best_move, score = max(move_score_tuples, key=lambda move_score: move_score[1])
            if score > 0:
                self.logger.info(f"My strongest damaging move is {best_move.id} with a score of {score}")
                return self.create_order(best_move)

        self.logger.info("I have no moves that do damage. Choosing a random action.")
        return self.choose_random_move(battle)

    @staticmethod
    def _calculate_score(battle: Battle, move: Move) -> float:
        target_pokemon = battle.opponent_active_pokemon
        stab_bonus = 1.5 if move.type in battle.active_pokemon.types else 1
        return move.base_power * target_pokemon.damage_multiplier(move) * stab_bonus
