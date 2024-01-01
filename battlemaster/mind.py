import pyClarion as cl


def create_agent():
    with cl.Structure("btlMaster") as agent:
        with cl.Structure("nacs"):
            cl.Module('physics_store', cl.Store(), ['params'])
            params = cl.Module('params', cl.Repeat(), ['params'])

    params.output = cl.NumDict({
        cl.feature("base_power"): 0
    })

    with open('data/physics.ccml') as f:
        cl.load(f, agent)

    return agent

