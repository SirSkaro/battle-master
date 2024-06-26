from typing import Mapping, List, Optional
from collections import defaultdict
from enum import Enum
from functools import partial

from poke_env.environment import Battle, Pokemon, Effect, Field
from poke_engine import Battle as Simulation, Battler, Pokemon as PokemonSimulation, constants, StateMutator
from poke_engine.select_best_move import get_payoff_matrix, pick_safest
from poke_engine.helpers import normalize_name
from poke_engine.constants import SWITCH_STRING
from pyClarion import nd

from .clarion_adapter import BattleConcept
from ..clarion_ext.attention import GroupedChunkInstance
from ..clarion_ext.numdicts_ext import get_chunk_from_numdict, get_only_value_from_numdict, is_empty


class OptionFilter(Enum):
    NO_FILTER = partial(lambda option: True)
    MOVES = partial(lambda option: not option.startswith(SWITCH_STRING))
    SWITCHES = partial(lambda option: option.startswith(SWITCH_STRING))

    def __call__(self, *args, **kwargs):
        return self.value(*args, **kwargs)


class Simulator:
    def __init__(self):
        pass

    def pick_safest_move(self, simulation: Simulation, user_option_filter: OptionFilter = OptionFilter.NO_FILTER) -> Optional[str]:
        battles = simulation.prepare_battles(guess_mega_evo_opponent=False, join_moves_together=True)
        all_scores = dict()
        for i, battle in enumerate(battles):
            state = battle.create_state()
            mutator = StateMutator(state)
            user_options, opponent_options = self._get_user_and_opponent_options(battle, user_option_filter)
            scores = get_payoff_matrix(mutator, user_options, opponent_options, prune=True)

            prefixed_scores = self._prefix_opponent_move(scores, str(i))
            all_scores = {**all_scores, **prefixed_scores}

        if not all_scores:
            return None

        decision, payoff = pick_safest(all_scores, remove_guaranteed=True)
        choice = decision[0]
        return choice

    @staticmethod
    def _get_user_and_opponent_options(battle: Simulation, user_option_filter: OptionFilter):
        user_options, opponent_options = battle.get_all_options()
        user_options = [option for option in user_options if user_option_filter(option)]

        return user_options, opponent_options

    @staticmethod
    def _prefix_opponent_move(score_lookup, prefix):
        new_score_lookup = dict()
        for k, v in score_lookup.items():
            bot_move, opponent_move = k
            new_opponent_move = "{}_{}".format(opponent_move, prefix)
            new_score_lookup[(bot_move, new_opponent_move)] = v

        return new_score_lookup


class BattleStimulusAdapter(Simulation):
    def __init__(self, battle_tag):
        super().__init__(battle_tag)

    def find_best_move(self):
        raise NotImplementedError('Adapter is intended to be controlled externally')

    @classmethod
    def from_stimulus(cls, stimulus: Mapping[BattleConcept, nd.NumDict]) -> 'BattleStimulusAdapter':
        battle_metadata_stim: GroupedChunkInstance = get_chunk_from_numdict('metadata', stimulus[BattleConcept.BATTLE])
        simulation = BattleSimulationAdapter(battle_metadata_stim.get_feature_value('battle_tag'))
        simulation.user = cls._convert_player(stimulus)
        simulation.opponent = cls._convert_opponent(stimulus)

        weather_stim = stimulus[BattleConcept.WEATHER]
        simulation.weather = get_only_value_from_numdict(weather_stim).cid if not is_empty(weather_stim) else None

        field_effects_stim = stimulus[BattleConcept.FIELD_EFFECTS]
        simulation.field = get_only_value_from_numdict(field_effects_stim).cid if not is_empty(field_effects_stim) else None
        simulation.trick_room = cls._check_trickroom(stimulus)
        simulation.turn = battle_metadata_stim.get_feature_value('turn')
        simulation.force_switch = battle_metadata_stim.get_feature_value('force_switch')
        simulation.wait = battle_metadata_stim.get_feature_value('wait')
        simulation.generation = 'gen9'

        return simulation

    @classmethod
    def _convert_player(cls, stimulus: Mapping[BattleConcept, nd.NumDict]) -> Battler:
        player_stim: GroupedChunkInstance = get_chunk_from_numdict('self', stimulus[BattleConcept.PLAYERS])

        user = Battler()
        user.name = player_stim.get_feature_value('name')
        user.account_name = user.name

        user.active = cls._convert_player_active_pokemon(stimulus) if not is_empty(stimulus[BattleConcept.ACTIVE_POKEMON]) else None
        user.reserve = cls._convert_player_benched_pokemon(stimulus)
        user.trapped = cls._check_trapped(stimulus, BattleConcept.ACTIVE_POKEMON) if user.active is not None else False
        user.side_conditions = defaultdict(lambda: 0, {condition_chunk.cid: condition_chunk.features[0].val for condition_chunk in stimulus[BattleConcept.SIDE_CONDITIONS].keys()})

        return user

    @classmethod
    def _convert_opponent(cls, stimulus: Mapping[BattleConcept, nd.NumDict]) -> Battler:
        player_stim: GroupedChunkInstance = get_chunk_from_numdict('opponent', stimulus[BattleConcept.PLAYERS])
        user = Battler()
        user.name = player_stim.get_feature_value('name')
        user.account_name = user.name

        pokemon_stim: GroupedChunkInstance = get_only_value_from_numdict(stimulus[BattleConcept.OPPONENT_ACTIVE_POKEMON]) if not is_empty(stimulus[BattleConcept.OPPONENT_ACTIVE_POKEMON]) else None
        user.active = cls._convert_opponent_pokemon(pokemon_stim) if pokemon_stim is not None else None
        user.reserve = cls._convert_opponent_benched_pokemon(stimulus)
        user.trapped = cls._check_trapped(stimulus, BattleConcept.OPPONENT_ACTIVE_POKEMON) if user.active is not None else False
        user.side_conditions = defaultdict(lambda: 0, {condition_chunk.cid: condition_chunk.features[0].val for condition_chunk in stimulus[BattleConcept.OPPONENT_SIDE_CONDITIONS].keys()})

        return user

    @classmethod
    def _convert_player_active_pokemon(cls, stimulus: Mapping[BattleConcept, nd.NumDict]) -> PokemonSimulation:
        pokemon_stim: GroupedChunkInstance = get_only_value_from_numdict(stimulus[BattleConcept.ACTIVE_POKEMON])
        available_move_stim: nd.NumDict = stimulus[BattleConcept.AVAILABLE_MOVES]

        simulated_pokemon = cls._convert_base_player_pokemon(pokemon_stim)
        for move_chunk in available_move_stim.keys():
            simulated_pokemon.add_move(move_chunk.cid)

        return simulated_pokemon

    @classmethod
    def _convert_player_benched_pokemon(cls, stimulus: Mapping[BattleConcept, nd.NumDict]) -> List[PokemonSimulation]:
        benched_pokemon = []
        team_stim = stimulus[BattleConcept.TEAM]
        for pokemon_chunk in team_stim.keys():
            if pokemon_chunk.get_feature_value('active'):
                continue
            simulated_pokemon = cls._convert_base_player_pokemon(pokemon_chunk)
            for move in pokemon_chunk.get_feature_value('move'):
                simulated_pokemon.add_move(move)
            benched_pokemon.append(simulated_pokemon)

        return benched_pokemon

    @staticmethod
    def _check_trickroom(stimulus: Mapping[BattleConcept, nd.NumDict]):
        field_effects_stim = stimulus[BattleConcept.FIELD_EFFECTS]
        for effect_chunk in field_effects_stim.keys():
            if effect_chunk.cid == 'trickroom':
                return True
        return False

    @staticmethod
    def _check_trapped(stimulus: Mapping[BattleConcept, nd.NumDict], concept: BattleConcept):
        pokemon_chunk = get_only_value_from_numdict(stimulus[concept])
        is_trapped = pokemon_chunk.get_feature_value('trapped')
        return is_trapped if is_trapped is not None else False

    @staticmethod
    def _convert_base_player_pokemon(pokemon_stim: GroupedChunkInstance) -> PokemonSimulation:
        """
        Maps everything but moves
        """
        simulated = PokemonSimulation(pokemon_stim.cid, pokemon_stim.get_feature_value('level'))
        simulated.fainted = pokemon_stim.get_feature_value('fainted')
        simulated.status = pokemon_stim.get_feature_value('status')
        simulated.stats = {
            constants.ATTACK: pokemon_stim.get_feature_value('atk'),
            constants.DEFENSE: pokemon_stim.get_feature_value('def'),
            constants.SPECIAL_ATTACK: pokemon_stim.get_feature_value('spa'),
            constants.SPECIAL_DEFENSE: pokemon_stim.get_feature_value('spd'),
            constants.SPEED: pokemon_stim.get_feature_value('spe')
        }
        simulated.hp = pokemon_stim.get_feature_value('hp')
        simulated.max_hp = pokemon_stim.get_feature_value('max_hp')
        simulated.item = pokemon_stim.get_feature_value('item')
        simulated.ability = pokemon_stim.get_feature_value('ability')
        simulated.volatile_statuses = [status_feature.val for status_feature in pokemon_stim.get_feature('volatile_status')]
        simulated.boosts = {
            constants.ACCURACY: pokemon_stim.get_feature_value('accuracy_boost'),
            constants.EVASION: pokemon_stim.get_feature_value('evasion_boost'),
            constants.ATTACK: pokemon_stim.get_feature_value('atk_boost'),
            constants.DEFENSE: pokemon_stim.get_feature_value('def_boost'),
            constants.SPECIAL_ATTACK: pokemon_stim.get_feature_value('spa_boost'),
            constants.SPECIAL_DEFENSE: pokemon_stim.get_feature_value('spd_boost'),
            constants.SPEED: pokemon_stim.get_feature_value('spe_boost')
        }
        simulated.terastallized = pokemon_stim.get_feature_value('terastallized')
        simulated.types = [feature.val for feature in pokemon_stim.get_feature('type')]

        return simulated

    @staticmethod
    def _convert_opponent_pokemon(pokemon_stim: GroupedChunkInstance) -> PokemonSimulation:
        simulated = PokemonSimulation(pokemon_stim.cid, pokemon_stim.get_feature_value('level'))
        simulated.fainted = pokemon_stim.get_feature_value('fainted')
        simulated.status = pokemon_stim.get_feature_value('status')
        simulated.set_most_likely_spread()
        simulated.hp = (pokemon_stim.get_feature_value('hp_percentage') / 100.0) * simulated.max_hp

        simulated.ability = pokemon_stim.get_feature_value('ability')
        if simulated.ability is None:
            simulated.set_most_likely_ability_unless_revealed()

        simulated.item = pokemon_stim.get_feature_value('item')
        if simulated.item is None:
            simulated.set_most_likely_item_unless_revealed()

        for move_feature in pokemon_stim.get_feature('move'):
            simulated.add_move(move_feature.tag)
        if len(simulated.moves) < 4:
            simulated.set_likely_moves_unless_revealed()

        simulated.volatile_statuses = [status_feature.val for status_feature in pokemon_stim.get_feature('volatile_status')]

        simulated.boosts = {
            constants.ACCURACY: pokemon_stim.get_feature_value('accuracy_boost'),
            constants.EVASION: pokemon_stim.get_feature_value('evasion_boost'),
            constants.ATTACK: pokemon_stim.get_feature_value('atk_boost'),
            constants.DEFENSE: pokemon_stim.get_feature_value('def_boost'),
            constants.SPECIAL_ATTACK: pokemon_stim.get_feature_value('spa_boost'),
            constants.SPECIAL_DEFENSE: pokemon_stim.get_feature_value('spd_boost'),
            constants.SPEED: pokemon_stim.get_feature_value('spe_boost')
        }

        simulated.terastallized = pokemon_stim.get_feature_value('terastallized')
        simulated.types = [feature.val for feature in pokemon_stim.get_feature('type')]

        return simulated

    @classmethod
    def _convert_opponent_benched_pokemon(cls, stimulus: Mapping[BattleConcept, nd.NumDict]) -> List[PokemonSimulation]:
        benched_pokemon = []
        team_stim = stimulus[BattleConcept.OPPONENT_TEAM]
        for pokemon_chunk in team_stim.keys():
            if pokemon_chunk.get_feature_value('active'):
                continue
            simulated_pokemon = cls._convert_opponent_pokemon(pokemon_chunk)
            benched_pokemon.append(simulated_pokemon)

        return benched_pokemon


class BattleSimulationAdapter(Simulation):
    def __init__(self, battle_tag):
        super().__init__(battle_tag)

    def find_best_move(self):
        raise NotImplementedError('Adapter is intended to be controlled externally')

    @classmethod
    def from_battle(cls, battle: Battle) -> 'BattleSimulationAdapter':
        simulation = BattleSimulationAdapter(battle.battle_tag)
        simulation.user = cls._convert_player(battle)
        simulation.opponent = cls._convert_opponent(battle)

        if len(battle.weather) > 0:
            weather = next(iter(battle.weather))
            simulation.weather = normalize_name(weather.name).replace("_", "")

        if len(battle.fields) > 0:
            field_effect = next(iter(battle.fields))
            simulation.field = normalize_name(field_effect.name).replace("_", "")

        simulation.trick_room = Field.TRICK_ROOM in battle.fields
        simulation.turn = battle.turn
        simulation.force_switch = battle.force_switch
        simulation.wait = battle._wait
        simulation.generation = 'gen9'

        return simulation

    @classmethod
    def _convert_player(cls, battle: Battle) -> Battler:
        user = Battler()
        user.name = battle.player_username
        user.account_name = battle.player_username
        user.active = cls._convert_player_pokemon(battle.active_pokemon, battle) if battle.active_pokemon is not None else None
        user.reserve = [cls._convert_player_pokemon(pokemon, battle) for pokemon in battle.available_switches]
        user.trapped = Effect.TRAPPED in battle.active_pokemon.effects if battle.active_pokemon is not None else False
        user.side_conditions = defaultdict(lambda: 0, {normalize_name(condition.name).replace("_", ""): value for condition, value in battle.side_conditions.items()})

        return user

    @classmethod
    def _convert_opponent(cls, battle: Battle) -> Battler:
        user = Battler()
        user.name = battle.opponent_username
        user.account_name = battle.opponent_username
        user.active = cls._convert_opponent_pokemon(battle.opponent_active_pokemon) if battle.opponent_active_pokemon is not None else None
        user.reserve = [cls._convert_opponent_pokemon(pokemon) for pokemon in battle.opponent_team.values() if not pokemon.active]
        user.trapped = Effect.TRAPPED in battle.opponent_active_pokemon.effects if battle.opponent_active_pokemon is not None else False
        user.side_conditions = defaultdict(lambda: 0, {normalize_name(condition.name).replace("_", ""): value for condition, value in battle.opponent_side_conditions.items()})

        return user

    @staticmethod
    def _convert_player_pokemon(pokemon: Pokemon, battle: Battle) -> PokemonSimulation:
        simulated = PokemonSimulation(pokemon.species, pokemon.level)
        simulated.fainted = pokemon.fainted
        simulated.status = normalize_name(pokemon.status.name) if pokemon.status is not None else None
        simulated.stats = {
            constants.ATTACK: pokemon.stats['atk'],
            constants.DEFENSE: pokemon.stats['def'],
            constants.SPECIAL_ATTACK: pokemon.stats['spa'],
            constants.SPECIAL_DEFENSE: pokemon.stats['spd'],
            constants.SPEED: pokemon.stats['spe']
        }
        simulated.hp = pokemon.current_hp
        simulated.max_hp = pokemon.max_hp
        simulated.item = pokemon.item
        simulated.ability = pokemon.ability

        moves = battle.available_moves if pokemon.active else [move for move in pokemon.moves.values() if move.current_pp > 0]
        for move in moves:
            simulated.add_move(move.id)

        simulated.volatile_statuses = [normalize_name(effect.name).replace("_", "") for effect, count in pokemon.effects.items() if count > 0]
        simulated.boosts = {
            constants.ACCURACY: pokemon.boosts['accuracy'],
            constants.EVASION: pokemon.boosts['evasion'],
            constants.ATTACK: pokemon.boosts['atk'],
            constants.DEFENSE: pokemon.boosts['def'],
            constants.SPECIAL_ATTACK: pokemon.boosts['spa'],
            constants.SPECIAL_DEFENSE: pokemon.boosts['spd'],
            constants.SPEED: pokemon.boosts['spe']
        }
        simulated.terastallized = pokemon.terastallized
        simulated.types = [normalize_name(type.name) for type in pokemon.types if type is not None]

        return simulated

    @staticmethod
    def _convert_opponent_pokemon(pokemon: Pokemon) -> PokemonSimulation:
        simulated = PokemonSimulation(pokemon.species, pokemon.level)
        simulated.fainted = pokemon.fainted
        simulated.status = normalize_name(pokemon.status.name) if pokemon.status is not None else None
        simulated.set_most_likely_spread()
        simulated.hp = (pokemon.current_hp / 100.0) * simulated.max_hp

        if pokemon.ability is not None:
            simulated.ability = pokemon.ability
        else:
            simulated.set_most_likely_ability_unless_revealed()

        if pokemon.item is not None:
            simulated.item = pokemon.item
        else:
            simulated.set_most_likely_item_unless_revealed()

        for move in pokemon.moves.values():
            simulated.add_move(move.id)
        if len(simulated.moves) < 4:
            simulated.set_likely_moves_unless_revealed()

        simulated.volatile_statuses = [normalize_name(effect.name).replace("_", "") for effect, count in pokemon.effects.items() if count > 0]

        simulated.boosts = {
            constants.ACCURACY: pokemon.boosts['accuracy'],
            constants.EVASION: pokemon.boosts['evasion'],
            constants.ATTACK: pokemon.boosts['atk'],
            constants.DEFENSE: pokemon.boosts['def'],
            constants.SPECIAL_ATTACK: pokemon.boosts['spa'],
            constants.SPECIAL_DEFENSE: pokemon.boosts['spd'],
            constants.SPEED: pokemon.boosts['spe']
        }

        simulated.terastallized = pokemon.terastallized
        simulated.types = [normalize_name(type.name) for type in pokemon.types if type is not None]

        return simulated
