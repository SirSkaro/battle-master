from typing import Tuple, Optional, List
from unittest.mock import Mock

import pytest
import pyClarion as cl

from battlemaster import mind
from battlemaster.agents import BattleMasterPlayer
from poke_env.environment import Battle, Pokemon, Move, PokemonType


@pytest.fixture
def mind_stimulus() -> Tuple[cl.Structure, cl.Construct]:
    return mind.create_agent()


@pytest.fixture
def battlemaster(mind_stimulus: Tuple[cl.Structure, cl.Construct]) -> BattleMasterPlayer:
    return BattleMasterPlayer(mind_stimulus[0], mind_stimulus[1], start_listening=False)


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


class TestBattleMasterPlayer:
    def test_choose_move_selects_super_effective_type(self, battlemaster: BattleMasterPlayer, battle):
        expected_move = self._create_move('ghost')
        battle.available_moves = [self._create_move('ice'), self._create_move('electric'), expected_move]

        selected_move = battlemaster.choose_move(battle)

        assert selected_move.order == expected_move

    @staticmethod
    def _create_move(type_name: str) -> Move:
        move = Mock(spec=Move)
        pokemon_type = Mock(spec=PokemonType)
        move.type = pokemon_type
        pokemon_type.name = type_name
        return move

