from typing import Mapping, Optional
from enum import Enum

import pyClarion as cl
from pyClarion import nd
from poke_env.environment import Battle, Pokemon

from ..clarion_ext.attention import GroupedStimulusInput


class BattleConcept(str, Enum):
    BATTLE_TAG = "battle_tag"
    ACTIVE_OPPONENT_TYPE = 'active_opponent_type'
    AVAILABLE_MOVES = 'available_moves'
    PLAYERS = 'players'
    ACTIVE_POKEMON = 'active_pokemon'
    TEAM = 'team'
    OPPONENT_ACTIVE_POKEMON = 'opponent_active_pokemon'
    OPPONENT_TEAM = 'opponent_team'

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

        self._add_active_pokemon_types(battle, perception)
        self._add_available_moves(battle, perception)
        #self._add_pokemon(battle.active_pokemon, BattleConcept.ACTIVE_POKEMON.value, perception)

        return perception

    @staticmethod
    def _add_active_pokemon_types(battle: Battle, perception: GroupedStimulusInput):
        type_chunks = [cl.chunk(typing.name.lower()) for typing in battle.opponent_active_pokemon.types if typing is not None]
        perception.add_chunks_to_group(type_chunks, BattleConcept.ACTIVE_OPPONENT_TYPE.value)

    @staticmethod
    def _add_available_moves(battle: Battle, perception: GroupedStimulusInput):
        move_chunks = [cl.chunk(move.id) for move in battle.available_moves]
        perception.add_chunks_to_group(move_chunks, BattleConcept.AVAILABLE_MOVES.value)

    @staticmethod
    def _add_pokemon(pokemon: Pokemon, group: str, perception: GroupedStimulusInput):
        if pokemon is None:
            return

        features = [
            cl.feature('level', pokemon.level),
            cl.feature('fainted', pokemon.fainted),
            cl.feature('active', pokemon.active),
            cl.feature('status', pokemon.status),
            *[cl.feature('volatile_status', effect) for effect in pokemon.effects.keys()],
            *[cl.feature(stat, pokemon.status[stat]) for stat in ['atk', 'def', 'spa', 'spd', 'spe']],
            cl.feature('hp', pokemon.current_hp),
            cl.feature('max_hp', pokemon.max_hp),
            cl.feature('item', pokemon.item),
            *[cl.feature('move', move) for move in pokemon.moves.keys()],
            *[cl.feature(f'{stat}_boost', pokemon.boosts[stat]) for stat in ['atk', 'def', 'spa', 'spd', 'spe', 'accuracy', 'evasion']],
            cl.feature('terastallized', pokemon.terastallized)
        ]

        perception.add_chunk_instance_to_group(cl.chunk(pokemon.species), group, features)
