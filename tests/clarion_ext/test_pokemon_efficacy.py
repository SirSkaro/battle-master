import pytest
import pyClarion as cl
from pyClarion import nd

from battlemaster.clarion_ext.pokemon_efficacy import MoveEfficacies

@pytest.fixture
def move_chunks() -> cl.Chunks:
    chunks = cl.Chunks()
    data = [('ember', 10, 'fire'), ('watergun', 20, 'water'), ('vinewhip', 30, 'grass')]

    for name, power, type in data:
        chunks.define(cl.chunk(name),
                              cl.feature('move', name),
                              cl.feature('base_power', power),
                              cl.feature('type', type))

    return chunks

@pytest.fixture
def process(move_chunks: cl.Chunks) -> MoveEfficacies:
    type_source = cl.buffer('opponent_type')
    move_source = cl.buffer('available_moves')
    return MoveEfficacies(type_source, move_source, move_chunks)


def test_only_keeps_super_effective_moves(process: MoveEfficacies):
    inputs = {
        cl.buffer('opponent_type'): nd.NumDict({cl.chunk('grass'): 1.}, default=0.),
        cl.buffer('available_moves'): nd.NumDict({cl.chunk('ember'): 1., cl.chunk('watergun'): 1., cl.chunk('vinewhip'): 1.}, default=0.)
    }
    result = process.call(inputs)

    assert len(result) == 1


#def test_normalizes_move_weights():
