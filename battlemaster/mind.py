import pyClarion as cl
from pyClarion import chunk, rule, feature, buffer, subsystem, Construct, chunks, features

def _define_type_chunks(chunk_database: cl.Chunks, rule_database: cl.Rules):
    types = ['normal', 'fighting', 'flying', 'poison', 'ground', 'rock', 'bug', 'ghost', 'steel', 'fire', 'water',
             'grass', 'electric', 'psychic', 'ice', 'dragon', 'dark', 'fairy']

    # attacking type (row) x defending type (column)
    type_chart = [
        #normal fighting    flying  poison  ground  rock    bug     ghost   steel   fire    water   grass   electric    psychic ice     dragon  dark    fairy
        [1.0,   1.0,        1.0,    1.0,    1.0,    0.5,    1.0,    0.0,    0.5,    1.0,    1.0,    1.0,    1.0,        1.0,    1.0,    1.0,    1.0,    1.0],  # normal
        [2.0,   1.0,        0.5,    0.5,    1.0,    2.0,    0.5,    0.0,    2.0,    1.0,    1.0,    1.0,    1.0,        0.5,    2.0,    1.0,    2.0,    0.5],  # fighting
        [1.0,   2.0,        1.0,    1.0,    1.0,    0.5,    2.0,    1.0,    0.5,    1.0,    1.0,    1.0,    0.5,        1.0,    1.0,    1.0,    1.0,    1.0],  # flying
        [1.0,   1.0,        1.0,    0.5,    0.5,    0.5,    1.0,    1.0,    0.0,    1.0,    1.0,    2.0,    0.5,        1.0,    1.0,    1.0,    1.0,    2.0],  # poison
        [1.0,   1.0,        0.0,    2.0,    1.0,    2.0,    1.0,    1.0,    2.0,    2.0,    1.0,    0.5,    2.0,        1.0,    1.0,    1.0,    1.0,    1.0],  # ground
        [1.0,   0.5,        2.0,    1.0,    0.5,    1.0,    2.0,    1.0,    0.5,    2.0,    1.0,    1.0,    1.0,        1.0,    2.0,    1.0,    1.0,    1.0],  # rock
        [1.0,   0.5,        0.5,    0.5,    1.0,    1.0,    1.0,    0.5,    0.5,    0.5,    1.0,    2.0,    1.0,        2.0,    1.0,    1.0,    2.0,    0.5],  # bug
        [0.0,   1.0,        1.0,    1.0,    1.0,    1.0,    1.0,    2.0,    1.0,    1.0,    1.0,    1.0,    1.0,        2.0,    1.0,    1.0,    0.5,    1.0],  # ghost
        [1.0,   1.0,        1.0,    1.0,    1.0,    2.0,    1.0,    1.0,    0.5,    0.5,    0.5,    1.0,    0.5,        1.0,    2.0,    1.0,    1.0,    2.0],  # steel
        [1.0,   1.0,        1.0,    1.0,    1.0,    0.5,    2.0,    1.0,    2.0,    0.5,    0.5,    2.0,    1.0,        1.0,    2.0,    0.5,    1.0,    1.0],  # fire
        [1.0,   1.0,        1.0,    1.0,    2.0,    2.0,    1.0,    1.0,    1.0,    2.0,    0.5,    0.5,    1.0,        1.0,    1.0,    0.5,    1.0,    1.0],  # water
        [1.0,   1.0,        0.5,    1.0,    2.0,    2.0,    0.5,    1.0,    0.5,    0.5,    2.0,    0.5,    1.0,        1.0,    1.0,    0.5,    1.0,    1.0],  # grass
        [1.0,   1.0,        2.0,    1.0,    0.0,    1.0,    1.0,    1.0,    1.0,    1.0,    2.0,    0.5,    0.5,        1.0,    1.0,    0.5,    1.0,    1.0],  # electric
        [1.0,   2.0,        1.0,    2.0,    0.0,    1.0,    1.0,    1.0,    0.5,    1.0,    1.0,    1.0,    1.0,        0.5,    1.0,    1.0,    0.0,    1.0],  # psychic
        [1.0,   1.0,        2.0,    1.0,    2.0,    1.0,    1.0,    1.0,    0.5,    0.5,    0.5,    2.0,    1.0,        1.0,    0.5,    2.0,    1.0,    1.0],  # ice
        [1.0,   1.0,        1.0,    1.0,    1.0,    1.0,    1.0,    1.0,    0.5,    1.0,    1.0,    1.0,    1.0,        1.0,    1.0,    2.0,    1.0,    0.0],  # dragon
        [1.0,   0.5,        1.0,    1.0,    1.0,    1.0,    1.0,    2.0,    1.0,    1.0,    1.0,    1.0,    1.0,        2.0,    1.0,    2.0,    0.5,    0.5],  # dark
        [1.0,   2.0,        1.0,    0.5,    1.0,    1.0,    1.0,    1.0,    0.5,    0.5,    1.0,    1.0,    1.0,        2.0,    1.0,    2.0,    2.0,    1.0],  # fairy
    ]

    for type in types:
        chunk_database.define(chunk(type), feature(type), feature('type'))

    for attacker_index, attacker_type in enumerate(types):
        attack_conclusion = chunk(attacker_type)
        attack_rule = rule(f'{attacker_type}-super-effective-against')
        attack_conditions = []
        efficacies = type_chart[attacker_index]
        for efficacy_index, efficacy in enumerate(efficacies):
            if efficacy == 2.0:
                weak_type = types[efficacy_index]
                attack_conditions.append(chunk(weak_type))

        rule_database.define(attack_rule, attack_conclusion, *attack_conditions)


def create_agent():
    chunk_database = cl.Chunks()
    rule_database = cl.Rules()

    _define_type_chunks(chunk_database, rule_database)

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

