from typing import Mapping, Any, Optional

import pyClarion as cl
from pyClarion import nd
from poke_engine.constants import SWITCH_STRING

from ..adapters.clarion_adapter import BattleConcept
from ..adapters.poke_engine_adapter import Simulator, BattleStimulusAdapter, OptionFilter
from .numdicts_ext import filter_chunks_by_group, get_only_value_from_numdict
from .motivation import GoalType, goal


class MentalSimulation(cl.Process):
    _serves = cl.ConstructType.flow_tt | cl.ConstructType.chunks

    def __init__(self, stimulus_source: cl.Symbol, goal_source: cl.Symbol, simulator: Simulator):
        super().__init__(expected=[stimulus_source, goal_source])
        self._goal_source = goal_source
        self._stimulus_source = stimulus_source
        self._simulator = simulator

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        grouped_stimulus = self._group_stimulus(inputs)
        current_goal = self._get_goal(inputs)

        simulation = BattleStimulusAdapter.from_stimulus(grouped_stimulus)
        action = self._generate_and_test_for_best_move(simulation, current_goal)
        return nd.NumDict({cl.chunk(action): 1.}, default=0.0) if action else nd.NumDict({}, default=0.0)

    def _group_stimulus(self, inputs: Mapping[Any, nd.NumDict]) -> Mapping[BattleConcept, nd.NumDict]:
        stimulus = inputs[cl.expand_address(self.client, self._stimulus_source)]
        return {concept: filter_chunks_by_group(concept, stimulus) for concept in BattleConcept}

    def _get_goal(self, inputs: Mapping[Any, nd.NumDict]) -> goal:
        goal_input = inputs[cl.expand_address(self.client, self._goal_source)]
        return get_only_value_from_numdict(goal_input)

    def _generate_and_test_for_best_move(self, simulation: BattleStimulusAdapter, current_goal: goal) -> Optional[str]:
        option_filter = self._get_option_filter(current_goal)
        action = self._simulator.pick_safest_move(simulation, option_filter)
        if not action:
            return None
        if not action.startswith(SWITCH_STRING):
            return action
        return action.split(SWITCH_STRING)[-1].strip()

    @staticmethod
    def _get_option_filter(current_goal: goal) -> OptionFilter:
        return OptionFilter.MOVES if current_goal.type == GoalType.MOVE else OptionFilter.SWITCHES
