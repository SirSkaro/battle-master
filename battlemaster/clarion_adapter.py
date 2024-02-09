from typing import Mapping, Optional

import pyClarion as cl
from pyClarion import nd
from poke_env.environment import Battle


class MindAdapter:

    def __init__(self, mind: cl.Structure, stimulus: cl.Construct):
        self._mind = mind
        self._stimulus = stimulus

    def perceive(self, battle: Battle) -> Mapping[str, nd.NumDict]:
        perception = {
            'active_opponent_type': nd.NumDict({cl.chunk(typing.name): 1.0 for typing in battle.opponent_active_pokemon.types if typing is not None}),
            'available_moves': nd.NumDict({cl.chunk(move.id): 1.0 for move in battle.available_moves})
        }

        self._stimulus.process.input(perception)
        self._mind.step()

        return perception

    def choose_action(self) -> Optional[str]:
        acs_terminus = self._mind[cl.subsystem('acs')][cl.terminus("choose_move")]
        acs_output = [move_name.val for move_name in acs_terminus.output.keys()]
        return acs_output[0] if len(acs_output) > 0 else None
