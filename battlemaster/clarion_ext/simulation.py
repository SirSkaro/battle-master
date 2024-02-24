from typing import Mapping, Any, List

import pyClarion as cl
from pyClarion import nd

from ..adapters.poke_engine_adapter import Simulator, Simulation, BattleStimulusAdapter


class EffectiveMoves(cl.Process):
    _serves = cl.ConstructType.flow_tt | cl.ConstructType.chunks

    def __init__(self, stimulus_source: cl.Symbol, simulator: Simulator):
        super().__init__(expected=[stimulus_source])
        self.simulator = simulator

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        stimulus = self.extract_inputs(inputs)
        simulation = BattleStimulusAdapter.from_stimulus(stimulus)
        self.simulator.pick_safest_move(simulation)
        pass





