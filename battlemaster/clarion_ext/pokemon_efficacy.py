from typing import Mapping, Any, List

import pyClarion as cl
from pyClarion import nd
from poke_env.environment import PokemonType
from poke_env.data import GenData

from .numdicts_ext import normalize, get_feature_value_by_name

_SUPER_EFFECTIVE_THRESHOLD = 1.9


class SuperEffectiveMoves(cl.Process):
    _serves = cl.ConstructType.flow_tt

    def __init__(self, type_source: cl.Symbol, move_source: cl.Symbol, move_chunks: cl.Chunks):
        super().__init__(expected=[type_source, move_source])
        self._type_source = type_source
        self._move_source = move_source
        self._move_chunks = move_chunks
        self._type_chart = GenData.from_gen(9).type_chart

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        result = nd.MutableNumDict(default=0.0)
        defending_type = inputs[cl.expand_address(self.client, self._type_source)]
        moves = inputs[cl.expand_address(self.client, self._move_source)]

        for move in moves.keys():
            move_type = get_feature_value_by_name('type', move, self._move_chunks)
            damage_multiplier = self._get_efficacy(move_type, [type.cid for type in defending_type.keys()])
            result[move] = damage_multiplier

        result = nd.threshold(result, th=_SUPER_EFFECTIVE_THRESHOLD, keep_default=True)
        return normalize(result)


    def _get_efficacy(self, attack_type: str, defending_types: List[str]) -> float:
        attack_type = PokemonType.from_name(attack_type)
        defending_types = (PokemonType.from_name(defending_types[0]),
                           PokemonType.from_name(defending_types[1]) if len(defending_types) > 1 else None)

        return attack_type.damage_multiplier(defending_types[0], defending_types[1], type_chart=self._type_chart)
