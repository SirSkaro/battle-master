from typing import Mapping, Any, List

import pyClarion as cl
from pyClarion import nd


class LogicalPosition(cl.Process):
    _serves = cl.ConstructType.features

    def __init__(self, team_source: cl.Symbol, opponent_team_source: cl.Symbol):
        super().__init__(expected=[team_source, opponent_team_source])
        self._team_source = team_source
        self._opponent_team_source = opponent_team_source

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        effort_feature = cl.feature('try_hard') if self._self_is_losing(inputs) else cl.feature('autopilot')
        return nd.NumDict({effort_feature: 1.}, default=0.)

    def _self_is_losing(self, inputs: Mapping[Any, nd.NumDict]) -> bool:
        team: nd.NumDict = inputs[cl.expand_address(self.client, self._team_source)]
        opponent_team: nd.NumDict = inputs[cl.expand_address(self.client, self._opponent_team_source)]

        return len(team) < len(opponent_team)
