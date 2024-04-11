from enum import Enum

import pyClarion as cl


class NacsWmSource(str, Enum):
    CANDIDATE_ACTIONS = 'candidate_actions'

    def __str__(self) -> str:
        return self.value


NACS_OUT_WM_INTERFACE = cl.RegisterArray.Interface(
    name="wm",
    slots=1,
    vops=tuple(source.value for source in NacsWmSource)
)


class MsWmSource(str, Enum):
    DRIVE_ACTIVATIONS = 'drive_activations'
    GOAL_ACTIVATIONS = 'goal_activations'

    def __str__(self) -> str:
        return self.value


MS_OUT_WM_INTERFACE = cl.RegisterArray.Interface(
    name="wm",
    slots=2,
    vops=tuple(source.value for source in MsWmSource)
)

class McsWmSource(str, Enum):
    GOAL = 'goal'

    def __str__(self) -> str:
        return self.value


MCS_OUT_WM_INTERFACE = cl.RegisterArray.Interface(
    name="wm",
    slots=1,
    vops=tuple(source.value for source in McsWmSource)
)

def format_contents(wm: cl.Construct) -> str:
    return ' | '.join([str(cell.store) for cell in wm.process.cells])

