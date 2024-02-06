from typing import Tuple, List, Dict

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
def type_chunks(nacs: cl.Structure) -> cl.Chunks:
    return nacs.assets.type_chunks


@pytest.fixture
def move_chunks(nacs: cl.Structure) -> cl.Chunks:
    return nacs.assets.move_chunks


@pytest.fixture
def pokemon_chunks(nacs: cl.Structure) -> cl.Chunks:
    return nacs.assets.pokemon_chunks


@pytest.fixture
def pokemon_database() -> GenData:
    return GenData(9)


def test_type_chunks_populated(type_chunks: cl.Chunks):
    types = ['normal', 'fighting', 'flying', 'poison', 'ground', 'rock', 'bug', 'ghost', 'steel', 'fire', 'water',
             'grass', 'electric', 'psychic', 'ice', 'dragon', 'dark', 'fairy']
    assert len(type_chunks) == len(types)
    for type in types:
        type_chunk = cl.chunk(type)
        assert type_chunk in type_chunks
        assert cl.feature('type', type) in type_chunks[type_chunk].features


def test_move_chunks_populated(move_chunks: cl.Chunks, pokemon_database: GenData):
    all_moves = pokemon_database.moves
    z_moves = {key: value for key, value in all_moves.items() if 'isZ' in value}
    expected_move_count = len(all_moves) - len(z_moves)
    assert len(move_chunks) == expected_move_count


@pytest.mark.parametrize("expected_chunks", [
    ('airslash', [("type", "flying"), ("base_power", 75), ("priority", 0), ("accuracy", 95), ("category", "special")]),
    ('amnesia', [("type", "psychic"), ("base_power", 0), ("priority", 0), ("accuracy", 100), ("category", "status")]),
])
def test_move_chunks_have_expected_features(expected_chunks: Tuple[str, List[Tuple[str, any]]], move_chunks: cl.Chunks):
    chunk_name, features = expected_chunks
    move_chunk = move_chunks[cl.chunk(chunk_name)]
    assert len(move_chunk.features) == len(features) + 1
    assert cl.feature('move', chunk_name) in move_chunk.features
    for feature in features:
        assert cl.feature(feature[0], feature[1]) in move_chunk.features


def test_pokemon_chunks_populated(pokemon_chunks: cl.Chunks, pokemon_database: GenData):
    all_pokemon = pokemon_database.pokedex
    assert len(pokemon_chunks) == len(all_pokemon)


@pytest.mark.parametrize("expected_chunks", [
    ('abra', [("type", "psychic"), ("type", None), ("hp", 25), ("attack", 20), ("defense", 15), ("special_attack", 105),
              ("special_defense", 55), ("speed", 90), ("weight", 19.5)]),
    ('diancie', [("type", "fairy"), ("type", "rock"), ("hp", 50), ("attack", 100), ("defense", 150),
                ("special_attack", 100), ("special_defense", 150), ("speed", 50), ("weight", 8.8)]),
])
def test_pokemon_chunks_have_expected_features(expected_chunks: Tuple[str, List[Tuple[str, any]]], pokemon_chunks: cl.Chunks):
    chunk_name, features = expected_chunks
    pokemon_chunk = pokemon_chunks[cl.chunk(chunk_name)]
    assert len(pokemon_chunk.features) == len(features) + 1
    assert cl.feature('pokemon') in pokemon_chunk.features
    for feature in features:
        assert cl.feature(feature[0], feature[1]) in pokemon_chunk.features


@pytest.mark.parametrize("defending_types, expected_super_effective_types", [
    (["normal"], ["fighting"]),
    (["ghost"], ["ghost", "dark"]),
    (["steel", "flying"], ["electric", "rock", "ice", "fighting", "fire", "ground"])
])
def test_super_effective_association(defending_types, expected_super_effective_types, agent: cl.Structure, stimulus: cl.Construct, nacs_terminus: cl.Construct):
    presented_types = {cl.chunk(defending_type): 1. for defending_type in defending_types}
    stimulus.process.input({'active_opponent_type': presented_types})
    agent.step()
    nacs_output = nacs_terminus.output

    super_effective_types = [type_chunk.cid for type_chunk, weight in iter(nacs_output.items())]
    assert sorted(expected_super_effective_types) == sorted(super_effective_types)


@pytest.mark.parametrize("active_opponent_type, available_moves, acceptable_moves", [
    (["normal"], ["tackle", "doublekick", "leer", "mudslap"], ["doublekick"]),
    (["ghost"], ["knockoff", "sludgewave", "doubleedge"], ["knockoff"]),
    (["steel", "flying"], ["thunder", "stoneedge", "sludge", "gigadrain"], ["thunder", "stoneedge"])
])
def test_acs_chooses_super_effective_move_from_available_moves(active_opponent_type: List[str], available_moves: List[str], acceptable_moves: List[str], agent: cl.Structure, stimulus: cl.Construct, acs_terminus: cl.Construct):
    stimulus.process.input({
        'active_opponent_type': {cl.chunk(defending_type): 1. for defending_type in active_opponent_type},
        'available_moves': {cl.chunk(name): 1. for name in available_moves}
    })
    agent.step()

    acs_action = acs_terminus.output
    chosen_move = next(iter(acs_action)).val

    assert chosen_move in acceptable_moves

