from typing import Tuple, List

import pytest
from pytest import MonkeyPatch
import pyClarion as cl
from pyClarion import nd
from poke_env.data import GenData

from battlemaster.clarion_ext.attention import GroupedStimulusInput
from battlemaster.clarion_ext.simulation import MentalSimulation
from battlemaster.adapters.clarion_adapter import BattleConcept


@pytest.fixture
def type_chunks(nacs: cl.Structure) -> cl.Chunks:
    return nacs.assets.type_chunks


@pytest.fixture
def move_chunks(nacs: cl.Structure) -> cl.Chunks:
    return nacs.assets.move_chunks


@pytest.fixture
def pokemon_chunks(nacs: cl.Structure) -> cl.Chunks:
    return nacs.assets.pokemon_chunks


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


@pytest.mark.parametrize("active_opponent_type, available_moves, acceptable_moves", [
    (["rock", "fire"], ["hydropump", "earthquake", "fireblast", "playrough"], ["hydropump", "earthquake"]),
    (["psychic", "dark"], ["uturn", "playrough", "doubleedge"], ["uturn", "playrough", "doubleedge"]),
    (["steel", "flying"], ["thunder", "stoneedge", "sludge", "gigadrain"], ["thunder", "stoneedge"])
])
def test_writes_effective_moves_to_working_memory(active_opponent_type: List[str], available_moves: List[str], acceptable_moves: List[str], agent: cl.Structure, stimulus: cl.Construct, working_memory: cl.Construct):
    perception = GroupedStimulusInput(['active_opponent_type', 'available_moves'])
    for defending_type in active_opponent_type:
        perception.add_chunk_to_group(cl.chunk(defending_type), 'active_opponent_type')
    for name in available_moves:
        perception.add_chunk_to_group(cl.chunk(name), 'available_moves')

    stimulus.process.input(perception)
    agent.step()
    working_memory_contents = working_memory.output

    super_effective_moves = [type_chunk.cid for type_chunk, weight in iter(working_memory_contents.items())]
    assert sorted(acceptable_moves) == sorted(super_effective_moves)


@pytest.mark.parametrize("active_opponent_type, available_moves, acceptable_moves", [
    (["normal"], ["tackle", "doublekick", "shadowball", "superpower"], ["tackle", "doublekick", "superpower"]),
    (["ghost"], ["knockoff", "sludgewave", "doubleedge"], ["knockoff"]),
    (["steel", "flying"], ["thunder", "stoneedge", "sludge", "gigadrain"], ["thunder", "stoneedge"])
])
def test_acs_chooses_effective_move_from_available_moves(active_opponent_type: List[str], available_moves: List[str], acceptable_moves: List[str], agent: cl.Structure, stimulus: cl.Construct, acs_terminus: cl.Construct):
    perception = GroupedStimulusInput(['active_opponent_type', 'available_moves'])
    for defending_type in active_opponent_type:
        perception.add_chunk_to_group(cl.chunk(defending_type), 'active_opponent_type')
    for name in available_moves:
        perception.add_chunk_to_group(cl.chunk(name), 'available_moves')

    stimulus.process.input(perception)
    agent.step()

    acs_action = acs_terminus.output
    chosen_move = next(iter(acs_action)).cid

    assert chosen_move in acceptable_moves

@pytest.mark.parametrize("team, opponent_team, expected_effort", [
    (["psyduck", "pidgey"], ["caterpie"], "autopilot"),
    (["pikachu"], ["raichu", "rhydon"], "try_hard"),
])
def test_mcs_outputs_effort(team: List[str], opponent_team: List[str], expected_effort: str, agent: cl.Structure,
                            stimulus: cl.Construct, mcs_effort_gate: cl.Construct, monkeypatch: MonkeyPatch):
    monkeypatch.setattr(MentalSimulation, 'call', lambda _self, inputs: nd.NumDict(default=0.))

    perception = GroupedStimulusInput([BattleConcept.TEAM, BattleConcept.OPPONENT_TEAM])
    for pokemon in team:
        perception.add_chunk_to_group(cl.chunk(pokemon), BattleConcept.TEAM)
    for pokemon in opponent_team:
        perception.add_chunk_to_group(cl.chunk(pokemon), BattleConcept.OPPONENT_TEAM)

    stimulus.process.input(perception)
    agent.step()
    effort = next(iter(mcs_effort_gate.output))

    assert expected_effort == effort.tag[1]
