from typing import Mapping, Optional
from enum import Enum

import pyClarion as cl
from pyClarion import nd
from poke_env.environment import Battle

from ..clarion_ext.attention import GroupedStimulusInput


class BattleConcept(str, Enum):
    ACTIVE_OPPONENT_TYPE = 'active_opponent_type'
    AVAILABLE_MOVES = 'available_moves'
    PLAYERS = 'players'
    ACTIVE_POKEMON = 'active_pokemon'
    TEAM_SLOT_1 = 'team_slot_1'
    OPPONENT_ACTIVE_POKEMON = 'opponent_active_pokemon'

    def __str__(self) -> str:
        return self.value


class MindAdapter:

    def __init__(self, mind: cl.Structure, stimulus: cl.Construct):
        self._mind = mind
        self._stimulus = stimulus

    def perceive(self, battle: Battle) -> Mapping[str, nd.NumDict]:
        perception = GroupedStimulusInput([BattleConcept.ACTIVE_OPPONENT_TYPE.value, BattleConcept.AVAILABLE_MOVES.value])
        for typing in battle.opponent_active_pokemon.types:
            if typing is None:
                continue
            perception.add_chunk_to_group(cl.chunk(typing.name.lower()), BattleConcept.ACTIVE_OPPONENT_TYPE.value)

        for move in battle.available_moves:
            perception.add_chunk_to_group(cl.chunk(move.id), BattleConcept.ACTIVE_OPPONENT_TYPE.value)

        self._stimulus.process.input(perception)
        self._mind.step()

        return perception.to_stimulus()

    def choose_action(self) -> Optional[str]:
        acs_terminus = self._mind[cl.subsystem('acs')][cl.terminus("choose_move")]
        acs_output = [move_name.cid for move_name in acs_terminus.output.keys()]
        return acs_output[0] if len(acs_output) > 0 else None
