from typing import Mapping, Any
from unittest.mock import Mock

import pytest
import pyClarion as cl
from pyClarion import nd

from battlemaster.clarion_ext.attention import NamedStimuli, AttentionFilter, GroupedChunk, GroupedChunkInstance, GroupedStimulusInput


class TestGroupedChunk:
    def test_constructing_from_chunk(self):
        chunk = cl.chunk('foo')
        grouped_chunk = GroupedChunk.from_chunk(chunk, 'some group')

        assert grouped_chunk.cid == chunk.cid
        assert grouped_chunk.group == 'some group'

    def test_equality_with_normal_chunk(self):
        chunk = cl.chunk('foo')
        grouped_chunk = GroupedChunk.from_chunk(chunk, 'some group')

        assert chunk == grouped_chunk


class TestGroupedChunkInstance:
    def test_constructing(self):
        chunk = cl.chunk('foo')
        features = [cl.feature('feature')]
        chunk = GroupedChunkInstance.from_chunk(chunk, 'group', features)

        assert chunk.cid == chunk.cid
        assert chunk.group == 'group'
        assert chunk.features == features

    def test_equality_with_normal_chunk(self):
        chunk = cl.chunk('foo')
        grouped_chunk = GroupedChunkInstance.from_chunk(chunk, 'some group', [])

        assert chunk == grouped_chunk


class TestGroupedStimulusInput:
    def test_add_chunk(self):
        input = GroupedStimulusInput(['foo'])
        input.add_chunk_to_group(cl.chunk('bar'), 'foo')

        assert cl.chunk('bar') in input._inputs['foo']
        assert isinstance(self._get_first_chunk(input), GroupedChunk)

    def test_add_chunk_nonexistant_group(self):
        input = GroupedStimulusInput(['foo'])

        with pytest.raises(ValueError):
            input.add_chunk_to_group(cl.chunk('bar'), 'does not exist')

    def test_add_chunk_instance(self):
        input = GroupedStimulusInput(['foo'])
        input.add_chunk_instance_to_group(cl.chunk('bar'), 'foo', [cl.feature('baz')])

        assert cl.chunk('bar') in input._inputs['foo']
        assert isinstance(self._get_first_chunk(input), GroupedChunkInstance)

    def test_add_chunk_instance_nonexistant_group(self):
        input = GroupedStimulusInput(['foo'])

        with pytest.raises(ValueError):
            input.add_chunk_instance_to_group(cl.chunk('bar'), 'does not exist', [])

    @staticmethod
    def _get_first_chunk(input: GroupedStimulusInput) -> cl.chunk:
        return next(iter(input._inputs['foo'].keys()))


class TestNamedStimuli:
    def test_creates_stimulus_per_name(self):
        named_stimuli = ['foo', 'bar', 'baz']
        result = NamedStimuli(named_stimuli)

        for name in named_stimuli:
            assert name in result._stimuli
            assert isinstance(result._stimuli[name], cl.Stimulus)

    def test_input_unknown_name(self):
        stimuli = NamedStimuli(['foo'])

        with pytest.raises(ValueError):
            stimuli.input({'bar': nd.NumDict({'chunk': 1.0})})

    def test_input_adds_to_individual_stimuli(self):
        named_stimuli = ['foo', 'bar']
        stimuli = NamedStimuli(named_stimuli)
        input = {
            'foo': nd.NumDict({cl.chunk('foo'): 1.}),
            'bar': nd.NumDict({cl.chunk('bar'): 1.})
        }

        stimuli.input(input)

        for name in named_stimuli:
            expected_chunk = cl.chunk(name)
            stimulus = stimuli._stimuli[name].stimulus
            assert expected_chunk in stimulus
            assert stimulus[expected_chunk] == input[name][expected_chunk]

    def test_input_converts_to_groupchunk(self):
        stimuli = NamedStimuli(['foo'])
        input = {
            'foo': nd.NumDict({cl.chunk('bar'): 1.})
        }

        stimuli.input(input)

        keys = stimuli._stimuli['foo'].stimulus.keys()
        groupchunk = next(iter(keys))

        assert isinstance(groupchunk, GroupedChunk)
        assert groupchunk.group == 'foo'
        assert groupchunk.cid == 'bar'

    def test_call_flattens_stimuli(self):
        named_stimuli = ['foo', 'bar', 'baz']
        stimuli = NamedStimuli(named_stimuli)
        input = {
            'foo': nd.NumDict({cl.chunk('foo'): 1.}),
            'bar': nd.NumDict({cl.chunk('bar'): 2.}),
            'baz': nd.NumDict({cl.chunk('baz'): 3.}),
        }

        stimuli.input(input)
        result = stimuli.call({})

        for name in named_stimuli:
            expected_chunk = cl.chunk(name)
            assert expected_chunk in result
            assert result[expected_chunk] == input[name][expected_chunk]


class TestAttentionFilter:
    @pytest.fixture
    def inputs(self) -> Mapping[Any, nd.NumDict]:
        return {
            cl.buffer('in1'): nd.NumDict({GroupedChunk('fire', 'typing'): 1., GroupedChunk('water', 'typing'): 1.}),
            cl.buffer('in2'): nd.NumDict({GroupedChunk('water', 'typing'): 1., GroupedChunk('foo', 'nickname'): 1.}),
            cl.buffer('in3'): nd.NumDict({GroupedChunk('bar', 'nickname'): 1.}),
        }

    @pytest.fixture
    def base_process(self) -> cl.Process:
        base = Mock(spec=cl.Process)
        base._expected = ()
        return base

    def test_preprocess_keeps_all_sources(self, base_process: cl.Process, inputs):
        filter = AttentionFilter(base_process, attend_to=[])
        result = filter.preprocess(inputs)

        for source in inputs.keys():
            assert source in result

    def test_preprocess_only_keeps_attended_symbols(self, base_process: cl.Process, inputs):
        filter = AttentionFilter(base_process, attend_to=['typing'])
        result = filter.preprocess(inputs)
        filtered_emissions = (emission for source, emission in result.items())

        total_attended_to_symbols = 0

        for emission in filtered_emissions:
            for symbol in emission.keys():
                total_attended_to_symbols += 1
                assert symbol.group == 'typing'

        assert total_attended_to_symbols == 3
