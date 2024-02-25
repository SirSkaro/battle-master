from typing import Tuple
import re

import pyClarion as cl
from pyClarion import chunk, rule, feature, buffer, subsystem, chunks, features
from poke_env import gen_data

from .clarion_ext.attention import NamedStimuli, AttentionFilter
from .clarion_ext.pokemon_efficacy import EffectiveMoves
from .adapters.clarion_adapter import BattleConcept

pokemon_database = gen_data.GenData.from_gen(9)


def _define_type_chunks() -> Tuple[cl.Chunks, cl.Rules]:
    type_chunks = cl.Chunks()
    rule_database = cl.Rules()
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
        type_chunks.define(chunk(type), feature('type', type))

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

    return type_chunks, rule_database


_camel_case_pattern = re.compile(r'(?<!^)(?=[A-Z])')
def _to_snake_case(camel_case: str) -> str:
    camel_case = camel_case.replace('-', '')
    camel_case = _camel_case_pattern.sub('_', camel_case).lower()
    return camel_case.replace(' ', '_')


def _define_move_chunks() -> cl.Chunks:
    move_chunks = cl.Chunks()
    all_moves = pokemon_database.moves
    for name, move_data in all_moves.items():
        if 'isZ' in move_data:
            continue
        move_chunks.define(chunk(name),
                              feature('move', name),
                              feature('accuracy', 100 if move_data['accuracy'] == True else move_data['accuracy']),
                              feature('base_power', move_data['basePower']),
                              feature('category', _to_snake_case(move_data['category'])),
                              feature('priority', move_data['priority']),
                              feature('type', _to_snake_case(move_data['type'])))

    return move_chunks


def _define_pokemon_chunks() -> cl.Chunks:
    pokemon_chunks = cl.Chunks()
    all_pokemon = pokemon_database.pokedex
    for name, pokemon in all_pokemon.items():
        typing = pokemon['types']
        stats = pokemon['baseStats']
        pokemon_chunks.define(chunk(name),
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

    return pokemon_chunks


def create_agent() -> Tuple[cl.Structure, cl.Construct]:
    type_chunks, rule_database = _define_type_chunks()
    move_chunks = _define_move_chunks()
    pokemon_chunks = _define_pokemon_chunks()

    wm_interface = cl.RegisterArray.Interface(name="wm", slots=1, vops=("effective_available_moves",))

    agent = cl.Structure(name=cl.agent('btlMaster'))

    with agent:
        stimulus = cl.Construct(
            name=buffer("stimulus"),
            process=NamedStimuli()
        )

        nacs = cl.Structure(name=subsystem("nacs"),
                            assets=cl.Assets(
                                type_chunks=type_chunks,
                                move_chunks=move_chunks,
                                pokemon_chunks=pokemon_chunks,
                                rdb=rule_database)
                            )

        cl.Construct(name=buffer("wm"),
                     process=cl.RegisterArray(
                        controller=(subsystem("nacs"), cl.terminus("wm_write")),
                        sources=((subsystem("nacs"), cl.terminus("main")),),
                        interface=wm_interface)
                     )

        acs = cl.Structure(name=subsystem("acs"))

        with nacs:
            cl.Construct(name=cl.chunks("opponent_type_in"), process=AttentionFilter(base=cl.MaxNodes(sources=[buffer("stimulus")]), attend_to=[BattleConcept.ACTIVE_OPPONENT_TYPE.value]))
            cl.Construct(name=cl.chunks("available_moves_in"), process=AttentionFilter(base=cl.MaxNodes(sources=[buffer("stimulus")]), attend_to=[BattleConcept.AVAILABLE_MOVES.value]))
            cl.Construct(name=cl.flow_tt("super_effective_available_moves"), process=EffectiveMoves(type_source=cl.chunks("opponent_type_in"), move_source=cl.chunks("available_moves_in"), move_chunks=nacs.assets.move_chunks))
            cl.Construct(name=chunks("out"), process=cl.MaxNodes(sources=[cl.flow_tt("super_effective_available_moves")]))
            cl.Construct(name=cl.terminus("main"), process=cl.ThresholdSelector(source=chunks("out"), threshold=0.1))
            cl.Construct(name=cl.terminus('wm_write'), process=cl.Constants(cl.nd.NumDict({feature(('wm', ('w', 0)), 'effective_available_moves'): 1.0, feature(("wm", ("r", 0)), "read"): 1.0}, default=0.0)))

        with acs:
            cl.Construct(name=cl.chunks('wm'), process=cl.MaxNodes(sources=[buffer("wm")]))
            cl.Construct(name=chunks("out"), process=cl.MaxNodes(sources=[cl.chunks("wm")]))
            cl.Construct(name=cl.terminus("choose_move"), process=cl.BoltzmannSelector(source=cl.chunks("out"), temperature=0.2, threshold=0.))

    return agent, stimulus

