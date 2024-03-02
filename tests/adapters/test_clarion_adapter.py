from unittest.mock import Mock
from typing import Optional, List

import pyClarion as cl
from pyClarion import nd
import pytest
from poke_env.environment import Battle, Pokemon, PokemonType, Move

from battlemaster.adapters.clarion_adapter import MindAdapter, BattleConcept, PerceptionFactory, GroupedStimulusInput


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
        battle = Mock(spec=Battle)
        battle.opponent_active_pokemon = self._given_opposing_pokemon('normal', 'flying')
        battle.available_moves = [self._given_move('thunderbolt'), self._given_move('icebeam')]

        return battle

    @pytest.fixture
    def perception(self, factory: PerceptionFactory, battle) -> GroupedStimulusInput:
        return factory.map(battle)

    def test_all_concepts_in_perception(self, perception: GroupedStimulusInput):
        for concept in [BattleConcept.ACTIVE_OPPONENT_TYPE, BattleConcept.AVAILABLE_MOVES]:
            assert concept.value in perception.to_stimulus()

    def test_opposing_pokemon_types_in_perception(self, perception: GroupedStimulusInput):
        perceived_opponent_types = perception.to_stimulus()[BattleConcept.ACTIVE_OPPONENT_TYPE]
        for expected_type in ['normal', 'flying']:
            assert cl.chunk(expected_type) in perceived_opponent_types

    def test_available_moves_in_perception(self, perception: GroupedStimulusInput):
        perceived_moves = perception.to_stimulus()[BattleConcept.AVAILABLE_MOVES]
        assert 2 == len(perceived_moves)
        for move_name in ['thunderbolt', 'icebeam']:
            assert cl.chunk(move_name) in perceived_moves

    @staticmethod
    def _given_move(name: str) -> Move:
        move = Mock(spec=Move)
        move.id = name
        return move

    def _given_opposing_pokemon(self, type1: str, type2: Optional[str] = None) -> Pokemon:
        pokemon = Mock(spec=Pokemon)
        primary_type = self._given_type(type1)
        secondary_type = self._given_type(type2) if type2 is not None else None
        pokemon.types = (primary_type, secondary_type)
        return pokemon

    @staticmethod
    def _given_type(name: str) -> PokemonType:
        type = Mock(spec=PokemonType)
        type.name = name
        return type