from typing import Tuple

import pytest
from pytest import MonkeyPatch
import pyClarion as cl
from pyClarion import nd
from poke_env.data import GenData

from battlemaster import mind
from battlemaster.clarion_ext.positioning import DecideEffort, EFFORT_INTERFACE


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
def working_memory(agent: cl.Structure) -> cl.Construct:
    return agent[cl.buffer("wm")]


@pytest.fixture
def acs_terminus(agent: cl.Structure) -> cl.Construct:
    return agent[cl.subsystem('acs')][cl.terminus("choose_move")]


@pytest.fixture
def mcs_effort_gate(agent: cl.Structure) -> cl.Construct:
    return agent[cl.buffer('mcs_effort_gate')]


@pytest.fixture
def given_effort(request, monkeypatch: MonkeyPatch):
    effort = request.param.value
    effort_feature = cl.feature((EFFORT_INTERFACE.name, effort))
    monkeypatch.setattr(DecideEffort, 'call', lambda _self, inputs: nd.NumDict({effort_feature: 1.}, default=0.))


@pytest.fixture
def pokemon_database() -> GenData:
    try:
        return GenData(9)
    except ValueError as e:
        return GenData._gen_data_per_gen[9]
