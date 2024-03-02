import typing
from unittest.mock import Mock
from typing import Optional, List

import pyClarion as cl
from pyClarion import nd
import pytest
from poke_env.environment import (
    Battle, Pokemon, PokemonType, Move, Status, Effect
)

from battlemaster.adapters.clarion_adapter import (
    MindAdapter, BattleConcept, PerceptionFactory, GroupedStimulusInput
)
from battlemaster.clarion_ext.attention import GroupedChunkInstance
from battlemaster.clarion_ext.numdicts_ext import get_chunk_from_numdict


class TestMindAdapter:
    @pytest.fixture
    def battle(self) -> Battle:
        battle = Mock(spec=Battle)
        return battle

    @pytest.fixture
    def acs_terminus(self) -> cl.Construct:
        return Mock(spec=cl.Construct)

    @pytest.fixture
    def perception_factory(self) -> PerceptionFactory:
        return Mock(spec=PerceptionFactory)

    @pytest.fixture
    def mind_adapter(self, acs_terminus: cl.Construct, perception_factory: PerceptionFactory) -> MindAdapter:
        structure = {
            cl.subsystem('acs'): {
                cl.terminus("choose_move"): acs_terminus
            }
        }
        mind = Mock(spec=cl.Structure, wraps=structure)
        mind.step = Mock()
        mind.__getitem__ = Mock()
        mind.__getitem__.side_effect = structure.__getitem__
        stimulus = Mock(spec=cl.Construct)
        return MindAdapter(mind, stimulus, perception_factory)

    def test_no_move_chosen(self, mind_adapter: MindAdapter, acs_terminus):
        self._given_no_chosen_move(acs_terminus)
        chosen_action = mind_adapter.choose_action()

        assert chosen_action is None

    def test_move_chosen(self, mind_adapter: MindAdapter, acs_terminus):
        self._given_chosen_move(acs_terminus, "snore")
        chosen_action = mind_adapter.choose_action()

        assert chosen_action is "snore"

    @staticmethod
    def _given_no_chosen_move(acs_terminus):
        acs_terminus.output = nd.NumDict()

    @staticmethod
    def _given_chosen_move(acs_terminus, move_name: str):
        acs_terminus.output = nd.NumDict({cl.chunk(move_name): 1.0})


class TestPerceptionFactory:
    @pytest.fixture
    def factory(self) -> PerceptionFactory:
        return PerceptionFactory()

    @pytest.fixture
    def battle(self) -> Battle:
        battle: Battle = Mock(spec=Battle)
        battle.active_pokemon = self._given_active_pokemon()
        battle.opponent_active_pokemon = self._given_opposing_pokemon()
        battle.available_moves = [self._given_move('thunderbolt'), self._given_move('icebeam')]

        return battle

    @pytest.fixture
    def perception(self, factory: PerceptionFactory, battle) -> GroupedStimulusInput:
        return factory.map(battle)

    @pytest.fixture
    def active_pokemon_perception(self, perception: GroupedStimulusInput) -> GroupedChunkInstance:
        perceived_pokemon = perception.to_stimulus()[BattleConcept.ACTIVE_POKEMON]
        return typing.cast(GroupedChunkInstance, get_chunk_from_numdict('blastoise', perceived_pokemon))

    def test_all_concepts_in_perception(self, perception: GroupedStimulusInput):
        for concept in [BattleConcept.ACTIVE_OPPONENT_TYPE, BattleConcept.AVAILABLE_MOVES, BattleConcept.ACTIVE_POKEMON]:
            assert concept in perception.to_stimulus()

    def test_opposing_pokemon_types_in_perception(self, perception: GroupedStimulusInput):
        perceived_opponent_types = perception.to_stimulus()[BattleConcept.ACTIVE_OPPONENT_TYPE]
        for expected_type in ['normal', 'flying']:
            assert cl.chunk(expected_type) in perceived_opponent_types

    def test_available_moves_in_perception(self, perception: GroupedStimulusInput):
        perceived_moves = perception.to_stimulus()[BattleConcept.AVAILABLE_MOVES]
        assert 2 == len(perceived_moves)
        for move_name in ['thunderbolt', 'icebeam']:
            assert cl.chunk(move_name) in perceived_moves

    def test_active_pokemon_in_perception(self, active_pokemon_perception: GroupedChunkInstance):
        assert 'blastoise' == active_pokemon_perception.cid
        assert 100 == active_pokemon_perception.get_feature_value('level')
        assert not active_pokemon_perception.get_feature_value('fainted')
        assert active_pokemon_perception.get_feature_value('active')
        assert not active_pokemon_perception.get_feature_value('terastallized')

    def test_active_pokemon_type_in_perception(self, active_pokemon_perception: GroupedChunkInstance):
        assert 1 == len(active_pokemon_perception.get_feature('type'))
        assert 'water' == active_pokemon_perception.get_feature_value('type')

    def test_active_pokemon_item_in_perception(self, active_pokemon_perception: GroupedChunkInstance):
        assert 'leftovers' == active_pokemon_perception.get_feature_value('item')

    def test_active_pokemon_statuses_in_perception(self, active_pokemon_perception: GroupedChunkInstance):
        assert 'brn' == active_pokemon_perception.get_feature_value('status')
        assert 2 == len(active_pokemon_perception.get_feature('volatile_status'))
        assert 'aqua_ring' == active_pokemon_perception.get_feature_value('volatile_status')[0]
        assert 'taunt' == active_pokemon_perception.get_feature_value('volatile_status')[1]

    def test_active_pokemon_stats_in_perception(self, active_pokemon_perception: GroupedChunkInstance):
        assert 291 == active_pokemon_perception.get_feature_value('atk')
        assert 328 == active_pokemon_perception.get_feature_value('def')
        assert 295 == active_pokemon_perception.get_feature_value('spa')
        assert 339 == active_pokemon_perception.get_feature_value('spd')
        assert 280 == active_pokemon_perception.get_feature_value('spe')
        assert 123 == active_pokemon_perception.get_feature_value('hp')
        assert 362 == active_pokemon_perception.get_feature_value('max_hp')

    def test_active_pokemon_stat_boosts_in_perception(self, active_pokemon_perception: GroupedChunkInstance):
        assert 2 == active_pokemon_perception.get_feature_value('atk_boost')
        assert -1 == active_pokemon_perception.get_feature_value('def_boost')
        assert 2 == active_pokemon_perception.get_feature_value('spa_boost')
        assert -1 == active_pokemon_perception.get_feature_value('spd_boost')
        assert 2 == active_pokemon_perception.get_feature_value('spe_boost')
        assert 0 == active_pokemon_perception.get_feature_value('accuracy_boost')
        assert 0 == active_pokemon_perception.get_feature_value('evasion_boost')

    def test_active_pokemon_moves_in_perception(self, active_pokemon_perception: GroupedChunkInstance):
        assert 4 == len(active_pokemon_perception.get_feature('move'))
        assert 'shellsmash' == active_pokemon_perception.get_feature_value('move')[0]
        assert 'icebeam' == active_pokemon_perception.get_feature_value('move')[1]
        assert 'hydropump' == active_pokemon_perception.get_feature_value('move')[2]
        assert 'terablast' == active_pokemon_perception.get_feature_value('move')[3]

    @classmethod
    def _given_active_pokemon(cls) -> Pokemon:
        pokemon: Pokemon = Mock(spec=Pokemon)
        pokemon.species = 'blastoise'
        pokemon.types = (cls._given_type('water'), None)
        pokemon.level = 100
        pokemon.fainted = False
        pokemon.active = True
        pokemon.status = Status.BRN
        pokemon.effects = {Effect.AQUA_RING: 1, Effect.TAUNT: 1}
        pokemon.stats = {'atk': 291, 'def': 328, 'spa': 295, 'spd': 339, 'spe': 280}
        pokemon.current_hp = 123
        pokemon.max_hp = 362
        pokemon.item = 'leftovers'
        pokemon.moves = {name: cls._given_move(name) for name in ['shellsmash', 'icebeam', 'hydropump', 'terablast']}
        pokemon.boosts = {'atk': 2, 'def': -1, 'spa': 2, 'spd': -1, 'spe': 2, 'accuracy': 0, 'evasion': 0}
        pokemon.terastallized = False

        return pokemon

    @classmethod
    def _given_opposing_pokemon(cls) -> Pokemon:
        pokemon: Pokemon = Mock(spec=Pokemon)
        pokemon.species = 'staraptor'
        pokemon.types = (cls._given_type('normal'), cls._given_type('flying'))
        return pokemon

    @staticmethod
    def _given_move(name: str) -> Move:
        move = Mock(spec=Move)
        move.id = name
        return move

    @staticmethod
    def _given_type(name: str) -> PokemonType:
        type = Mock(spec=PokemonType)
        type.name = name.upper()
        return type