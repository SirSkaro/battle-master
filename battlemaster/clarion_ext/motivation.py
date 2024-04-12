from abc import abstractmethod
from enum import Enum
import typing
from typing import Mapping, Any, Dict, Callable, Hashable

import pyClarion as cl
from pyClarion import nd
from pyClarion import feature

from ..adapters.clarion_adapter import BattleConcept
from ..clarion_ext.attention import GroupedChunkInstance
from .numdicts_ext import filter_chunks_by_group, get_chunk_from_numdict, get_only_value_from_numdict


class drive(feature, Enum):
    KEEP_POKEMON_ALIVE = 'keep_pokemon_alive'
    HAVE_MORE_POKEMON_THAN_OPPONENT = 'have_more_pokemon_than_opponent'
    KO_OPPONENT = 'ko_opponent'
    DO_DAMAGE = 'do_damage'
    KEEP_HEALTHY = 'keep_healthy'
    BUFF_SELF = 'buff_self'
    DEBUFF_OPPONENT = 'debuff_opponent'
    PREVENT_OPPONENT_BUFF = 'prevent_opponent_buff'
    KEEP_TYPE_ADVANTAGE = 'keep_type_advantage'
    PREVENT_TYPE_DISADVANTAGE = 'prevent_type_disadvantage'
    HAVE_SUPER_EFFECTIVE_MOVE_AVAILABLE = 'have_super_effective_move_available'
    REVEAL_HIDDEN_INFORMATION = 'reveal_hidden_information'

    def __setattr__(self, key, value):
        if key.startswith('_'):
            super(Enum, self).__setattr__(key, value)
        else:
            super(feature, self).__setattr__(key, value)


class GoalType(Enum):
    ANY = 'any'
    MOVE = 'move'
    SWITCH = 'switch'


class goal(cl.chunk):
    """A goal symbol that can be treated like a normal chunk."""
    __slots__ = ('type',)
    type: GoalType

    def __init__(self, cid: Hashable, type: GoalType = GoalType.ANY):
        self.type = type
        super().__init__(cid)

    def __repr__(self):
        cls_name = type(self).__name__
        return "{}({}|{})".format(cls_name, self.cid, self.type.value())

    def __setattr__(self, key, value):
        object.__setattr__(self, key, value)


DRIVE_DOMAIN = cl.Domain(features=tuple([d for d in drive]))
GroupedStimulus = Mapping[BattleConcept, nd.NumDict]


class DriveStrength(cl.Process):
    _serves = cl.ConstructType.features

    def __init__(self, stimulus_source: cl.Symbol, personality_map: Dict[drive, Callable[[GroupedStimulus], float]]):
        super().__init__(expected=[stimulus_source])
        self._stimulus_source = stimulus_source
        self._drive_evaluations = personality_map

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        result = nd.MutableNumDict(default=0.)
        stimulus = inputs[cl.expand_address(self.client, self._stimulus_source)]
        grouped_stimulus = self._group_stimulus(stimulus)
        for drive in DRIVE_DOMAIN.features:
            if drive in self._drive_evaluations:
                result[drive] = self._drive_evaluations[drive](grouped_stimulus)

        return result

    @staticmethod
    def _group_stimulus(stimulus: nd.NumDict) -> GroupedStimulus:
        return {concept: filter_chunks_by_group(concept, stimulus) for concept in BattleConcept}


class DriveEvaluator:
    '''
    A method to evaluate a drive strength. A value between [0,5].
    '''
    @abstractmethod
    def evaluate(self, stimulus: GroupedStimulus) -> float:
        pass


class DoDamageDriveEvaluator(DriveEvaluator):
    def evaluate(self, stimulus: GroupedStimulus) -> float:
        battle_metadata = typing.cast(GroupedChunkInstance, get_chunk_from_numdict('metadata', stimulus[BattleConcept.BATTLE]))
        is_force_switch_turn = battle_metadata.get_feature_value('force_switch')
        return 0.0 if is_force_switch_turn else 5.


class KoOpponentDriveEvaluator(DriveEvaluator):
    def evaluate(self, stimulus: GroupedStimulus) -> float:
        opponent_active_pokemon_perception = stimulus[BattleConcept.OPPONENT_ACTIVE_POKEMON]
        if len(opponent_active_pokemon_perception) == 0:
            return 0.

        opponent_active_pokemon = typing.cast(GroupedChunkInstance, get_only_value_from_numdict(opponent_active_pokemon_perception))
        hp_percentage = opponent_active_pokemon.get_feature_value('hp_percentage')
        return ((100 - hp_percentage) / 20) + 0.05


class KeepPokemonAliveEvaluator(DriveEvaluator):
    def evaluate(self, stimulus: GroupedStimulus) -> float:
        active_pokemon_perception = stimulus[BattleConcept.ACTIVE_POKEMON]
        if len(active_pokemon_perception) == 0:
            return 0.

        active_pokemon = typing.cast(GroupedChunkInstance, get_only_value_from_numdict(active_pokemon_perception))
        hp = active_pokemon.get_feature_value('hp')
        max_hp = active_pokemon.get_feature_value('max_hp')
        hp_percentage = hp / max_hp
        drive_multiplier = 1.0 - hp_percentage

        if hp == 1:
            return 5.
        elif drive_multiplier <= 0.01:
            return 0.05
        else:
            return drive_multiplier * 5


class KeepHealthyEvaluator(DriveEvaluator):
    def evaluate(self, stimulus: GroupedStimulus) -> float:
        active_pokemon_perception = stimulus[BattleConcept.ACTIVE_POKEMON]
        if len(active_pokemon_perception) == 0:
            return 0.

        active_pokemon = typing.cast(GroupedChunkInstance, get_only_value_from_numdict(active_pokemon_perception))
        hp = active_pokemon.get_feature_value('hp')
        max_hp = active_pokemon.get_feature_value('max_hp')
        hp_percentage = hp / max_hp

        if hp_percentage <= 0.05:
            return 0.05
        return hp_percentage * 5


class ConstantDriveEvaluator(DriveEvaluator):
    def __init__(self, strength: float):
        super().__init__()
        self._strength = strength

    def evaluate(self, stimulus: GroupedStimulus) -> float:
        return self._strength

# TODO class KeepTypeAdvantageDriveEvaluator(DriveEvaluator):