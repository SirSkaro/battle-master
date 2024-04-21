from typing import Mapping, Any, List
import logging

import pyClarion as cl
from pyClarion import nd
from poke_env.environment import PokemonType
from poke_env.data import GenData

from .numdicts_ext import absolute_normalize, get_feature_value_by_name, get_features_by_name

_EFFECTIVE_THRESHOLD = 0.9
_MAX_EFFECTIVENESS_MULTIPLIER = 4.0


def _get_efficacy(type_chart, attack_type: str, defending_types: List[str]) -> float:
    attack_type = PokemonType.from_name(attack_type)
    defending_types = (PokemonType.from_name(defending_types[0]),
                       PokemonType.from_name(defending_types[1]) if len(defending_types) > 1 else None)

    return attack_type.damage_multiplier(defending_types[0], defending_types[1], type_chart=type_chart)


class EffectiveMoves(cl.Process):
    _serves = cl.ConstructType.flow_tt

    def __init__(self, type_source: cl.Symbol, move_source: cl.Symbol, move_chunks: cl.Chunks):
        super().__init__(expected=[type_source, move_source])
        self._type_source = type_source
        self._move_source = move_source
        self._move_chunks = move_chunks
        self._type_chart = GenData.from_gen(9).type_chart
        self._logger = logging.getLogger(f"{__name__}")

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        result = nd.MutableNumDict(default=0.0)
        defending_type = inputs[cl.expand_address(self.client, self._type_source)]
        moves = inputs[cl.expand_address(self.client, self._move_source)]

        for move in moves.keys():
            if move not in self._move_chunks:
                result[move] = 1.0
                self._logger.warning(f"Encountered unknown move {move}. Assuming normal efficacy.")
                continue

            move_type = get_feature_value_by_name('type', move, self._move_chunks)
            damage_multiplier = _get_efficacy(self._type_chart, move_type, [type.cid for type in defending_type.keys()])
            result[move] = damage_multiplier

        result = nd.threshold(result, th=_EFFECTIVE_THRESHOLD, keep_default=True)
        return absolute_normalize(result, _MAX_EFFECTIVENESS_MULTIPLIER)


class EffectiveSwitches(cl.Process):
    _serves = cl.ConstructType.flow_tt

    def __init__(self, type_source: cl.Symbol, switch_source: cl.Symbol, pokemon_chunks: cl.Chunks):
        super().__init__(expected=[type_source, switch_source])
        self._type_source = type_source
        self._switch_source = switch_source
        self._pokemon_chunks = pokemon_chunks
        self._type_chart = GenData.from_gen(9).type_chart
        self._logger = logging.getLogger(f"{__name__}")

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        result = nd.MutableNumDict(default=0.0)
        defending_type = inputs[cl.expand_address(self.client, self._type_source)]
        switches = inputs[cl.expand_address(self.client, self._switch_source)]

        for switch in switches.keys():
            damage_multiplier = 1.0
            if switch not in self._pokemon_chunks:
                result[switch] = 1.0
                self._logger.warning(f"Encountered unknown pokemon {switch}. Assuming normal efficacy.")
                continue

            switch_types = [feature.val for feature in get_features_by_name('type', switch, self._pokemon_chunks)]
            for switch_type in switch_types:
                damage_multiplier *= _get_efficacy(self._type_chart, switch_type, [type.cid for type in defending_type.keys()])
            result[switch] = damage_multiplier

        result = nd.threshold(result, th=_EFFECTIVE_THRESHOLD, keep_default=True)
        return absolute_normalize(result, _MAX_EFFECTIVENESS_MULTIPLIER * len(switches))


class DefensiveSwitches(cl.Process):
    _serves = cl.ConstructType.flow_tt

    def __init__(self, type_source: cl.Symbol, switch_source: cl.Symbol, pokemon_chunks: cl.Chunks):
        super().__init__(expected=[type_source, switch_source])
        self._type_source = type_source
        self._switch_source = switch_source
        self._pokemon_chunks = pokemon_chunks
        self._type_chart = GenData.from_gen(9).type_chart
        self._logger = logging.getLogger(f"{__name__}")
        self._reverse_multiplier_map = {
            0.: 4.,
            0.25: 4.,
            0.5: 2.,
            1.: 1.,
            2.: 0.5,
            4.: 0.25
        }

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        result = nd.MutableNumDict(default=0.0)
        attacking_type: nd.NumDict = inputs[cl.expand_address(self.client, self._type_source)]
        switches = inputs[cl.expand_address(self.client, self._switch_source)]

        for switch in switches.keys():
            damage_multiplier = 1.0
            if switch not in self._pokemon_chunks:
                result[switch] = 1.0
                self._logger.warning(f"Encountered unknown pokemon {switch}. Assuming normal efficacy.")
                continue

            switch_types = [feature.val for feature in get_features_by_name('type', switch, self._pokemon_chunks)]
            for attack_type in attacking_type:
                damage_multiplier *= _get_efficacy(self._type_chart, attack_type.cid, switch_types)
            result[switch] = self._reverse_multiplier_map[damage_multiplier]

        result = nd.threshold(result, th=1.9, keep_default=True)
        return absolute_normalize(result, _MAX_EFFECTIVENESS_MULTIPLIER * len(switches))

