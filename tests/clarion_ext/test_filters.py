from typing import List

import pyClarion as cl
from pyClarion import nd
import pytest

from battlemaster.clarion_ext.filters import SwitchIfEmpty


class TestSwitchIfEmpty:
    @pytest.fixture
    def primary_sources(self) -> List[cl.Symbol]:
        return [cl.chunks('primary1'),  cl.chunks('primary2')]

    @pytest.fixture
    def alternative_sources(self) -> List[cl.Symbol]:
        return [cl.chunks('alt1'), cl.chunks('alt2')]

    @pytest.fixture
    def process(self, primary_sources, alternative_sources):
        return SwitchIfEmpty(primary_sources, alternative_sources)

    def test_primary_resource_not_empty(self, process: SwitchIfEmpty):
        inputs = {
            cl.chunks('primary1'): nd.NumDict({cl.chunk('foo'): 1.}, default=0.),
            cl.chunks('primary2'): nd.NumDict({cl.chunk('bar'): 1.}, default=0.),
            cl.chunks('alt1'): nd.NumDict({cl.chunk('faz'): 1.}, default=0.),
            cl.chunks('alt2'): nd.NumDict({cl.chunk('baz'): 1.}, default=0.),
        }

        result = process.call(inputs)

        assert cl.chunk('foo') in result
        assert cl.chunk('bar') in result
        assert not cl.chunk('faz') in result
        assert not cl.chunk('baz') in result

    def test_primary_resource_empty(self, process: SwitchIfEmpty):
        inputs = {
            cl.chunks('primary1'): nd.NumDict({}, default=0.),
            cl.chunks('primary2'): nd.NumDict({}, default=0.),
            cl.chunks('alt1'): nd.NumDict({cl.chunk('faz'): 1.}, default=0.),
            cl.chunks('alt2'): nd.NumDict({cl.chunk('baz'): 1.}, default=0.),
        }

        result = process.call(inputs)

        assert not cl.chunk('foo') in result
        assert not cl.chunk('bar') in result
        assert cl.chunk('faz') in result
        assert cl.chunk('baz') in result
