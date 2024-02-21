from typing import Tuple

import pytest
import pyClarion as cl
from poke_env.data import GenData

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


@pytest.fixture
def acs_terminus(agent: cl.Structure) -> cl.Construct:
    return agent[cl.subsystem('acs')][cl.terminus("choose_move")]


@pytest.fixture
def pokemon_database() -> GenData:
    try:
        return GenData(9)
    except ValueError as e:
        return GenData._gen_data_per_gen[9]
