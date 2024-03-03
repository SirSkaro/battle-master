from typing import Mapping, Optional, Dict
from enum import Enum

import pyClarion as cl
from pyClarion import nd
from poke_env.environment import Battle, Pokemon, SideCondition, STACKABLE_CONDITIONS, Weather

from ..clarion_ext.attention import GroupedStimulusInput


class BattleConcept(str, Enum):
    BATTLE_TAG = "battle_tag"
    ACTIVE_OPPONENT_TYPE = 'active_opponent_type'
    AVAILABLE_MOVES = 'available_moves'
    PLAYERS = 'players'
    ACTIVE_POKEMON = 'active_pokemon'
    TEAM = 'team'
    SIDE_CONDITIONS = 'side_conditions'
    OPPONENT_ACTIVE_POKEMON = 'opponent_active_pokemon'
    OPPONENT_TEAM = 'opponent_team'
    OPPONENT_SIDE_CONDITIONS = 'opponent_side_conditions'
    WEATHER = 'weather'

    def __str__(self) -> str:
        return self.value


class MindAdapter:

    def __init__(self, mind: cl.Structure, stimulus: cl.Construct, factory: 'PerceptionFactory'):
        self._mind = mind
        self._stimulus = stimulus
        self._factory = factory

    def perceive(self, battle: Battle) -> Mapping[str, nd.NumDict]:
        perception = self._factory.map(battle)

        self._stimulus.process.input(perception)
        self._mind.step()

        return perception.to_stimulus()

    def choose_action(self) -> Optional[str]:
        acs_terminus = self._mind[cl.subsystem('acs')][cl.terminus("choose_move")]
        acs_output = [move_name.cid for move_name in acs_terminus.output.keys()]
        return acs_output[0] if len(acs_output) > 0 else None


class PerceptionFactory:
    def map(self, battle: Battle) -> GroupedStimulusInput:
        perception = GroupedStimulusInput([concept.value for concept in BattleConcept])

        self._add_players(battle, perception)

        self._add_player_active_pokemon(battle.active_pokemon, perception)
        self._add_available_moves(battle, perception)
        self._add_player_team(battle.team, perception)
        self._add_side_conditions(battle.side_conditions, BattleConcept.SIDE_CONDITIONS.value, perception)

        self._add_opponent_active_pokemon(battle.opponent_active_pokemon, perception)
        self._add_active_opponent_pokemon_types(battle, perception)
        self._add_opponent_team(battle.opponent_team, perception)
        self._add_side_conditions(battle.opponent_side_conditions, BattleConcept.OPPONENT_SIDE_CONDITIONS.value, perception)

        self._add_weather(battle.weather, perception)

        return perception

    @staticmethod
    def _add_players(battle: Battle, perception: GroupedStimulusInput):
        self_features = [cl.feature('name', battle.player_username), cl.feature('role', battle.player_role)]
        perception.add_chunk_instance_to_group(cl.chunk('self'), BattleConcept.PLAYERS, self_features)

        self_features = [cl.feature('name', battle.opponent_username), cl.feature('role', battle.opponent_role)]
        perception.add_chunk_instance_to_group(cl.chunk('opponent'), BattleConcept.PLAYERS, self_features)

    @staticmethod
    def _add_active_opponent_pokemon_types(battle: Battle, perception: GroupedStimulusInput):
        type_chunks = [cl.chunk(typing.name.lower()) for typing in battle.opponent_active_pokemon.types if typing is not None]
        perception.add_chunks_to_group(type_chunks, BattleConcept.ACTIVE_OPPONENT_TYPE.value)

    @staticmethod
    def _add_available_moves(battle: Battle, perception: GroupedStimulusInput):
        move_chunks = [cl.chunk(move.id) for move in battle.available_moves]
        perception.add_chunks_to_group(move_chunks, BattleConcept.AVAILABLE_MOVES.value)

    @classmethod
    def _add_player_active_pokemon(cls, pokemon: Pokemon, perception: GroupedStimulusInput):
        if pokemon is None:
            return
        cls._add_player_pokemon(pokemon, BattleConcept.ACTIVE_POKEMON.value, perception)

    @classmethod
    def _add_player_team(cls, team: Dict[str, Pokemon], perception: GroupedStimulusInput):
        for pokemon in team.values():
            cls._add_player_pokemon(pokemon, BattleConcept.TEAM, perception)

    @staticmethod
    def _add_side_conditions(side_conditions: Dict[SideCondition, int], group: str, perception: GroupedStimulusInput):
        for condition, value in side_conditions.items():
            features = []
            if condition in STACKABLE_CONDITIONS:
                features.append(cl.feature('layers', value))
            else:
                features.append(cl.feature('start_turn', value))

            perception.add_chunk_instance_to_group(cl.chunk(condition.name.lower()), group, features)

    @classmethod
    def _add_opponent_active_pokemon(cls, pokemon: Pokemon, perception: GroupedStimulusInput):
        if pokemon is None:
            return
        cls._add_opponent_pokemon(pokemon, BattleConcept.OPPONENT_ACTIVE_POKEMON.value, perception)

    @classmethod
    def _add_opponent_team(cls, team: Dict[str, Pokemon], perception: GroupedStimulusInput):
        for pokemon in team.values():
            cls._add_opponent_pokemon(pokemon, BattleConcept.OPPONENT_TEAM, perception)

    @staticmethod
    def _add_weather(weather_turn_map: Dict[Weather, int], perception: GroupedStimulusInput):
        for weather, turn in weather_turn_map.items():
            perception.add_chunk_instance_to_group(cl.chunk(weather.name.lower()),
                                                   BattleConcept.WEATHER.value,
                                                   [cl.feature('start_turn', turn)])

    @staticmethod
    def _add_player_pokemon(pokemon: Pokemon, group: str, perception: GroupedStimulusInput):
        features = [
            *[cl.feature('type', typing.name.lower()) for typing in pokemon.types if typing is not None],
            cl.feature('level', pokemon.level),
            cl.feature('fainted', pokemon.fainted),
            cl.feature('active', pokemon.active),
            cl.feature('status', pokemon.status.name.lower() if pokemon.status is not None else None),
            *[cl.feature('volatile_status', effect.name.lower()) for effect in pokemon.effects.keys()],
            *[cl.feature(stat, pokemon.stats[stat]) for stat in ['atk', 'def', 'spa', 'spd', 'spe']],
            cl.feature('hp', pokemon.current_hp),
            cl.feature('max_hp', pokemon.max_hp),
            cl.feature('item', pokemon.item),
            cl.feature('ability', pokemon.ability),
            *[cl.feature('move', move) for move in pokemon.moves.keys()],
            *[cl.feature(f'{stat}_boost', pokemon.boosts[stat]) for stat in ['atk', 'def', 'spa', 'spd', 'spe', 'accuracy', 'evasion']],
            cl.feature('terastallized', pokemon.terastallized)
        ]

        perception.add_chunk_instance_to_group(cl.chunk(pokemon.species), group, features)

    @staticmethod
    def _add_opponent_pokemon(pokemon: Pokemon, group: str, perception: GroupedStimulusInput):
        features = [
            *[cl.feature('type', typing.name.lower()) for typing in pokemon.types if typing is not None],
            cl.feature('level', pokemon.level),
            cl.feature('fainted', pokemon.fainted),
            cl.feature('active', pokemon.active),
            cl.feature('status', pokemon.status.name.lower() if pokemon.status is not None else None),
            *[cl.feature('volatile_status', effect.name.lower()) for effect in pokemon.effects.keys()],
            cl.feature('hp_percentage', pokemon.current_hp),
            cl.feature('item', pokemon.item),
            cl.feature('ability', pokemon.ability),
            *[cl.feature('move', move) for move in pokemon.moves.keys()],
            *[cl.feature(f'{stat}_boost', pokemon.boosts[stat]) for stat in ['atk', 'def', 'spa', 'spd', 'spe', 'accuracy', 'evasion']],
            cl.feature('terastallized', pokemon.terastallized)
        ]

        perception.add_chunk_instance_to_group(cl.chunk(pokemon.species), group, features)
