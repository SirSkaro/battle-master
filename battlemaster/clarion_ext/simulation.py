from typing import Mapping, Any, Tuple

import pyClarion as cl
from pyClarion import nd

from ..adapters.clarion_adapter import BattleConcept
from ..adapters.poke_engine_adapter import Simulator, BattleStimulusAdapter
from .numdicts_ext import filter_chunks_by_group


class MentalSimulation(cl.Process):
    _serves = cl.ConstructType.flow_tt | cl.ConstructType.chunks

    def __init__(self, stimulus_source: cl.Symbol, simulator: Simulator):
        super().__init__(expected=[stimulus_source])
        self._simulator = simulator
        self._stimulus_source = stimulus_source

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        stimulus = inputs[cl.expand_address(self.client, self._stimulus_source)]
        grouped_stimulus = self._group_stimulus(stimulus)
        simulation = BattleStimulusAdapter.from_stimulus(grouped_stimulus)
        action = self._simulator.pick_safest_move(simulation)
        return nd.NumDict({cl.chunk(action): 1.}, default=0.0)

    def _group_stimulus(self, stimulus: nd.NumDict) -> Mapping[BattleConcept, nd.NumDict]:
        return {concept: filter_chunks_by_group(concept, stimulus) for concept in BattleConcept}
