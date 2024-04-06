import logging
from typing import Mapping, Optional, Dict
from enum import Enum

import pyClarion as cl
from pyClarion import nd
from poke_env.environment import (
    Battle, Pokemon, SideCondition, STACKABLE_CONDITIONS, Weather, Field
)

from ..clarion_ext.attention import GroupedStimulusInput


class BattleConcept(str, Enum):
    ACTIVE_OPPONENT_TYPE = 'active_opponent_type'
    AVAILABLE_MOVES = 'available_moves'
    AVAILABLE_SWITCHES = 'available_switches'
    PLAYERS = 'players'
    ACTIVE_POKEMON = 'active_pokemon'
    TEAM = 'team'
    SIDE_CONDITIONS = 'side_conditions'
    OPPONENT_ACTIVE_POKEMON = 'opponent_active_pokemon'
    OPPONENT_TEAM = 'opponent_team'
    OPPONENT_SIDE_CONDITIONS = 'opponent_side_conditions'
    WEATHER = 'weather'
    FIELD_EFFECTS = 'field_effects'
    BATTLE = "battle"

    def __str__(self) -> str:
        return self.value


class MindAdapter:
    def __init__(self, mind: cl.Structure, stimulus: cl.Construct, factory: 'PerceptionFactory'):
        self._mind = mind
        self._stimulus = stimulus
        self._factory = factory
        self._logger = logging.getLogger(f"{__name__}")

    def perceive(self, battle: Battle) -> Mapping[str, nd.NumDict]:
        perception = self._factory.map(battle)

        self._stimulus.process.input(perception)
        self._mind.step()
        self._logger.info(cl.pprint(self._mind.output))

        return perception.to_stimulus()

    def choose_action(self) -> Optional[str]:
        acs_terminus = self._mind[cl.subsystem('acs')][cl.terminus("choose_move")]
        acs_output = [action_chunk.cid for action_chunk in acs_terminus.output.keys()]
        return acs_output[0] if len(acs_output) > 0 else None


class PerceptionFactory:
    def map(self, battle: Battle) -> GroupedStimulusInput:
        perception = GroupedStimulusInput([concept for concept in BattleConcept])

        self._add_battle_metadata(battle, perception)
        self._add_players(battle, perception)

        self._add_player_active_pokemon(battle.active_pokemon, perception)
        self._add_available_moves(battle, perception)
        self._add_available_switches(battle, perception)
        self._add_player_team(battle.team, perception)
        self._add_side_conditions(battle.side_conditions, BattleConcept.SIDE_CONDITIONS, perception)

        self._add_opponent_active_pokemon(battle.opponent_active_pokemon, perception)
        self._add_active_opponent_pokemon_types(battle, perception)
        self._add_opponent_team(battle.opponent_team, perception)
        self._add_side_conditions(battle.opponent_side_conditions, BattleConcept.OPPONENT_SIDE_CONDITIONS, perception)

        self._add_weather(battle.weather, perception)
        self._add_field_effects(battle.fields, perception)

        return perception

    @staticmethod
    def _add_battle_metadata(battle: Battle, perception: GroupedStimulusInput):
        features = [
            cl.feature('tag', battle.battle_tag),
            cl.feature('force_switch', battle.force_switch),
            cl.feature('wait', battle._wait),
            cl.feature('format', battle._format),
            cl.feature('is_team_preview', battle.in_team_preview),
            cl.feature('turn', battle.turn)
        ]
        perception.add_chunk_instance_to_group(cl.chunk('metadata'), BattleConcept.BATTLE, features)

    @staticmethod
    def _add_players(battle: Battle, perception: GroupedStimulusInput):
        self_features = [
            cl.feature('name', battle.player_username),
            cl.feature('role', battle.player_role),
            cl.feature('rating', battle.rating)
        ]
        perception.add_chunk_instance_to_group(cl.chunk('self'), BattleConcept.PLAYERS, self_features)

        opponent_features = [
            cl.feature('name', battle.opponent_username),
            cl.feature('role', battle.opponent_role),
            cl.feature('rating', battle.opponent_rating)
        ]
        perception.add_chunk_instance_to_group(cl.chunk('opponent'), BattleConcept.PLAYERS, opponent_features)

    @staticmethod
    def _add_active_opponent_pokemon_types(battle: Battle, perception: GroupedStimulusInput):
        type_chunks = [cl.chunk(typing.name.lower()) for typing in battle.opponent_active_pokemon.types if typing is not None]
        perception.add_chunks_to_group(type_chunks, BattleConcept.ACTIVE_OPPONENT_TYPE)

    @staticmethod
    def _add_available_moves(battle: Battle, perception: GroupedStimulusInput):
        move_chunks = [cl.chunk(move.id) for move in battle.available_moves]
        perception.add_chunks_to_group(move_chunks, BattleConcept.AVAILABLE_MOVES)

    @staticmethod
    def _add_available_switches(battle: Battle, perception: GroupedStimulusInput):
        pokemon_chunks = [cl.chunk(pokemon.species) for pokemon in battle.available_switches]
        perception.add_chunks_to_group(pokemon_chunks, BattleConcept.AVAILABLE_SWITCHES)

    @classmethod
    def _add_player_active_pokemon(cls, pokemon: Pokemon, perception: GroupedStimulusInput):
        if pokemon is None:
            return
        cls._add_player_pokemon(pokemon, BattleConcept.ACTIVE_POKEMON, perception)

    @classmethod
    def _add_player_team(cls, team: Dict[str, Pokemon], perception: GroupedStimulusInput):
        for pokemon in team.values():
            if pokemon.active:
                continue
            cls._add_player_pokemon(pokemon, BattleConcept.TEAM, perception)

    @classmethod
    def _add_side_conditions(cls, side_conditions: Dict[SideCondition, int], group: str, perception: GroupedStimulusInput):
        for condition, value in side_conditions.items():
            chunk = cl.chunk(cls._normalize_name(condition))
            features = []
            if condition in STACKABLE_CONDITIONS:
                features.append(cl.feature('layers', value))
            else:
                features.append(cl.feature('start_turn', value))

            perception.add_chunk_instance_to_group(chunk, group, features)

    @classmethod
    def _add_opponent_active_pokemon(cls, pokemon: Pokemon, perception: GroupedStimulusInput):
        if pokemon is None:
            return
        cls._add_opponent_pokemon(pokemon, BattleConcept.OPPONENT_ACTIVE_POKEMON, perception)

    @classmethod
    def _add_opponent_team(cls, team: Dict[str, Pokemon], perception: GroupedStimulusInput):
        for pokemon in team.values():
            if pokemon.active:
                continue
            cls._add_opponent_pokemon(pokemon, BattleConcept.OPPONENT_TEAM, perception)

    @classmethod
    def _add_weather(cls, weather_turn_map: Dict[Weather, int], perception: GroupedStimulusInput):
        for weather, turn in weather_turn_map.items():
            chunk = cl.chunk(cls._normalize_name(weather))
            perception.add_chunk_instance_to_group(chunk,
                                                   BattleConcept.WEATHER,
                                                   [cl.feature('start_turn', turn)])

    @classmethod
    def _add_field_effects(cls, fields: Dict[Field, int], perception: GroupedStimulusInput):
        for field, turn in fields.items():
            chunk = cl.chunk(cls._normalize_name(field))
            perception.add_chunk_instance_to_group(chunk,
                                                   BattleConcept.FIELD_EFFECTS,
                                                   [cl.feature('start_turn', turn)])

    @classmethod
    def _add_player_pokemon(cls, pokemon: Pokemon, group: str, perception: GroupedStimulusInput):
        features = [
            *[cl.feature('type', cls._normalize_name(typing)) for typing in pokemon.types if typing is not None],
            cl.feature('level', pokemon.level),
            cl.feature('fainted', pokemon.fainted),
            cl.feature('active', pokemon.active),
            cl.feature('status', cls._normalize_name(pokemon.status) if pokemon.status is not None else None),
            *[cl.feature('volatile_status', cls._normalize_name(effect)) for effect in pokemon.effects.keys()],
            *[cl.feature(stat, pokemon.stats[stat]) for stat in ['atk', 'def', 'spa', 'spd', 'spe']],
            cl.feature('hp', pokemon.current_hp),
            cl.feature('max_hp', pokemon.max_hp),
            cl.feature('item', pokemon.item),
            cl.feature('ability', pokemon.ability),
            *[cl.feature('move', name) for name, move in pokemon.moves.items() if move.current_pp > 0],
            *[cl.feature(f'{stat}_boost', pokemon.boosts[stat]) for stat in ['atk', 'def', 'spa', 'spd', 'spe', 'accuracy', 'evasion']],
            cl.feature('terastallized', pokemon.terastallized)
        ]

        perception.add_chunk_instance_to_group(cl.chunk(pokemon.species), group, features)

    @classmethod
    def _add_opponent_pokemon(cls, pokemon: Pokemon, group: str, perception: GroupedStimulusInput):
        features = [
            *[cl.feature('type', cls._normalize_name(typing)) for typing in pokemon.types if typing is not None],
            cl.feature('level', pokemon.level),
            cl.feature('fainted', pokemon.fainted),
            cl.feature('active', pokemon.active),
            cl.feature('status', cls._normalize_name(pokemon.status) if pokemon.status is not None else None),
            *[cl.feature('volatile_status', cls._normalize_name(effect)) for effect in pokemon.effects.keys()],
            cl.feature('hp_percentage', pokemon.current_hp),
            cl.feature('item', pokemon.item),
            cl.feature('ability', pokemon.ability),
            *[cl.feature('move', name) for name, move in pokemon.moves.items() if move.current_pp > 0],
            *[cl.feature(f'{stat}_boost', pokemon.boosts[stat]) for stat in ['atk', 'def', 'spa', 'spd', 'spe', 'accuracy', 'evasion']],
            cl.feature('terastallized', pokemon.terastallized)
        ]

        perception.add_chunk_instance_to_group(cl.chunk(pokemon.species), group, features)

    @staticmethod
    def _normalize_name(enum: Enum):
        return enum.name\
            .lower()\
            .replace("_", "")
