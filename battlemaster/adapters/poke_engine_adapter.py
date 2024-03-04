from typing import Mapping, Any
from collections import defaultdict

from poke_env.environment import Battle, Pokemon, Effect, Field
from poke_engine import Battle as Simulation, Battler, Pokemon as PokemonSimulation, constants, StateMutator
from poke_engine.select_best_move import get_payoff_matrix, pick_safest
from poke_engine.battle_modifier import check_speed_ranges
from poke_engine.helpers import normalize_name
from pyClarion import nd

from .clarion_adapter import BattleConcept
from ..clarion_ext.attention import GroupedChunkInstance
from ..clarion_ext.numdicts_ext import get_chunk_from_numdict


class Simulator:
    def __init__(self):
        pass

    def pick_safest_move(self, simulation: Simulation) -> str:
        battles = simulation.prepare_battles(join_moves_together=True)
        all_scores = dict()
        for i, b in enumerate(battles):
            state = b.create_state()
            mutator = StateMutator(state)
            user_options, opponent_options = b.get_all_options()
            scores = get_payoff_matrix(mutator, user_options, opponent_options, prune=True)

            prefixed_scores = self._prefix_opponent_move(scores, str(i))
            all_scores = {**all_scores, **prefixed_scores}

        decision, payoff = pick_safest(all_scores, remove_guaranteed=True)
        choice = decision[0]
        return choice

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

    @classmethod
    def _convert_player(cls, stimulus: Mapping[BattleConcept, nd.NumDict]) -> Battler:
        player_stim: GroupedChunkInstance = get_chunk_from_numdict('self', stimulus[BattleConcept.PLAYERS])

        user = Battler()
        user.name = player_stim.get_feature_value('name')
        user.account_name = user.name

        user.active = cls._convert_player_pokemon(stimulus) if BattleConcept.ACTIVE_POKEMON in stimulus else None
        user.reserve = [cls._convert_player_pokemon(stimulus) for pokemon in battle.available_switches]
        user.trapped = Effect.TRAPPED in battle.active_pokemon.effects if battle.active_pokemon is not None else False
        user.side_conditions = defaultdict(lambda: 0,
                                           {normalize_name(condition.name).replace("_", ""): value for condition, value
                                            in battle.side_conditions.items()})

        return user

    @staticmethod
    def _convert_player_pokemon(stimulus: Mapping[BattleConcept, nd.NumDict]) -> PokemonSimulation:
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
        for move in battle.available_moves:
            simulated.add_move(move.id)
        simulated.volatile_statuses = [normalize_name(effect.name).replace("_", "") for effect, count in
                                       pokemon.effects.items() if count > 0]
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
        check_speed_ranges(battle, '')

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

        for move in [move for move in pokemon.moves.values() if move.current_pp > 0]:
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
