from typing import Tuple
import re

import pyClarion as cl
from pyClarion import chunk, feature, buffer, subsystem, chunks
from poke_env import gen_data

from .clarion_ext.attention import NamedStimuli, AttentionFilter
from .clarion_ext.pokemon_efficacy import EffectiveMoves, EffectiveSwitches
from .clarion_ext.positioning import DecideEffort, Effort, EFFORT_INTERFACE
from .clarion_ext.working_memory import WM_INTERFACE, WmSource
from .clarion_ext.simulation import MentalSimulation
from .clarion_ext.filters import ReasoningPath
from .clarion_ext.motivation import (
    drive, goal, DriveStrength, DoDamageDriveEvaluator, KoOpponentDriveEvaluator, KeepPokemonAliveEvaluator,
    KeepHealthyEvaluator, ConstantDriveEvaluator
)
from .adapters.clarion_adapter import BattleConcept
from .adapters.poke_engine_adapter import Simulator

pokemon_database = gen_data.GenData.from_gen(9)


def _define_goals() -> cl.Chunks:
    goal_chunks = cl.Chunks()

    goal_chunks.define(
        goal('preserve'),
        drive('keep_pokemon_alive'),
        drive('keep_type_advantage'),
        drive('keep_healthy'),
        drive('have_more_pokemon_than_opponent'),
        drive('have_super_effective_move_available'),
    )
    goal_chunks.define(
        goal('sacrifice'),
        drive('keep_type_advantage'),
        drive('prevent_opponent_buff'),
        drive('prevent_type_disadvantage'),
    )
    goal_chunks.define(
        goal('deal_damage'),
        drive('ko_opponent'),
        drive('do_damage'),
        drive('prevent_opponent_buff'),
        drive('keep_pokemon_alive'),
        drive('reveal_hidden_information'),
    )
    goal_chunks.define(
        goal('switch'),
        drive('keep_pokemon_alive'),
        drive('keep_healthy'),
        drive('prevent_opponent_buff'),
        drive('prevent_type_disadvantage'),
        drive('have_super_effective_move_available'),
        drive('reveal_hidden_information'),
    )

    return goal_chunks


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
                              *[feature('type', type.lower()) for type in typing],
                              feature('hp', stats['hp']),
                              feature('attack', stats['atk']),
                              feature('defense', stats['def']),
                              feature('special_attack', stats['spa']),
                              feature('special_defense', stats['spd']),
                              feature('speed', stats['spe']),
                              feature('weight', pokemon['weightkg']))

    return pokemon_chunks


def create_agent() -> Tuple[cl.Structure, cl.Construct]:
    goal_chunks = _define_goals()
    move_chunks = _define_move_chunks()
    pokemon_chunks = _define_pokemon_chunks()

    agent = cl.Structure(name=cl.agent('btlMaster'))

    with agent:
        stimulus = cl.Construct(
            name=buffer("stimulus"),
            process=NamedStimuli()
        )

        ms = cl.Structure(
            name=subsystem('ms'),
            assets=cl.Assets(
                goal_chunks=goal_chunks,
                personality={
                    drive('keep_pokemon_alive'): KeepPokemonAliveEvaluator().evaluate,
                    drive('have_more_pokemon_than_opponent'): ConstantDriveEvaluator(4.0).evaluate,
                    drive('ko_opponent'): KoOpponentDriveEvaluator().evaluate,
                    drive('do_damage'): DoDamageDriveEvaluator().evaluate,
                    drive('keep_healthy'): KeepHealthyEvaluator().evaluate,
                    drive('buff_self'): ConstantDriveEvaluator(1.0).evaluate,
                    drive('debuff_opponent'): ConstantDriveEvaluator(1.0).evaluate,
                    drive('prevent_opponent_buff'): ConstantDriveEvaluator(3.0).evaluate,
                    drive('keep_type_advantage'): ConstantDriveEvaluator(4.0).evaluate,
                    drive('prevent_type_disadvantage'): ConstantDriveEvaluator(4.0).evaluate,
                    drive('have_super_effective_move_available'): ConstantDriveEvaluator(4.0).evaluate,
                    drive('reveal_hidden_information'): ConstantDriveEvaluator(4.0).evaluate
                }
            )
        )

        mcs = cl.Structure(name=subsystem('mcs'))

        cl.Construct(
            name=cl.buffer("mcs_effort_gate"),
            process=cl.ParamSet(
                controller=(cl.subsystem('mcs'), cl.terminus('effort')),
                interface=EFFORT_INTERFACE)
        )

        nacs = cl.Structure(
            name=subsystem("nacs"),
            assets=cl.Assets(
                move_chunks=move_chunks,
                pokemon_chunks=pokemon_chunks,
                mental_simulator=Simulator())
        )

        cl.Construct(
            name=buffer("wm"),
            process=cl.RegisterArray(
                controller=(subsystem("nacs"), cl.terminus("wm_write")),
                sources=((subsystem("nacs"), cl.terminus("main")),),
                interface=WM_INTERFACE)
        )

        acs = cl.Structure(name=subsystem("acs"))

        with ms:
            pass

        with mcs:
            cl.Construct(name=cl.chunks("self_team_in"), process=AttentionFilter(base=cl.MaxNodes(sources=[buffer("stimulus")]), attend_to=[BattleConcept.TEAM, BattleConcept.ACTIVE_POKEMON]))
            cl.Construct(name=cl.chunks("opponent_team_in"), process=AttentionFilter(base=cl.MaxNodes(sources=[buffer("stimulus")]), attend_to=[BattleConcept.OPPONENT_TEAM, BattleConcept.OPPONENT_ACTIVE_POKEMON]))
            cl.Construct(name=cl.features('effort'), process=DecideEffort(team_source=cl.chunks('self_team_in'), opponent_team_source=cl.chunks('opponent_team_in')))
            cl.Construct(name=cl.features('effort_gate_write'), process=cl.Constants(cl.nd.NumDict({cl.feature(('effort', 'w'), 'clrupd'): 1.0}, default=0.0)))
            cl.Construct(name=cl.features('effort_main'), process=cl.MaxNodes(sources=[cl.features('effort'), cl.features('effort_gate_write')]))
            cl.Construct(name=cl.terminus('effort'), process=cl.ActionSelector(source=cl.features('effort_main'), interface=EFFORT_INTERFACE, temperature=0.01))

        with nacs:
            cl.Construct(name=cl.chunks("opponent_type_in"), process=AttentionFilter(base=cl.MaxNodes(sources=[buffer("stimulus")]), attend_to=[BattleConcept.ACTIVE_OPPONENT_TYPE]))
            cl.Construct(name=cl.chunks("available_moves_in"), process=AttentionFilter(base=cl.MaxNodes(sources=[buffer("stimulus")]), attend_to=[BattleConcept.AVAILABLE_MOVES]))
            cl.Construct(name=cl.chunks("available_switches_in"), process=AttentionFilter(base=cl.MaxNodes(sources=[buffer("stimulus")]), attend_to=[BattleConcept.AVAILABLE_SWITCHES]))
            cl.Construct(name=cl.flow_tt("effective_available_moves"),
                         process=ReasoningPath(
                             base=EffectiveMoves(type_source=cl.chunks("opponent_type_in"), move_source=cl.chunks("available_moves_in"), move_chunks=nacs.assets.move_chunks),
                             controller=cl.buffer("mcs_effort_gate"),
                             interface=EFFORT_INTERFACE,
                             pidx=Effort.AUTOPILOT.index))
            cl.Construct(name=cl.flow_tt("effective_available_switches"),
                         process=ReasoningPath(
                             base=EffectiveSwitches(type_source=cl.chunks("opponent_type_in"), switch_source=cl.chunks("available_switches_in"), pokemon_chunks=nacs.assets.pokemon_chunks),
                             controller=cl.buffer("mcs_effort_gate"),
                             interface=EFFORT_INTERFACE,
                             pidx=Effort.AUTOPILOT.index))

            cl.Construct(name=cl.chunks("generate_and_test"),
                         process=ReasoningPath(
                             base=MentalSimulation(stimulus_source=cl.buffer('stimulus'), simulator=nacs.assets.mental_simulator),
                             controller=cl.buffer("mcs_effort_gate"),
                             interface=EFFORT_INTERFACE,
                             pidx=Effort.TRY_HARD.index
                         ))

            cl.Construct(name=cl.chunks("out"), process=cl.MaxNodes(sources=[cl.flow_tt("effective_available_moves"), cl.flow_tt("effective_available_switches"), cl.chunks("generate_and_test")]))
            cl.Construct(name=cl.terminus("main"), process=cl.ThresholdSelector(source=chunks("out"), threshold=0.001))
            cl.Construct(name=cl.terminus('wm_write'), process=cl.Constants(cl.nd.NumDict({feature(('wm', ('w', 0)), WmSource.CANDIDATE_MOVES.value): 1.0, feature(("wm", ("r", 0)), "read"): 1.0}, default=0.0)))

        with acs:
            cl.Construct(name=cl.chunks('wm'), process=cl.MaxNodes(sources=[buffer("wm")]))
            cl.Construct(name=cl.chunks("out"), process=cl.MaxNodes(sources=[cl.chunks("wm")]))
            cl.Construct(name=cl.terminus("choose_move"), process=cl.BoltzmannSelector(source=cl.chunks("out"), temperature=0.2, threshold=0.))

    return agent, stimulus

