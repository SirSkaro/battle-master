from unittest.mock import Mock, MagicMock
from typing import Optional, List

import pyClarion as cl
from pyClarion import nd
import pytest
from poke_env.environment import Battle, Pokemon, PokemonType, Move

from battlemaster.clarion_adapter import MindAdapter, BattleConcept


@pytest.fixture
def battle():
    battle = Mock(spec=Battle)
    return battle


@pytest.fixture
def acs_terminus() -> cl.Construct:
    return Mock(spec=cl.Construct)


@pytest.fixture
def mind_adapter(acs_terminus: cl.Construct) -> MindAdapter:
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
    return MindAdapter(mind, stimulus)


class TestMindAdapter:
    def test_all_concepts_in_perception(self, mind_adapter: MindAdapter, battle):
        battle.opponent_active_pokemon = self._given_opposing_pokemon('foo', 'bar')
        battle.available_moves = [self._given_move('icepunch')]

        perception = mind_adapter.perceive(battle)

        for concept in BattleConcept:
            assert concept.value in perception

    @pytest.mark.parametrize("active_opponent_types", [
        (["normal", None]),
        (["ghost", "fairy"])
    ])
    def test_opposing_pokemon_types_in_perception(self, mind_adapter: MindAdapter, battle, active_opponent_types: List[str]):
        battle.opponent_active_pokemon = self._given_opposing_pokemon(active_opponent_types[0], active_opponent_types[1])
        battle.available_moves = []

        perception = mind_adapter.perceive(battle)

        perceived_opponent_types = perception[BattleConcept.ACTIVE_OPPONENT_TYPE]
        for expected_type in [type for type in active_opponent_types if type is not None]:
            assert cl.chunk(expected_type) in perceived_opponent_types

    @pytest.mark.parametrize("available_moves", [
        (["foo", "bar", "baz", "faz"]),
        (["get them!"])
    ])
    def test_available_moves_in_perception(self, mind_adapter: MindAdapter, battle, available_moves: List[str]):
        battle.opponent_active_pokemon = self._given_opposing_pokemon("some type")
        battle.available_moves = []

        perception = mind_adapter.perceive(battle)

        perceived_moves = perception[BattleConcept.AVAILABLE_MOVES]
        for move_name in perceived_moves:
            assert cl.chunk(move_name) in perceived_moves

    def test_no_move_chosen(self, mind_adapter: MindAdapter, acs_terminus):
        self._given_no_chosen_move(acs_terminus)
        chosen_action = mind_adapter.choose_action()

        assert chosen_action is None

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

    @staticmethod
    def _given_no_chosen_move(acs_terminus):
        acs_terminus.output = nd.NumDict()
