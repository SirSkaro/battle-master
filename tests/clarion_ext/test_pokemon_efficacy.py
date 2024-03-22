import pytest
import pyClarion as cl
from pyClarion import nd

from battlemaster.clarion_ext.pokemon_efficacy import EffectiveMoves

type_source = cl.buffer('opponent_type')
move_source = cl.buffer('available_moves')


@pytest.fixture
def move_chunks() -> cl.Chunks:
    chunks = cl.Chunks()
    data = [('ember', 10, 'fire'), ('watergun', 20, 'water'), ('vinewhip', 30, 'grass'), ('rockthrow', 50, 'rock')]

    for name, power, type in data:
        chunks.define(cl.chunk(name),
                      cl.feature('move', name),
                      cl.feature('base_power', power),
                      cl.feature('type', type))

    return chunks


@pytest.fixture
def process(move_chunks: cl.Chunks) -> EffectiveMoves:
    return EffectiveMoves(type_source, move_source, move_chunks)


@pytest.mark.parametrize("opponent_type, expected_moves", [
        (("grass",), ['ember', 'rockthrow']),
        (("fire", "rock"), ['vinewhip', 'watergun', 'rockthrow'])
    ])
def test_only_keeps_effective_moves(process: EffectiveMoves, opponent_type, expected_moves):
    inputs = {
        cl.buffer('opponent_type'): {cl.chunk(type): 1. for type in opponent_type},
        cl.buffer('available_moves'): nd.NumDict({cl.chunk('ember'): 1., cl.chunk('watergun'): 1., cl.chunk('vinewhip'): 1., cl.chunk('rockthrow'): 1.}, default=0.)
    }
    result = process.call(inputs)

    assert len(result) == len(expected_moves)
    for super_effective_move_chunk in result.keys():
        assert super_effective_move_chunk.cid in expected_moves


def test_normalizes_move_weights(process: EffectiveMoves):
    inputs = {
        cl.buffer('opponent_type'): {cl.chunk(type): 1. for type in ('fire', 'rock')},
        cl.buffer('available_moves'): nd.NumDict({cl.chunk('ember'): 1., cl.chunk('watergun'): 1., cl.chunk('vinewhip'): 1., cl.chunk('rockthrow'): 1.},default=0.)
    }

    result = process.call(inputs)

    assert result[cl.chunk('watergun')] == 1.0
    assert result[cl.chunk('rockthrow')] == 0.5
    assert result[cl.chunk('vinewhip')] == 0.25


def test_assumes_normal_efficacy_for_unknown_move(process: EffectiveMoves):
    inputs = {
        cl.buffer('opponent_type'): {cl.chunk(type): 1. for type in ('dragon', 'steel')},
        cl.buffer('available_moves'): nd.NumDict({cl.chunk('recharge'): 1.}, default=0.)
    }

    result = process.call(inputs)

    assert result[cl.chunk('recharge')] == 1.

