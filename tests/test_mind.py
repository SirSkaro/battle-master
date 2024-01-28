import pyClarion as cl
from battlemaster import mind


def test_nacs():
    agent, stimulus = mind.create_agent()
    agent_nacs_terminus = agent[cl.subsystem('nacs')][cl.terminus('main')]
    stimulus.process.input({cl.chunk('normal'): 1.})
    agent.step()

    nacs_output = agent_nacs_terminus.output
    len(nacs_output)

    type_chunk, weight = next(iter(nacs_output.items()))

    assert 'fighting' == type_chunk.cid

