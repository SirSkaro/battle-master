import pyClarion as cl
from pyClarion import chunk, rule, feature, buffer, subsystem, Construct, chunks, features


def create_agent():
    chunk_database = cl.Chunks()
    rule_database = cl.Rules()

    chunk_database.define(
        chunk('firepunch'),
        feature('base_power', 75),
        feature('type', 'fire')
    )
    chunk_database.define(
        chunk('icepunch'),
        feature('base_power', 75),
        feature('type', 'ice')
    )

    rule_database.define(rule(1), chunk("icepunch"), chunk("firepunch"))

    with cl.Structure(name=cl.agent('btlMaster')) as btlMaster:
        stimulus = Construct(name=buffer("stimulus"), process=cl.Stimulus())
        nacs = cl.Structure(name=subsystem("nacs"),
            assets=cl.Assets(
                cdb=chunk_database,
                rdb=rule_database
            )
        )

        with nacs:
            Construct(name=cl.chunks("in"), process=cl.MaxNodes(sources=[buffer("stimulus")]))
            Construct(name=cl.flow_tb("main"), process=cl.TopDown(source=chunks("in"), chunks=nacs.assets.cdb))
            Construct(name=features("main"), process=cl.MaxNodes(sources=[cl.flow_tb("main")]))
            Construct(name=cl.flow_tt("associations"), process=cl.AssociativeRules(source=chunks("in"), rules=nacs.assets.rdb))
            Construct(name=cl.flow_bt("main"), process=cl.BottomUp(source=features("main"), chunks=nacs.assets.cdb))
            Construct(name=chunks("out"), process=cl.MaxNodes(sources=[chunks("in"), cl.flow_bt("main"), cl.flow_tt("associations")]))
            Construct(name=cl.terminus("main"),process=cl.Filtered(base=cl.BoltzmannSelector(source=chunks("out"), temperature=.1), controller=buffer("stimulus")))

    return btlMaster, stimulus

