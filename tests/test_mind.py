from typing import Tuple

import pytest
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


@pytest.mark.parametrize("defending_types, expected_super_effective_types", [
    (["normal"], ["fighting"]),
    (["ghost"], ["ghost", "dark"]),
    (["steel", "flying"], ["electric", "rock", "ice", "fighting", "fire", "ground"])
])
def test_super_effective_association(defending_types, expected_super_effective_types, agent: cl.Structure, stimulus: cl.Construct, nacs_terminus: cl.Construct):
    presented_types = {cl.chunk(defending_type): 1. for defending_type in defending_types}

    stimulus.process.input(presented_types)
    agent.step()
    nacs_output = nacs_terminus.output

    super_effective_types = [type_chunk.cid for type_chunk, weight in iter(nacs_output.items())]
    assert sorted(expected_super_effective_types) == sorted(super_effective_types)



