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

    def test_membership_with_normal_chunk(self):
        chunk = cl.chunk('foo')
        grouped_chunk = GroupedChunk.from_chunk(chunk, 'some group')

        assert grouped_chunk in {chunk: 1.}
        assert chunk in {grouped_chunk: 1.}


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


class TestNamedStimuliComponentTest:
    def test_input_adds_to_individual_stimuli(self):
        stimuli = NamedStimuli()
        named_stimuli = GroupedStimulusInput(['foo', 'bar'])
        named_stimuli.add_chunk_to_group(cl.chunk('foo'), 'foo')
        named_stimuli.add_chunk_to_group(cl.chunk('bar'), 'bar')

        stimuli.input(named_stimuli)

        for name in named_stimuli.groups:
            expected_chunk = cl.chunk(name)
            stimulus = stimuli._stimuli[name].stimulus
            assert expected_chunk in stimulus

    def test_call_flattens_stimuli(self):
        named_stimuli = ['foo', 'bar', 'baz']
        stimuli = NamedStimuli()
        named_stimuli = GroupedStimulusInput(named_stimuli)
        named_stimuli.add_chunk_to_group(cl.chunk('foo'), 'foo', 1.)
        named_stimuli.add_chunk_to_group(cl.chunk('bar'), 'bar', 2.)
        named_stimuli.add_chunk_to_group(cl.chunk('baz'), 'baz', 3.)

        stimuli.input(named_stimuli)
        result = stimuli.call({})
        input = named_stimuli.to_stimulus()

        for name in named_stimuli.groups:
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
