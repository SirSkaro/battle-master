import typing
from unittest.mock import Mock
from typing import Optional, List, Dict

import pyClarion as cl
from pyClarion import nd
import pytest
from poke_env.environment import (
    Battle, Pokemon, PokemonType, Move, Status, Effect, SideCondition
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
        self._given_players(battle)
        battle.active_pokemon = self._given_active_pokemon()
        battle.team = self._given_team(battle.active_pokemon)
        battle.opponent_active_pokemon = self._given_opposing_pokemon()
        battle.opponent_team = self._given_opposing_team(battle.opponent_active_pokemon)
        battle.available_moves = [self._given_move('thunderbolt'), self._given_move('icebeam')]
        self._given_side_conditions(battle)

        return battle

    @pytest.fixture
    def perception(self, factory: PerceptionFactory, battle) -> GroupedStimulusInput:
        return factory.map(battle)

    @pytest.fixture
    def active_pokemon_perception(self, perception: GroupedStimulusInput) -> GroupedChunkInstance:
        perceived_pokemon = perception.to_stimulus()[BattleConcept.ACTIVE_POKEMON]
        return typing.cast(GroupedChunkInstance, get_chunk_from_numdict('blastoise', perceived_pokemon))

    @pytest.fixture
    def team_perception(self, perception: GroupedStimulusInput) -> nd.NumDict:
        return perception.to_stimulus()[BattleConcept.TEAM]

    @pytest.fixture
    def players_perception(self, perception: GroupedStimulusInput) -> nd.NumDict:
        return perception.to_stimulus()[BattleConcept.PLAYERS]

    @pytest.fixture
    def opponent_active_pokemon_perception(self, perception: GroupedStimulusInput) -> GroupedChunkInstance:
        perceived_pokemon = perception.to_stimulus()[BattleConcept.OPPONENT_ACTIVE_POKEMON]
        return typing.cast(GroupedChunkInstance, get_chunk_from_numdict('staraptor', perceived_pokemon))

    @pytest.fixture
    def opponent_team_perception(self, perception: GroupedStimulusInput) -> nd.NumDict:
        return perception.to_stimulus()[BattleConcept.OPPONENT_TEAM]

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

    def test_active_pokemon_ability_in_perception(self, active_pokemon_perception: GroupedChunkInstance):
        assert 'torrent' == active_pokemon_perception.get_feature_value('ability')

    def test_active_pokemon_statuses_in_perception(self, active_pokemon_perception: GroupedChunkInstance):
        assert 'brn' == active_pokemon_perception.get_feature_value('status')
        assert 2 == len(active_pokemon_perception.get_feature('volatile_status'))
        volatile_statuses = active_pokemon_perception.get_feature_value('volatile_status')
        assert 'aqua_ring' == volatile_statuses[0]
        assert 'taunt' == volatile_statuses[1]

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
        moves = active_pokemon_perception.get_feature_value('move')
        assert 'shellsmash' == moves[0]
        assert 'icebeam' == moves[1]
        assert 'hydropump' == moves[2]
        assert 'terablast' == moves[3]

    def test_all_pokemon_in_team(self, team_perception: nd.NumDict):
        assert 2 == len(team_perception)
        assert cl.chunk('blastoise') in team_perception
        assert cl.chunk('charizard') in team_perception

    def test_fainted_benched_pokemon_in_team_perception(self, team_perception: nd.NumDict):
        benched_pokemon = typing.cast(GroupedChunkInstance, get_chunk_from_numdict('charizard', team_perception))
        assert benched_pokemon.get_feature_value('fainted')
        assert not benched_pokemon.get_feature_value('active')

    def test_self_in_perception(self, players_perception: nd.NumDict):
        player = typing.cast(GroupedChunkInstance, get_chunk_from_numdict('self', players_perception))
        assert 'me' == player.get_feature_value('name')
        assert 'AI' == player.get_feature_value('role')

    def test_opponent_in_perception(self, players_perception: nd.NumDict):
        player = typing.cast(GroupedChunkInstance, get_chunk_from_numdict('opponent', players_perception))
        assert 'them' == player.get_feature_value('name')
        assert 'punching bag' == player.get_feature_value('role')

    def test_side_conditions_in_perception(self, perception: GroupedStimulusInput):
        perceived_conditions = perception.to_stimulus()[BattleConcept.SIDE_CONDITIONS]
        assert 2 == len(perceived_conditions)

        light_screen = typing.cast(GroupedChunkInstance, get_chunk_from_numdict('light_screen', perceived_conditions))
        reflect = typing.cast(GroupedChunkInstance, get_chunk_from_numdict('reflect', perceived_conditions))

        assert 23 == light_screen.get_feature_value('start_turn')
        assert 24 == reflect.get_feature_value('start_turn')

    def test_opponent_side_conditions_in_perception(self, perception: GroupedStimulusInput):
        perceived_conditions = perception.to_stimulus()[BattleConcept.OPPONENT_SIDE_CONDITIONS]
        assert 1 == len(perceived_conditions)

        spikes = typing.cast(GroupedChunkInstance, get_chunk_from_numdict('spikes', perceived_conditions))
        assert 3 == spikes.get_feature_value('layers')

    def test_opponent_active_pokemon_in_perception(self, opponent_active_pokemon_perception: GroupedChunkInstance):
        assert 'staraptor' == opponent_active_pokemon_perception.cid
        assert 100 == opponent_active_pokemon_perception.get_feature_value('level')
        assert not opponent_active_pokemon_perception.get_feature_value('fainted')
        assert opponent_active_pokemon_perception.get_feature_value('active')
        assert not opponent_active_pokemon_perception.get_feature_value('terastallized')

    def test_opponent_active_pokemon_type_in_perception(self, opponent_active_pokemon_perception: GroupedChunkInstance):
        assert 2 == len(opponent_active_pokemon_perception.get_feature('type'))
        types = opponent_active_pokemon_perception.get_feature_value('type')
        assert 'normal' == types[0]
        assert 'flying' == types[1]

    def test_opponent_active_pokemon_item_in_perception(self, opponent_active_pokemon_perception: GroupedChunkInstance):
        assert 'choiceband' == opponent_active_pokemon_perception.get_feature_value('item')

    def test_opponent_active_pokemon_unknown_ability_in_perception(self, opponent_active_pokemon_perception: GroupedChunkInstance):
        assert opponent_active_pokemon_perception.get_feature_value('ability') is None

    def test_opponent_active_pokemon_statuses_in_perception(self, opponent_active_pokemon_perception: GroupedChunkInstance):
        assert 'tox' == opponent_active_pokemon_perception.get_feature_value('status')
        assert 'future_sight' == opponent_active_pokemon_perception.get_feature_value('volatile_status')

    def test_opponent_active_pokemon_stat_boosts_in_perception(self, opponent_active_pokemon_perception: GroupedChunkInstance):
        assert 0 == opponent_active_pokemon_perception.get_feature_value('atk_boost')
        assert -1 == opponent_active_pokemon_perception.get_feature_value('def_boost')
        assert 0 == opponent_active_pokemon_perception.get_feature_value('spa_boost')
        assert -1 == opponent_active_pokemon_perception.get_feature_value('spd_boost')
        assert 0 == opponent_active_pokemon_perception.get_feature_value('spe_boost')
        assert 1 == opponent_active_pokemon_perception.get_feature_value('accuracy_boost')
        assert 1 == opponent_active_pokemon_perception.get_feature_value('evasion_boost')

    def test_opponent_active_pokemon_moves_in_perception(self, opponent_active_pokemon_perception: GroupedChunkInstance):
        assert 1 == len(opponent_active_pokemon_perception.get_feature('move'))
        assert 'closecombat' == opponent_active_pokemon_perception.get_feature_value('move')

    def test_all_pokemon_in_opponent_team(self, opponent_team_perception: nd.NumDict):
        assert 2 == len(opponent_team_perception)
        assert cl.chunk('staraptor') in opponent_team_perception
        assert cl.chunk('tornadus') in opponent_team_perception

    def test_fainted_benched_pokemon_in_opponent_team_perception(self, opponent_team_perception: nd.NumDict):
        benched_pokemon = typing.cast(GroupedChunkInstance, get_chunk_from_numdict('tornadus', opponent_team_perception))
        assert benched_pokemon.get_feature_value('fainted')
        assert not benched_pokemon.get_feature_value('active')
        assert benched_pokemon.get_feature_value('terastallized')
        assert 'grass' == benched_pokemon.get_feature_value('type')

    @staticmethod
    def _given_players(battle):
        battle.player_username = 'me'
        battle.player_role = 'AI'
        battle.opponent_username = 'them'
        battle.opponent_role = 'punching bag'

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
        pokemon.ability = 'torrent'
        pokemon.boosts = {'atk': 2, 'def': -1, 'spa': 2, 'spd': -1, 'spe': 2, 'accuracy': 0, 'evasion': 0}
        pokemon.terastallized = False

        return pokemon

    @classmethod
    def _given_opposing_pokemon(cls) -> Pokemon:
        pokemon: Pokemon = Mock(spec=Pokemon)
        pokemon.species = 'staraptor'
        pokemon.types = (cls._given_type('normal'), cls._given_type('flying'))
        pokemon.level = 100
        pokemon.fainted = False
        pokemon.active = True
        pokemon.status = Status.TOX
        pokemon.effects = {Effect.FUTURE_SIGHT: 1}
        pokemon.stats = {'atk': 372, 'def': 262, 'spa': 218, 'spd': 240, 'spe': 328}
        pokemon.current_hp = 75
        pokemon.item = 'choiceband'
        pokemon.moves = {name: cls._given_move(name) for name in ['closecombat']}
        pokemon.ability = None
        pokemon.boosts = {'atk': 0, 'def': -1, 'spa': 0, 'spd': -1, 'spe': 0, 'accuracy': 1, 'evasion': 1}
        pokemon.terastallized = False

        return pokemon

    @classmethod
    def _given_team(cls, active_pokemon: Pokemon) -> Dict[str, Pokemon]:
        team = {active_pokemon.species: active_pokemon}
        benched_pokemon: Pokemon = Mock(spec=Pokemon)
        benched_pokemon.species = 'charizard'
        benched_pokemon.types = (cls._given_type('fire'), cls._given_type('flying'))
        benched_pokemon.level = 100
        benched_pokemon.fainted = True
        benched_pokemon.active = False
        benched_pokemon.status = None
        benched_pokemon.effects = {}
        benched_pokemon.stats = {'atk': 293, 'def': 280, 'spa': 348, 'spd': 295, 'spe': 328}
        benched_pokemon.current_hp = 0
        benched_pokemon.max_hp = 360
        benched_pokemon.item = 'choicespecs'
        benched_pokemon.moves = {name: cls._given_move(name) for name in ['fireblast', 'solarbeam']}
        benched_pokemon.ability = 'blaze'
        benched_pokemon.boosts = {'atk': 0, 'def': 0, 'spa': 0, 'spd': 0, 'spe': 0, 'accuracy': 0, 'evasion': 0}
        benched_pokemon.terastallized = False

        team[benched_pokemon.species] = benched_pokemon

        return team

    @classmethod
    def _given_opposing_team(cls, active_pokemon: Pokemon) -> Dict[str, Pokemon]:
        team = {active_pokemon.species: active_pokemon}
        benched_pokemon: Pokemon = Mock(spec=Pokemon)
        benched_pokemon.species = 'tornadus'
        benched_pokemon.types = (cls._given_type('grass'), None)
        benched_pokemon.level = 100
        benched_pokemon.fainted = True
        benched_pokemon.active = False
        benched_pokemon.status = None
        benched_pokemon.effects = {}
        benched_pokemon.stats = {'atk': 361, 'def': 262, 'spa': 383, 'spd': 284, 'spe': 353}
        benched_pokemon.current_hp = 0
        benched_pokemon.item = None
        benched_pokemon.moves = {name: cls._given_move(name) for name in ['terablast', 'uturn']}
        benched_pokemon.ability = None
        benched_pokemon.boosts = {'atk': 0, 'def': 0, 'spa': 0, 'spd': 0, 'spe': 0, 'accuracy': 1, 'evasion': 1}
        benched_pokemon.terastallized = True

        team[benched_pokemon.species] = benched_pokemon

        return team

    @staticmethod
    def _given_side_conditions(battle):
        battle.side_conditions = {
            SideCondition.LIGHT_SCREEN: 23,
            SideCondition.REFLECT: 24
        }
        battle.opponent_side_conditions = {
            SideCondition.SPIKES: 3
        }

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