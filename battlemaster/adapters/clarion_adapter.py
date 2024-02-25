from typing import Mapping, Optional
from enum import Enum

import pyClarion as cl
from pyClarion import nd
from poke_env.environment import Battle

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

    def __init__(self, mind: cl.Structure, stimulus: cl.Construct):
        self._mind = mind
        self._stimulus = stimulus
        self._factory = PerceptionFactory()

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

        return perception

    @staticmethod
    def _add_active_pokemon_types(battle: Battle, perception: GroupedStimulusInput):
        for typing in battle.opponent_active_pokemon.types:
            if typing is None:
                continue
            perception.add_chunk_to_group(cl.chunk(typing.name.lower()), BattleConcept.ACTIVE_OPPONENT_TYPE.value)

    @staticmethod
    def _add_available_moves(battle: Battle, perception: GroupedStimulusInput):
        for move in battle.available_moves:
            perception.add_chunk_to_group(cl.chunk(move.id), BattleConcept.AVAILABLE_MOVES.value)
