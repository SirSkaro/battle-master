from types import MappingProxyType
from typing import Hashable, List, Dict, Mapping, Any, Optional, Union

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
        return "{}({}|{})".format(cls_name, self.cid, self.group)

    @staticmethod
    def from_chunk(other: cl.chunk, group: str):
        return GroupedChunk(other.cid, group)


class GroupedChunkInstance(GroupedChunk):
    """A chunk symbol with features associated under it"""
    __slots__ = ('_args', 'group', 'features')
    features: List[cl.feature]

    def __init__(self, cid: Hashable, group: str, features: List[cl.feature]) -> None:
        self.features = features
        super().__init__(cid, group)

    def __setattr__(self, key, value):
        object.__setattr__(self, key, value)

    def __repr__(self):
        cls_name = type(self).__name__
        return "{}({}|{}){}".format(cls_name, self.cid, self.group, self.features)

    @staticmethod
    def from_chunk(other: cl.chunk, group: str, features: List[cl.feature]):
        return GroupedChunkInstance(other.cid, group, features)

    def get_feature(self, name: str) -> List[cl.feature]:
        return [feature for feature in self.features if feature.tag == name]

    def get_feature_value(self, name: str) -> Union[Optional[str], List[str]]:
        features = self.get_feature(name)
        if len(features) == 0:
            return None
        elif len(features) == 1:
            return features[0].val
        return [feature.val for feature in features]


class GroupedStimulusInput:
    def __init__(self, groups: List[str]):
        self.groups = groups
        self._inputs = {group: nd.MutableNumDict(default=0.) for group in groups}

    def add_chunk_to_group(self, chunk: cl.chunk, group: str, weight: float = 1.):
        self._assert_group_registered(group)
        self._add_chunk(chunk, group, weight)

    def add_chunks_to_group(self, chunks: List[cl.chunk], group: str, weight: float = 1.):
        self._assert_group_registered(group)

        for chunk in chunks:
            self._add_chunk(chunk, group, weight)

    def add_chunk_instance_to_group(self, chunk: cl.chunk, group: str, features: List[cl.feature], weight: float = 1.):
        self._assert_group_registered(group)

        chunk_instance = GroupedChunkInstance.from_chunk(chunk, group, features)
        self._inputs[group][chunk_instance] = weight

    def to_stimulus(self, default=0.) -> Dict[str, nd.NumDict]:
        return {group: nd.NumDict(d, default=default) for group, d in self._inputs.items()}

    def _assert_group_registered(self, group: str):
        if group not in self.groups:
            raise ValueError(f'{group} is not in the list of supported groups: {self.groups}')

    def _add_chunk(self, chunk: cl.chunk, group: str, weight: float):
        groupchunk = GroupedChunk.from_chunk(chunk, group)
        self._inputs[group][groupchunk] = weight


class NamedStimuli(cl.Process):
    """
    Because a single stimulus buffer can only communicate chunks/features without any context, it's impossible to
    explicitly model the game state (e.g., communicate which is the active Pokemon vs benched Pokemon). This class is an
    adapters to name certain stimuli so that different parts of the game state can be explicitly communicated.
    """

    _serves = cl.ConstructType.buffer
    _stimuli: Dict[str, cl.Stimulus]

    def __init__(self) -> None:
        super().__init__()

    def input(self, named_stimuli: GroupedStimulusInput) -> None:
        self._stimuli = {name: cl.Stimulus() for name in named_stimuli.groups}

        for name, stimulus in named_stimuli.to_stimulus().items():
            self._stimuli[name].input(stimulus)

    def call(self, inputs: Mapping[Any, nd.NumDict]) -> nd.NumDict:
        result = nd.MutableNumDict(default=0.0)
        for stimulus in self._stimuli.values():
            stimulus_output = stimulus.call(nd.NumDict())
            for symbol, weight in stimulus_output.items():
                result[symbol] = weight

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

