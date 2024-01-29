import pytest
from typing import Tuple

import pyClarion as cl

from battlemaster import mind


@pytest.fixture
def agent_stimulus() -> Tuple[cl.Structure, cl.Construct]:
    return mind.create_agent()


@pytest.fixture
def agent(agent_stimulus: Tuple[cl.Structure, cl.Construct]) -> cl.Structure:
    return agent_stimulus[0]


@pytest.fixture
def stimulus(agent_stimulus: Tuple[cl.Structure, cl.Construct]) -> cl.Construct:
    return agent_stimulus[1]


@pytest.fixture
def nacs(agent: cl.Structure) -> cl.Structure:
    return agent[cl.subsystem('nacs')]


@pytest.fixture
def nacs_terminus(nacs: cl.Structure) -> cl.Construct:
    return nacs[cl.terminus("main")]


def test_nacs(agent: cl.Structure, stimulus: cl.Construct, nacs_terminus: cl.Construct):
    stimulus.process.input({cl.chunk('normal'): 1.})
    agent.step()

    nacs_output = nacs_terminus.output
    type_chunk, weight = next(iter(nacs_output.items()))

    assert 'fighting' == type_chunk.cid

