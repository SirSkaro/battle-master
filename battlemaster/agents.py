from poke_env.player import Player, BattleOrder
from poke_env.environment import Battle, Move
from poke_engine.select_best_move import get_payoff_matrix, pick_safest
from poke_engine import Battle as BattleSimulation, StateMutator
from poke_engine.constants import SWITCH_STRING as SWITCH_ACTION

from battlemaster.adapters.clarion_adapter import MindAdapter
from battlemaster.adapters.poke_engine_adapter import BattleSimulationAdapter


class BattleMasterPlayer(Player):

    def __init__(self, mind: MindAdapter, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mind = mind

    def choose_move(self, battle: Battle) -> BattleOrder:
        perception = self._mind.perceive(battle)
        chosen_move = self._mind.choose_action()

        self.logger.debug(f'I see {perception}')

        if chosen_move is not None:
            self.logger.info(f"I'm choosing {chosen_move}")
            return self._select_move(battle, chosen_move)

        self.logger.info("I couldn't decide on an action. I'm picking a random action")
        return self.choose_random_move(battle)

    def _select_move(self, battle: Battle, order: str) -> BattleOrder:
        if self._is_available_move(battle, order):
            move_to_choose = [move for move in battle.available_moves if move.id == order][0]
            return self.create_order(move_to_choose)

        elif self._is_available_switch(battle, order):
            switch_to_choose = [pokemon for pokemon in battle.available_switches if pokemon.species == order or pokemon.base_species == order][0]
            return self.create_order(switch_to_choose)

        self.logger.warning(f"Attempted to choose {order}, but it's not one of the available moves or switches. Choosing a random action instead.")
        return self.choose_random_move(battle)

    def _is_available_move(self, battle: Battle, order: str) -> bool:
        move_names = [move.id for move in battle.available_moves]
        return order in move_names

    def _is_available_switch(self, battle: Battle, order: str):
        pokemon_names = [pokemon.species for pokemon in battle.available_switches] + [pokemon.base_species for pokemon in battle.available_switches]
        return order in pokemon_names


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


class ExpectiminimaxPlayer(Player):
    def choose_move(self, battle: Battle):
        simulation = BattleSimulationAdapter.from_battle(battle)
        action = self._simulate_and_pick_safest_move(simulation)
        if action.startswith(SWITCH_ACTION):
            return self._select_switch(battle, action)

        return self._select_move(battle, action)

    def _simulate_and_pick_safest_move(self, simulation: BattleSimulation) -> str:
        battles = simulation.prepare_battles(join_moves_together=True)
        all_scores = dict()
        for i, b in enumerate(battles):
            state = b.create_state()
            mutator = StateMutator(state)
            user_options, opponent_options = b.get_all_options()
            self.logger.info("Searching through the state: {}".format(mutator.state))
            scores = get_payoff_matrix(mutator, user_options, opponent_options, prune=True)

            prefixed_scores = self._prefix_opponent_move(scores, str(i))
            all_scores = {**all_scores, **prefixed_scores}

        decision, payoff = pick_safest(all_scores, remove_guaranteed=True)
        choice = decision[0]
        self.logger.info("Safest: {}, {}".format(choice, payoff))
        return choice

    def _select_switch(self, battle: Battle, pokemon_name: str) -> BattleOrder:
        pokemon_name = pokemon_name.split(SWITCH_ACTION)[-1].strip()
        pokemon_to_choose = [pokemon for pokemon in battle.available_switches if pokemon.species == pokemon_name or pokemon.base_species == pokemon_name][0]
        return self.create_order(pokemon_to_choose)

    def _select_move(self, battle: Battle, move_name: str) -> BattleOrder:
        move_to_choose = [move for move in battle.available_moves if move.id == move_name][0]
        return self.create_order(move_to_choose)

    def _prefix_opponent_move(self, score_lookup, prefix):
        new_score_lookup = dict()
        for k, v in score_lookup.items():
            bot_move, opponent_move = k
            new_opponent_move = "{}_{}".format(opponent_move, prefix)
            new_score_lookup[(bot_move, new_opponent_move)] = v

        return new_score_lookup
