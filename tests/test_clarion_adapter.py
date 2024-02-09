from unittest.mock import Mock
from typing import Tuple

import pyClarion as cl
import pytest
from poke_env.environment import Battle, Pokemon, PokemonType, Move
from poke_env.data import GenData

from battlemaster.clarion_adapter import MindAdapter


@pytest.fixture
def battle():
    battle = Mock(spec=Battle)
    pokemon = Mock(spec=Pokemon)
    type_ghost = Mock(spec=PokemonType)
    type_fairy = Mock(spec=PokemonType)
    battle.opponent_active_pokemon = pokemon
    pokemon.types = (type_ghost, type_fairy)
    type_ghost.name = 'ghost'
    type_fairy.name = 'fairy'
    return battle


@pytest.fixture
def mind_adapter(agent_stimulus: Tuple[cl.Structure, cl.Construct]) -> MindAdapter:
    return MindAdapter(agent_stimulus[0], agent_stimulus[1])


class TestMindAdapter:
    def test_choose_move_selects_super_effective_type(self, mind_adapter: MindAdapter, battle):
        expected_move = self._create_move('shadowball')
        battle.available_moves = [self._create_move('icepunch'),
                                  self._create_move('thunder'),
                                  expected_move]

        mind_adapter.perceive(battle)
        selected_move = mind_adapter.choose_action()

        assert selected_move == expected_move.id

    @staticmethod
    def _create_move(name: str) -> Move:
        move = Mock(spec=Move)
        move.id = name
        return move

