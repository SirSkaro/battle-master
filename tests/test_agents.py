from unittest.mock import Mock, MagicMock
from typing import Optional

import pytest
from battlemaster.agents import BattleMasterPlayer
from poke_env.environment import Battle, Move, Pokemon, PokemonType
import pyClarion as cl

from battlemaster.clarion_adapter import MindAdapter


def _given_move(name: str) -> Move:
    move = Mock(spec=Move)
    move.id = name
    return move

@pytest.fixture
def battle():
    battle = Mock(spec=Battle)
    battle.available_switches = []
    battle.can_mega_evolve = False
    battle.can_dynamax = False
    battle.can_tera = False
    battle.can_z_move = False
    return battle


class TestBattleMasterPlayerUnitTests:
    @pytest.fixture
    def mind_adapter(self) -> MindAdapter:
        return Mock(spec=MindAdapter)

    @pytest.fixture
    def player(self, mind_adapter: MindAdapter) -> BattleMasterPlayer:
        return BattleMasterPlayer(mind_adapter, start_listening=False)

    def test_choose_move_selects_available_move(self, player: BattleMasterPlayer, battle, mind_adapter):
        mind_adapter.choose_action = MagicMock(return_value='bodyslam')
        battle.available_moves = [_given_move('sleeptalk'), _given_move('bodyslam')]

        issued_action = player.choose_move(battle)

        assert issued_action.order.id == 'bodyslam'

    def test_choose_move_selects_random_if_chosen_move_is_not_available(self, player: BattleMasterPlayer, battle, mind_adapter):
        mind_adapter.choose_action = MagicMock(return_value='hyperbeam')
        battle.available_moves = [_given_move('sleeptalk')]

        issued_action = player.choose_move(battle)

        assert issued_action.order.id == 'sleeptalk'

    def test_choose_move_selects_random_move_if_no_action_chosen(self, player: BattleMasterPlayer, battle, mind_adapter):
        mind_adapter.choose_action = MagicMock(return_value=None)
        battle.available_moves = [_given_move('gigaimpact')]

        issued_action = player.choose_move(battle)

        assert issued_action.order.id == 'gigaimpact'


class TestBattleMasterPlayerComponentTests:
    @pytest.fixture
    def mind_adapter(self, agent: cl.Structure, stimulus: cl.Construct) -> MindAdapter:
        return MindAdapter(agent, stimulus)

    @pytest.fixture
    def player(self, mind_adapter: MindAdapter) -> BattleMasterPlayer:
        return BattleMasterPlayer(mind_adapter, start_listening=False)

    def test_chooses_super_effective_move(self, player: BattleMasterPlayer, battle):
        battle.available_moves = [_given_move('darkpulse'), _given_move('bodyslam')]
        battle.opponent_active_pokemon = self._given_opposing_pokemon('ghost')

        issued_action = player.choose_move(battle)

        assert issued_action.order.id == 'darkpulse'

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