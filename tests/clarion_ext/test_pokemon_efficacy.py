import pytest
import pyClarion as cl
from pyClarion import nd

from battlemaster.clarion_ext.pokemon_efficacy import EffectiveMoves, EffectiveSwitches
from battlemaster.clarion_ext.attention import GroupedChunkInstance


class TestEffectiveMoves:
    @pytest.fixture
    def move_chunks(self) -> cl.Chunks:
        chunks = cl.Chunks()
        data = [('ember', 10, 'fire'), ('watergun', 20, 'water'), ('vinewhip', 30, 'grass'), ('rockthrow', 50, 'rock')]

        for name, power, type in data:
            chunks.define(cl.chunk(name),
                          cl.feature('move', name),
                          cl.feature('base_power', power),
                          cl.feature('type', type))

        return chunks

    @pytest.fixture
    def process(self, move_chunks: cl.Chunks) -> EffectiveMoves:
        type_source = cl.buffer('opponent_type')
        move_source = cl.buffer('available_moves')
        return EffectiveMoves(type_source, move_source, move_chunks)

    @pytest.mark.parametrize("opponent_type, expected_moves", [
            (("grass",), ['ember', 'rockthrow']),
            (("fire", "rock"), ['vinewhip', 'watergun', 'rockthrow'])
        ])
    def test_only_keeps_effective_moves(self, process: EffectiveMoves, opponent_type, expected_moves):
        inputs = {
            cl.buffer('opponent_type'): {cl.chunk(type): 1. for type in opponent_type},
            cl.buffer('available_moves'): nd.NumDict({cl.chunk('ember'): 1., cl.chunk('watergun'): 1., cl.chunk('vinewhip'): 1., cl.chunk('rockthrow'): 1.}, default=0.)
        }
        result = process.call(inputs)

        assert len(result) == len(expected_moves)
        for super_effective_move_chunk in result.keys():
            assert super_effective_move_chunk.cid in expected_moves

    def test_normalizes_move_weights(self, process: EffectiveMoves):
        inputs = {
            cl.buffer('opponent_type'): {cl.chunk(type): 1. for type in ('fire', 'rock')},
            cl.buffer('available_moves'): nd.NumDict({cl.chunk('ember'): 1., cl.chunk('watergun'): 1., cl.chunk('vinewhip'): 1., cl.chunk('rockthrow'): 1.},default=0.)
        }

        result = process.call(inputs)

        assert result[cl.chunk('watergun')] == 1.0 / 4
        assert result[cl.chunk('rockthrow')] == 0.5 / 4
        assert result[cl.chunk('vinewhip')] == 0.25 / 4

    def test_assumes_normal_efficacy_for_unknown_move(self, process: EffectiveMoves):
        inputs = {
            cl.buffer('opponent_type'): {cl.chunk(type): 1. for type in ('dragon', 'steel')},
            cl.buffer('available_moves'): nd.NumDict({cl.chunk('recharge'): 1.}, default=0.)
        }

        result = process.call(inputs)

        assert result[cl.chunk('recharge')] == 0.25


class TestEffectiveSwitches:
    @pytest.fixture
    def process(self) -> EffectiveSwitches:
        type_source = cl.buffer('opponent_type')
        switch_source = cl.buffer('available_switches')
        return EffectiveSwitches(type_source, switch_source)

    @pytest.mark.parametrize("opponent_type, expected_switches", [
        (("grass",), ['caterpie', 'pidgey', 'mankey', 'bisharp']),
        (("fire", "rock"), ['blastoise', 'mankey', 'bisharp'])
    ])
    def test_only_keeps_effective_switches(self, process: EffectiveSwitches, opponent_type, expected_switches):
        inputs = {
            cl.buffer('opponent_type'): {cl.chunk(type): 1. for type in opponent_type},
            cl.buffer('available_switches'): nd.NumDict(
                {GroupedChunkInstance('caterpie', 'switches', [cl.feature('type', 'bug')]): 1.,
                 GroupedChunkInstance('pidgey', 'switches', [cl.feature('type', 'flying'), cl.feature('type', 'normal')]): 1.,
                 GroupedChunkInstance('blastoise', 'switches', [cl.feature('type', 'water')]): 1.,
                 GroupedChunkInstance('mankey', 'switches', [cl.feature('type', 'fighting')]): 1.,
                 GroupedChunkInstance('bisharp', 'switches', [cl.feature('type', 'steel'), cl.feature('type', 'dark')]): 1.},
                default=0.)
        }
        result = process.call(inputs)

        assert len(result) == len(expected_switches)
        for super_effective_move_chunk in result.keys():
            assert super_effective_move_chunk.cid in expected_switches

    def test_normalizes_switch_weights(self, process: EffectiveSwitches):
        inputs = {
            cl.buffer('opponent_type'): {cl.chunk(type): 1. for type in ('grass', 'dark')},
            cl.buffer('available_switches'): nd.NumDict(
                {GroupedChunkInstance('caterpie', 'switches', [cl.feature('type', 'bug')]): 1.,
                 GroupedChunkInstance('registeel', 'switches', [cl.feature('type', 'steel')]): 1.,
                 GroupedChunkInstance('mankey', 'switches', [cl.feature('type', 'fighting')]): 1.,},
                default=0.)
        }

        result = process.call(inputs)

        assert result[cl.chunk('caterpie')] == 1.0 / 3
        assert result[cl.chunk('mankey')] == 0.5 / 3
        assert result[cl.chunk('registeel')] == 0.25 / 3
