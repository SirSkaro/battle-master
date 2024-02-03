from typing import Tuple
import re

import pyClarion as cl
from pyClarion import chunk, rule, feature, buffer, subsystem, chunks, features
from poke_env import gen_data

pokemon_database = gen_data.GenData(9)


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
        chunk_database.define(chunk(type), feature('type', type))

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


_camel_case_pattern = re.compile(r'(?<!^)(?=[A-Z])')
def _to_snake_case(camel_case: str) -> str:
    camel_case = camel_case.replace('-', '')
    camel_case = _camel_case_pattern.sub('_', camel_case).lower()
    return camel_case.replace(' ', '_')


def _define_move_chunks(chunk_database: cl.Chunks):
    all_moves = pokemon_database.moves
    for name, move_data in all_moves.items():
        if 'isZ' in move_data:
            continue
        chunk_database.define(chunk(name),
                              feature('move', name),
                              feature('accuracy', 100 if move_data['accuracy'] == True else move_data['accuracy']),
                              feature('base_power', move_data['basePower']),
                              feature('category', _to_snake_case(move_data['category'])),
                              feature('priority', move_data['priority']),
                              feature('type', _to_snake_case(move_data['type'])))


def _define_move_command_interface() -> cl.Interface:
    command_features = tuple([cl.feature('move', name) for name, data in pokemon_database.moves.items() if 'isZ' not in data])
    return cl.Interface(cmds=command_features)


def _define_pokemon_chunks(chunk_database: cl.Chunks):
    all_pokemon = pokemon_database.pokedex
    for name, pokemon in all_pokemon.items():
        typing = pokemon['types']
        stats = pokemon['baseStats']
        chunk_database.define(chunk(name),
                              feature('pokemon'),
                              feature('type', typing[0].lower()),
                              feature('type', typing[1].lower() if len(typing) > 1 else None),
                              feature('hp', stats['hp']),
                              feature('attack', stats['atk']),
                              feature('defense', stats['def']),
                              feature('special_attack', stats['spa']),
                              feature('special_defense', stats['spd']),
                              feature('speed', stats['spe']),
                              feature('weight', pokemon['weightkg']))


def create_agent() -> Tuple[cl.Structure, cl.Construct]:
    type_chunks = cl.Chunks()
    move_chunks = cl.Chunks()
    pokemon_chunks = cl.Chunks()
    rule_database = cl.Rules()

    _define_type_chunks(type_chunks, rule_database)
    _define_move_chunks(move_chunks)
    _define_pokemon_chunks(pokemon_chunks)

    wm_interface = cl.RegisterArray.Interface(name="wm", slots=1, vops=("choose_move",))
    choose_move_interface = _define_move_command_interface()

    btlMaster = cl.Structure(name=cl.agent('btlMaster'),
                             assets=cl.Assets(
                                working_memory=wm_interface,
                                choose_move_interface=choose_move_interface)
                             )

    with btlMaster:
        stimulus = cl.Construct(name=buffer("stimulus"), process=cl.Stimulus())
        acs_ctrl = cl.Construct(name=buffer("acs_ctrl"), process=cl.Stimulus()) #TODO expose WM and see if can manually mess around with it

        cl.Construct(name=buffer("wm"),
                     process=cl.RegisterArray(
                         controller=(subsystem("acs"), cl.terminus("wm")),
                         sources=((subsystem("nacs"), cl.terminus("main")),),
                         interface=wm_interface)
                     )

        acs = cl.Structure(name=subsystem("acs"))

        nacs = cl.Structure(name=subsystem("nacs"),
            assets=cl.Assets(
                type_chunks=type_chunks,
                move_chunks=move_chunks,
                pokemon_chunks=pokemon_chunks,
                rdb=rule_database
            )
        )

        with nacs:
            cl.Construct(name=cl.chunks("in"), process=cl.MaxNodes(sources=[buffer("stimulus")]))
            cl.Construct(name=cl.flow_tt("associations"), process=cl.AssociativeRules(source=chunks("in"), rules=nacs.assets.rdb))
            cl.Construct(name=chunks("out"), process=cl.MaxNodes(sources=[cl.flow_tt("associations")]))
            cl.Construct(name=cl.terminus("main"), process=cl.ThresholdSelector(source=chunks("out"), threshold=0.1))

        with acs:
            cl.Construct(name=cl.flow_in('in'), process=cl.TopDown(source=buffer("acs_ctrl"), chunks=type_chunks))
            cl.Construct(name=features('main'), process=cl.MaxNodes(sources=[cl.flow_in('in')]))
            cl.Construct(name=cl.flow_bt('to_move'), process=cl.BottomUp(source=features('main'), chunks=move_chunks))
            cl.Construct(name=cl.flow_tb('to_features'), process=cl.TopDown(source=cl.flow_bt('to_move'), chunks=move_chunks))
            cl.Construct(name=features('move_features'), process=cl.MaxNodes(sources=[cl.flow_tb('to_features')]))
            #cl.Construct(name=cl.flow_in("wm"), process=cl.TopDown(source=buffer("wm"), chunks=move_chunks))
            #cl.Construct(name=features('main'), process=cl.MaxNodes(sources=[cl.flow_in('wm')]))
            cl.Construct(name=cl.terminus('wm'), process=cl.ActionSelector(source=features("main"), temperature=0.01, interface=btlMaster.assets.working_memory))
            cl.Construct(name=cl.terminus("choose_move"), process=cl.ActionSelector(source=cl.features("move_features"), temperature=0.01, interface=btlMaster.assets.choose_move_interface))

    return btlMaster, stimulus

