import logging
from abc import abstractmethod
from enum import Enum
import typing
from typing import Mapping, Any, Dict, Callable, Hashable, Tuple
import math

import pyClarion as cl
from pyClarion import nd
from pyClarion import feature

from ..adapters.clarion_adapter import BattleConcept
from ..clarion_ext.attention import GroupedChunkInstance
from .numdicts_ext import filter_chunks_by_group, get_chunk_from_numdict, get_only_value_from_numdict, is_empty


class GoalType(str, Enum):
    ANY = 'any', 0
    MOVE = 'move', 1
    SWITCH = 'switch', 2

    def __new__(cls, *args, **kwargs):
        obj = str.__new__(cls)
        obj._value_ = args[0]
        return obj

    def __init__(self, _: str, index: int):
        self._index = index

    def __str__(self) -> str:
        return self.value

    @property
    def index(self):
        return self._index


class goal(cl.chunk):
    """A goal symbol that can be treated like a normal chunk."""
    __slots__ = ('type',)
    type: GoalType

    def __init__(self, cid: Hashable, type: GoalType = GoalType.ANY):
        self.type = type
        super().__init__(cid)

    def __repr__(self):
        cls_name = type(self).__name__
        return "{}({}|{})".format(cls_name, self.cid, self.type.value)

    def __setattr__(self, key, value):
        object.__setattr__(self, key, value)


GOAL_GATE_INTERFACE = cl.ParamSet.Interface(
    name="goal",
    pmkrs=tuple(type.value for type in GoalType)
)


class GoalGateAdapter(cl.Process):
    '''
    The gating API in pyClarion is very awkward. This process only exists to turn a goal chunk into a weird feature that
    can control the goal gate.
    '''
    _serves = cl.ConstructType.features

    def __init__(self, goal_source: cl.Symbol):
        super().__init__(expected=[goal_source])
        self._goal_source = goal_source

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        goal_chunk: goal = get_only_value_from_numdict(inputs[cl.expand_address(self.client, self._goal_source)])
        goal_feature = cl.feature((GOAL_GATE_INTERFACE.name, goal_chunk.type.value))
        self._logger.debug(f"My goal is to {goal_feature}")
        return nd.NumDict({goal_feature: 1.}, default=0.)

    @property
    def _logger(self):
        return logging.getLogger(self.__class__.__name__)


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


class GaussianTargetEvaluator(DriveEvaluator):
    '''
    The closer the current percentage is to the target percentage, the stronger this drive evaluates. Uses a gaussian
    over the mean (target percentage) and takes the normalized output of the gaussian rather than sampling.
    '''
    def __init__(self, target_percentage):
        self.target_percentage = target_percentage

    @abstractmethod
    def evaluate(self, stimulus: GroupedStimulus) -> float:
        pass

    def calculate_drive_strength(self, current_percentage):
        max = self._normal_dist(self.target_percentage, self.target_percentage)
        normalized_multiplier = self._normal_dist(current_percentage, self.target_percentage) / max
        return 5 * normalized_multiplier

    @staticmethod
    def _normal_dist(x, mean, sigma=0.15):
        return (1 / (sigma * math.sqrt(2 * math.pi))) * (math.exp(-0.5 * math.pow(((x - mean) / sigma), 2)))


class InflictDamageAware:
    def can_do_damage(self, stimulus: GroupedStimulus) -> bool:
        battle_metadata = typing.cast(GroupedChunkInstance, get_chunk_from_numdict('metadata', stimulus[BattleConcept.BATTLE]))
        active_pokemon = stimulus[BattleConcept.ACTIVE_POKEMON]
        opponent_active_pokemon = stimulus[BattleConcept.OPPONENT_ACTIVE_POKEMON]

        is_force_switch_turn = battle_metadata.get_feature_value('force_switch')
        has_active_pokemon = not is_empty(active_pokemon)
        opponent_has_active_pokemon = not is_empty(opponent_active_pokemon)
        return has_active_pokemon and opponent_has_active_pokemon and not is_force_switch_turn


class DoDamageDriveEvaluator(DriveEvaluator, InflictDamageAware):
    def evaluate(self, stimulus: GroupedStimulus) -> float:
        can_do_damage = self.can_do_damage(stimulus)

        return 5.0 if can_do_damage else 0.


class KoOpponentDriveEvaluator(DriveEvaluator, InflictDamageAware):
    def evaluate(self, stimulus: GroupedStimulus) -> float:
        can_do_damage = self.can_do_damage(stimulus)
        if not can_do_damage:
            return 0.

        opponent_active_pokemon_perception = stimulus[BattleConcept.OPPONENT_ACTIVE_POKEMON]
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


class KeepHealthyEvaluator(GaussianTargetEvaluator):
    '''
    The closer the Pokemon is to the target health percentage, the stronger this drive evaluates
    '''
    def __init__(self, target_percentage):
        super(KeepHealthyEvaluator, self).__init__(target_percentage)

    def evaluate(self, stimulus: GroupedStimulus) -> float:
        active_pokemon_perception = stimulus[BattleConcept.ACTIVE_POKEMON]
        if len(active_pokemon_perception) == 0:
            return 0.

        active_pokemon = typing.cast(GroupedChunkInstance, get_only_value_from_numdict(active_pokemon_perception))
        hp = active_pokemon.get_feature_value('hp')
        max_hp = active_pokemon.get_feature_value('max_hp')
        hp_percentage = hp / max_hp

        return self.calculate_drive_strength(hp_percentage)


class KeepTypeAdvantageDriveEvaluator(DriveEvaluator):
    def evaluate(self, stimulus: GroupedStimulus) -> float:
        battle_metadata = typing.cast(GroupedChunkInstance, get_chunk_from_numdict('metadata', stimulus[BattleConcept.BATTLE]))
        is_force_switch_turn = battle_metadata.get_feature_value('force_switch')
        return 5.0 if is_force_switch_turn else 0.


class RevealHiddenInformationDriveEvaluator(DriveEvaluator):
    def evaluate(self, stimulus: GroupedStimulus) -> float:
        opponent_active_pokemon_perception: nd.NumDict = stimulus[BattleConcept.OPPONENT_ACTIVE_POKEMON]
        opponent_team_perception: nd.NumDict = stimulus[BattleConcept.OPPONENT_TEAM]
        total_pokemon_count, unknown_pokemon_count = self._count_unknown_pokemon(opponent_active_pokemon_perception, opponent_team_perception)
        total_move_count, unknown_move_count = self._count_unknown_moves(total_pokemon_count, opponent_active_pokemon_perception, opponent_team_perception)
        total_ability_count, unknown_ability_count = self._count_unknown_abilities(total_pokemon_count, opponent_active_pokemon_perception, opponent_team_perception)
        total_item_count, unknown_item_count = self._count_unknown_items(total_pokemon_count, opponent_active_pokemon_perception, opponent_team_perception)

        total_unknown_information_count = unknown_pokemon_count + unknown_move_count + unknown_ability_count + unknown_item_count
        total_possible_information_count = total_pokemon_count + total_move_count + total_ability_count + total_item_count

        return 5 * (total_unknown_information_count / total_possible_information_count)

    def _count_unknown_pokemon(self, opponent_active_pokemon: nd.NumDict, opponent_team: nd.NumDict) -> Tuple[int, int]:
        total_pokemon = 6
        active_count = 0 if is_empty(opponent_active_pokemon) else 1
        unknown_count = 6 - len(opponent_team) - active_count
        return total_pokemon, unknown_count

    def _count_unknown_moves(self, total_pokemon_count: int, opponent_active_pokemon: nd.NumDict, opponent_team: nd.NumDict) -> Tuple[int, int]:
        total_possible_move_count = total_pokemon_count * 4
        known_move_count = self._count_known_feature(opponent_active_pokemon, opponent_team, 'move')
        return total_possible_move_count, total_possible_move_count - known_move_count

    def _count_unknown_abilities(self, total_pokemon_count: int, opponent_active_pokemon: nd.NumDict, opponent_team: nd.NumDict) -> Tuple[int, int]:
        total_possible_ability_count = total_pokemon_count * 1
        known_ability_count = self._count_known_feature(opponent_active_pokemon, opponent_team, 'ability')
        return total_possible_ability_count, total_possible_ability_count - known_ability_count

    def _count_unknown_items(self, total_pokemon_count: int, opponent_active_pokemon: nd.NumDict, opponent_team: nd.NumDict) -> Tuple[int, int]:
        total_possible_item_count = total_pokemon_count * 1
        known_item_count = self._count_known_feature(opponent_active_pokemon, opponent_team, 'item')
        return total_possible_item_count, total_possible_item_count - known_item_count

    def _count_known_feature(self, opponent_active_pokemon: nd.NumDict, opponent_team: nd.NumDict, feature_name: str) -> int:
        count = len(get_only_value_from_numdict(opponent_active_pokemon).get_feature(feature_name)) if not is_empty(opponent_active_pokemon) else 0
        for pokemon_chunk in opponent_team:
            is_fainted = pokemon_chunk.get_feature_value('fainted')
            if not is_fainted:
                features = pokemon_chunk.get_feature(feature_name)
                count += len([feature for feature in features if feature.val is not None])

        return count


class ConstantDriveEvaluator(DriveEvaluator):
    def __init__(self, strength: float):
        super().__init__()
        self._strength = strength

    def evaluate(self, stimulus: GroupedStimulus) -> float:
        return self._strength


