from types import MappingProxyType
from typing import *

import pyClarion as cl
from pyClarion import nd
from pyClarion.base.realizers import Pt


class GroupedChunk(cl.chunk):
    """A chunk symbol with extra metadata attaching it to a group"""
    __slots__ = ('_args', 'group')
    group: str

    def __init__(self, cid: Hashable, group: str) -> None:
        self.group = group
        super().__init__(cid)

    def __setattr__(self, key, value):
        object.__setattr__(self, key, value)

    def __repr__(self):
        cls_name = type(self).__name__
        return "{}({}|{})".format(cls_name, repr(self.cid), self.group)

    @staticmethod
    def from_chunk(other: cl.chunk, group: str):
        return GroupedChunk(other.cid, group)


class NamedStimuli(cl.Process):
    """
    Because a single stimulus buffer can only communicate chunks/features without any context, it's impossible to
    explicitly model the game state (e.g., communicate which is the active Pokemon vs benched Pokemon). This class is an
    adapter to name certain stimuli so that different parts of the game state can be explicitly communicated.
    """

    _serves = cl.ConstructType.buffer

    def __init__(self, named_stimuli: List[str]) -> None:
        super().__init__()
        self.stimuli: Dict[str, cl.Stimulus] = {name: cl.Stimulus() for name in named_stimuli}

    def input(self, named_stimuli: Dict[str, nd.NumDict]) -> None:
        for name, numdict in named_stimuli.items():
            if name not in self.stimuli:
                raise ValueError(f'There is no named stimulus called {name}')

            grouped_chunks = self._to_grouped_chunks(name, numdict)
            self.stimuli[name].input(grouped_chunks)

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        result = nd.MutableNumDict(default=0.0)
        for stimulus in self.stimuli.values():
            stimulus_output = stimulus.call(nd.NumDict())
            for symbol, weight in stimulus_output.items():
                result[symbol] = weight

        return result

    @staticmethod
    def _to_grouped_chunks(name: str, numdict: nd.NumDict) -> nd.NumDict:
        result = nd.MutableNumDict(default=0.0)
        for chunk_symbol, weight in numdict.items():
            new_symbol = GroupedChunk.from_chunk(chunk_symbol, name)
            result[new_symbol] = weight

        return result


class AttentionFilter(cl.Wrapped[Pt]):
    _serves = cl.ConstructType.buffer

    def __init__(self, base: Pt, attend_to: List[str]) -> None:
        super().__init__(base=base)
        self.attend_to = attend_to

    def preprocess(self, inputs: Mapping[Any, nd.NumDict]) -> Mapping[Any, nd.NumDict]:
        attended_inputs = {}
        for source, emission in inputs.items():
            attended_emissions = self._filter_to_attended(emission)
            attended_inputs[source] = attended_emissions if len(attended_emissions) > 0 else nd.NumDict(default=0.0)

        return MappingProxyType(attended_inputs)

    def _filter_to_attended(self, original_emission: nd.NumDict) -> nd.NumDict:
        attended = nd.MutableNumDict(default=0.0)
        for symbol, weight in original_emission.items():
            if not isinstance(symbol, GroupedChunk):
                continue
            if symbol.group in self.attend_to:
                attended[symbol] = weight

        return attended


class MentalSimulation(cl.Process):
    _serves = cl.ConstructType.chunk

    pass
