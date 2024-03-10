from typing import Mapping, Any, List
from enum import Enum, auto

import pyClarion as cl
from pyClarion import nd


class Effort(str, Enum):
    TRY_HARD = 'try_hard', 0
    AUTOPILOT = 'autopilot', 1

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


EFFORT_INTERFACE = cl.ParamSet.Interface(
    name='effort',
    pmkrs=tuple(effort.value for effort in Effort)
)


class DecideEffort(cl.Process):
    _serves = cl.ConstructType.features

    def __init__(self, team_source: cl.Symbol, opponent_team_source: cl.Symbol):
        super().__init__(expected=[team_source, opponent_team_source])
        self._team_source = team_source
        self._opponent_team_source = opponent_team_source

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        effort = Effort.TRY_HARD.value if self._self_is_losing(inputs) else Effort.AUTOPILOT.value
        effort_feature = cl.feature((EFFORT_INTERFACE.name, effort))
        return nd.NumDict({effort_feature: 1.}, default=0.)

    def _self_is_losing(self, inputs: Mapping[Any, nd.NumDict]) -> bool:
        team: nd.NumDict = inputs[cl.expand_address(self.client, self._team_source)]
        opponent_team: nd.NumDict = inputs[cl.expand_address(self.client, self._opponent_team_source)]

        return len(team) < len(opponent_team)
