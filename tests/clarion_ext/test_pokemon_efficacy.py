import pytest
import pyClarion as cl
from pyClarion import nd

from battlemaster.clarion_ext.pokemon_efficacy import EffectiveMoves, EffectiveSwitches, DefensiveSwitches
from battlemaster.clarion_ext.attention import GroupedChunk


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

        assert result[cl.chunk('watergun')] == 1.0
        assert result[cl.chunk('rockthrow')] == 0.5
        assert result[cl.chunk('vinewhip')] == 0.25

    def test_assumes_normal_efficacy_for_unknown_move(self, process: EffectiveMoves):
        inputs = {
            cl.buffer('opponent_type'): {cl.chunk(type): 1. for type in ('dragon', 'steel')},
            cl.buffer('available_moves'): nd.NumDict({cl.chunk('recharge'): 1.}, default=0.)
        }

        result = process.call(inputs)

        assert result[cl.chunk('recharge')] == 0.25


class TestEffectiveSwitches:
    @pytest.fixture
    def pokemon_chunks(self) -> cl.Chunks:
        chunks = cl.Chunks()
        data = [('caterpie', ('bug',)), ('pidgey', ('normal', 'flying')), ('mankey', ('fighting',)),
                ('bisharp', ('dark', 'steel')), ('blastoise', ('water',)), ('registeel', ('steel',))]

        for name, types in data:
            chunks.define(cl.chunk(name),
                          *[cl.feature('type', type) for type in types])

        return chunks

    @pytest.fixture
    def process(self, pokemon_chunks) -> EffectiveSwitches:
        type_source = cl.buffer('opponent_type')
        switch_source = cl.buffer('available_switches')
        return EffectiveSwitches(type_source, switch_source, pokemon_chunks)

    @pytest.mark.parametrize("opponent_type, expected_switches", [
        (("grass",), ['caterpie', 'pidgey', 'mankey', 'bisharp']),
        (("fire", "rock"), ['blastoise', 'mankey', 'bisharp'])
    ])
    def test_only_keeps_effective_switches(self, process: EffectiveSwitches, opponent_type, expected_switches):
        inputs = {
            cl.buffer('opponent_type'): {cl.chunk(type): 1. for type in opponent_type},
            cl.buffer('available_switches'): nd.NumDict(
                {GroupedChunk('caterpie', 'switches'): 1.,
                 GroupedChunk('pidgey', 'switches'): 1.,
                 GroupedChunk('blastoise', 'switches'): 1.,
                 GroupedChunk('mankey', 'switches'): 1.,
                 GroupedChunk('bisharp', 'switches'): 1.},
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
                {GroupedChunk('caterpie', 'switches'): 1.,
                 GroupedChunk('registeel', 'switches'): 1.,
                 GroupedChunk('mankey', 'switches'): 1.},
                default=0.)
        }

        result = process.call(inputs)

        assert result[cl.chunk('caterpie')] == 1.0 / 3
        assert result[cl.chunk('mankey')] == 0.5 / 3
        assert result[cl.chunk('registeel')] == 0.25 / 3


class TestDefensiveSwitches:
    @pytest.fixture
    def pokemon_chunks(self) -> cl.Chunks:
        chunks = cl.Chunks()
        data = [('caterpie', ('bug',)), ('pidgey', ('normal', 'flying')), ('mankey', ('fighting',)),
                ('bisharp', ('dark', 'steel')), ('blastoise', ('water',)), ('registeel', ('steel',)),
                ('tropius', ('flying', 'grass'))]

        for name, types in data:
            chunks.define(cl.chunk(name),
                          *[cl.feature('type', type) for type in types])

        return chunks

    @pytest.fixture
    def process(self, pokemon_chunks) -> DefensiveSwitches:
        type_source = cl.buffer('opponent_type')
        switch_source = cl.buffer('available_switches')
        return DefensiveSwitches(type_source, switch_source, pokemon_chunks)

    @pytest.mark.parametrize("opponent_type, expected_switches", [
        (("psychic",), ['registeel', 'bisharp']),
        (("bug", "water"), ['blastoise', 'registeel', 'pidgey', 'mankey'])
    ])
    def test_only_keeps_defensive_switches(self, process: DefensiveSwitches, opponent_type, expected_switches):
        inputs = {
            cl.buffer('opponent_type'): {cl.chunk(type): 1. for type in opponent_type},
            cl.buffer('available_switches'): nd.NumDict({
                GroupedChunk('caterpie', 'switches'): 1.,
                GroupedChunk('pidgey', 'switches'): 1.,
                GroupedChunk('blastoise', 'switches'): 1.,
                GroupedChunk('mankey', 'switches'): 1.,
                GroupedChunk('bisharp', 'switches'): 1.,
                GroupedChunk('registeel', 'switches'): 1.,},
                default=0.)
        }
        result = process.call(inputs)

        assert len(result) == len(expected_switches)
        for super_effective_move_chunk in result.keys():
            assert super_effective_move_chunk.cid in expected_switches

    def test_normalizes_switch_weights(self, process: EffectiveSwitches):
        inputs = {
            cl.buffer('opponent_type'): {cl.chunk(type): 1. for type in ('grass', 'psychic')},
            cl.buffer('available_switches'): nd.NumDict(
                {GroupedChunk('pidgey', 'switches'): 1.,
                 GroupedChunk('tropius', 'switches'): 1.,
                 GroupedChunk('bisharp', 'switches'): 1.},
                default=0.)
        }

        result = process.call(inputs)

        assert result[cl.chunk('bisharp')] == 8.0 / 16 / 3
        assert result[cl.chunk('tropius')] == 4.0 / 16 / 3
        assert result[cl.chunk('pidgey')] == 2.0 / 16 / 3
