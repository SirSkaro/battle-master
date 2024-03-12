from enum import Enum

import pyClarion as cl


class WmSource(str, Enum):
    CANDIDATE_MOVES = 'candidate_moves'

    def __str__(self) -> str:
        return self.value


WM_INTERFACE = cl.RegisterArray.Interface(
    name="wm",
    slots=1,
    vops=tuple(source.value for source in WmSource)
)


def format_contents(wm: cl.Construct) -> str:
    return ' | '.join([str(cell.store) for cell in wm.process.cells])

