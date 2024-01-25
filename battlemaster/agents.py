from random import shuffle

from pyClarion import chunk
from poke_env.player import Player
from poke_env.environment import Battle, Move
from pyClarion import Structure, Construct, subsystem, flow_tt


class BattleMasterPlayer(Player):

    def __init__(self, mind: Structure, stimulus: Construct, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mind = mind
        self.stimulus = stimulus

    def choose_move(self, battle: Battle):
        type1, type2 = battle.opponent_active_pokemon.types
        stimulus = {chunk(type1.name.lower()): 1.}
        if type2 is not None:
            stimulus[chunk(type2.name.lower())] = 1.

        self.stimulus.process.input(stimulus)
        self.mind.step()
        associations = self.mind.output[(subsystem('nacs'), flow_tt('associations'))]

        move_type_priority_list = [symbol.cid for symbol in sorted(associations, key=associations.get, reverse=True) if isinstance(symbol, chunk)]
        shuffle(battle.available_moves)

        self.logger.info(f'I see {stimulus}')
        self.logger.info(f'I know these types are super-effective: {move_type_priority_list}, and I have {[move.id for move in battle.available_moves]}')

        for move_type_to_choose in move_type_priority_list:
            for available_move in battle.available_moves:
                if available_move.type.name.lower() == move_type_to_choose:
                    self.logger.info(f'I am picking on of my super-effective moves: {available_move.id}')
                    return self.create_order(available_move)

        self.logger.info(f"I don't have a super-effective move. Picking a random action...")
        return self.choose_random_move(battle)


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
