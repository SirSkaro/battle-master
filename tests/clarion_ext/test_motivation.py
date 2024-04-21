from typing import Dict, Callable, Mapping, Any

import pyClarion as cl
from pyClarion import nd
import pytest

from battlemaster.adapters.clarion_adapter import BattleConcept
from battlemaster.clarion_ext.attention import GroupedChunk, GroupedChunkInstance
from battlemaster.clarion_ext.motivation import (
    goal, StickyBoltzmannSelector,
    drive, DoDamageDriveEvaluator, KoOpponentDriveEvaluator, DriveStrength, GroupedStimulus,
    KeepPokemonAliveEvaluator, KeepHealthyEvaluator, ConstantDriveEvaluator,
    KeepTypeAdvantageDriveEvaluator, RevealHiddenInformationDriveEvaluator
)


class TestStickyBoltzmannSelector:
    @pytest.fixture
    def goal_source(self) -> cl.Symbol:
        return cl.buffer('goals')

    @pytest.fixture
    def battle_metadata_source(self) -> cl.Symbol:
        return cl.buffer('battle')

    @pytest.fixture
    def process(self, goal_source, battle_metadata_source) -> StickyBoltzmannSelector:
        return StickyBoltzmannSelector(goal_source, battle_metadata_source, temperature=0.1, threshold=0.5)

    @pytest.fixture
    def given_selection(self, request, monkeypatch):
        selection_goal = request.param[0]
        selection_strength = request.param[1]
        monkeypatch.setattr(nd, 'boltzmann', lambda d, t: nd.NumDict({selection_goal: selection_strength}, default=0.))

    @pytest.fixture
    def battle_tag(self) -> str:
        return 'genNou-123'

    @pytest.fixture
    def battle_metadata_input(self, battle_tag: str):
        return nd.NumDict({GroupedChunkInstance('metadata', BattleConcept.BATTLE, [cl.feature('tag', battle_tag)]): 1.})

    @pytest.fixture
    def given_previous_goal(self, request, process, battle_tag: str):
        selection_goal = request.param[0]
        selection_strength = request.param[1]
        process._previous_goals[battle_tag] = nd.NumDict({selection_goal: selection_strength}, default=0.)

    @pytest.fixture
    def inputs(self, battle_metadata_source, battle_metadata_input):
        return {
            battle_metadata_source: battle_metadata_input
        }

    @pytest.mark.parametrize('given_selection', [(goal('eat'), 3.5)], indirect=True)
    @pytest.mark.parametrize('given_previous_goal', [(goal('sleep'), 5.)], indirect=True)
    def test_stick_to_previous_goal_if_activation_not_above_threshold(self, process, inputs, goal_source, given_selection, given_previous_goal):
        inputs[goal_source] = nd.NumDict({
            goal('eat'): 3.5,
            goal('sleep'): 4.,
        })
        result = process.call(inputs)

        assert goal('sleep') in result
        assert not goal('eat') in result

    @pytest.mark.parametrize('given_selection', [(goal('sleep'), 2.)], indirect=True)
    @pytest.mark.parametrize('given_previous_goal', [(goal('sleep'), 5.)], indirect=True)
    def test_stick_to_previous_goal_if_new_goal_is_the_same(self, process, inputs, goal_source, given_selection, given_previous_goal):
        inputs[goal_source] = nd.NumDict({
            goal('eat'): 5.,
            goal('sleep'): 2.,
        })

        result = process.call(inputs)

        assert goal('sleep') in result
        assert not goal('eat') in result

    @pytest.mark.parametrize('given_selection', [(goal('eat'), 5.)], indirect=True)
    @pytest.mark.parametrize('given_previous_goal', [(goal('sleep'), 3.)], indirect=True)
    def test_switch_to_new_goal_if_above_threshold(self, process, inputs, goal_source, given_selection, given_previous_goal):
        inputs[goal_source] = nd.NumDict({
            goal('eat'): 5.,
            goal('sleep'): 3.,
        })

        result = process.call(inputs)

        assert goal('eat') in result
        assert not goal('sleep') in result


class TestDriveStrength:
    @pytest.fixture
    def drive_evaluations(self) -> Dict[drive, Callable[[GroupedStimulus], float]]:
        return {
            drive.DO_DAMAGE: lambda stim: 1.,
            drive.KO_OPPONENT: lambda stim: 10.
        }

    @pytest.fixture
    def stimulus_source(self) -> cl.Symbol:
        return cl.buffer('stimulus')

    @pytest.fixture
    def process(self, stimulus_source, drive_evaluations) -> DriveStrength:
        return DriveStrength(stimulus_source, drive_evaluations)

    @pytest.fixture
    def inputs(self, stimulus_source) -> Mapping[Any, nd.NumDict]:
        return {
            stimulus_source: nd.NumDict({
                GroupedChunk('drapion', BattleConcept.TEAM): 1.,
                GroupedChunk('snorlax', BattleConcept.TEAM): 1.,
                GroupedChunk('joltik', BattleConcept.OPPONENT_TEAM): 1.,
            })
        }

    @pytest.fixture
    def output(self, process, inputs) -> nd.NumDict:
        return process.call(inputs)

    @pytest.mark.parametrize("expected_drive, expected_strength", [
        (drive.DO_DAMAGE, 1.),
        (drive.KO_OPPONENT, 10.),
    ])
    def test_drive_has_strength(self, output, expected_drive: drive, expected_strength: float):
        assert expected_drive in output
        assert expected_strength == output[expected_drive]

    def test_missing_drive_has_default_value(self, output):
        assert drive.DEBUFF_OPPONENT not in output
        assert output[drive.DEBUFF_OPPONENT] == output.default


class TestDoDamageDriveEvaluator:
    @pytest.fixture
    def stimulus(self, request) -> GroupedStimulus:
        has_available_moves = request.param
        stimulus = {
            BattleConcept.AVAILABLE_MOVES: nd.MutableNumDict()
        }

        if has_available_moves:
            stimulus[BattleConcept.AVAILABLE_MOVES][cl.chunk('some_move')] = 1.0

        return stimulus

    @pytest.fixture
    def evaluator(self):
        return DoDamageDriveEvaluator()

    @pytest.mark.parametrize('stimulus', [True], indirect=True)
    def test_evaluate_has_moves(self, evaluator: DoDamageDriveEvaluator, stimulus):
        strength = evaluator.evaluate(stimulus)
        assert strength == 5.0

    @pytest.mark.parametrize('stimulus', [False], indirect=True)
    def test_evaluate_no_moves(self, evaluator: DoDamageDriveEvaluator, stimulus):
        strength = evaluator.evaluate(stimulus)
        assert strength == 0.0


class TestKoOpponentDriveEvaluator:
    @pytest.fixture
    def stimulus(self, request) -> GroupedStimulus:
        hp_percentage = request.param[0]
        has_available_moves = request.param[1]

        stimulus = {
            BattleConcept.AVAILABLE_MOVES: nd.MutableNumDict({}),
            BattleConcept.OPPONENT_ACTIVE_POKEMON: nd.MutableNumDict({GroupedChunkInstance('elekid', BattleConcept.OPPONENT_ACTIVE_POKEMON, [cl.feature('hp_percentage', hp_percentage)]): 1.}),
        }

        if has_available_moves:
            stimulus[BattleConcept.AVAILABLE_MOVES][cl.chunk('some_move')] = 1.0

        return stimulus

    @pytest.fixture
    def evaluator(self):
        return KoOpponentDriveEvaluator()

    @pytest.mark.parametrize('stimulus', [(100, True)], indirect=True)
    def test_evaluate_full_health(self, evaluator: KoOpponentDriveEvaluator, stimulus):
        strength = evaluator.evaluate(stimulus)
        assert strength == 0.05

    @pytest.mark.parametrize('stimulus', [(1, True)], indirect=True)
    def test_evaluate_almost_no_health(self, evaluator: KoOpponentDriveEvaluator, stimulus):
        strength = evaluator.evaluate(stimulus)
        assert strength == 5.0

    @pytest.mark.parametrize('stimulus', [(100, False)], indirect=True)
    def test_forced_switch(self, evaluator: KoOpponentDriveEvaluator, stimulus):
        strength = evaluator.evaluate(stimulus)
        assert strength == 0.


class TestKeepPokemonAliveEvaluator:
    @pytest.fixture
    def stimulus(self, request) -> GroupedStimulus:
        hp = request.param[0]
        max_hp = request.param[1]
        has_active_pokemon = request.param[2]
        has_available_switches = request.param[3]
        stimulus = {
            BattleConcept.AVAILABLE_SWITCHES: nd.MutableNumDict({}),
            BattleConcept.ACTIVE_POKEMON: nd.MutableNumDict({})
        }

        if has_active_pokemon:
            stimulus[BattleConcept.ACTIVE_POKEMON][GroupedChunkInstance('blissey', BattleConcept.ACTIVE_POKEMON, [cl.feature('hp', hp), cl.feature('max_hp', max_hp)])] = 1.

        if has_available_switches:
            stimulus[BattleConcept.AVAILABLE_SWITCHES][cl.chunk('some_pokemon')] = 1.

        return stimulus

    @pytest.fixture
    def evaluator(self):
        return KeepPokemonAliveEvaluator()

    @pytest.mark.parametrize('stimulus', [(714, 714, True, True)], indirect=True)
    def test_evaluate_full_health(self, evaluator: KeepPokemonAliveEvaluator, stimulus):
        strength = evaluator.evaluate(stimulus)
        assert strength == 0.05

    @pytest.mark.parametrize('stimulus', [(1, 714, True, True)], indirect=True)
    def test_evaluate_one_hp(self, evaluator: KeepPokemonAliveEvaluator, stimulus):
        strength = evaluator.evaluate(stimulus)
        assert strength == 5

    @pytest.mark.parametrize('stimulus', [(357, 714, True, True)], indirect=True)
    def test_evaluate_half_hp(self, evaluator: KeepPokemonAliveEvaluator, stimulus):
        strength = evaluator.evaluate(stimulus)
        assert strength == 2.5

    @pytest.mark.parametrize('stimulus', [(0, 0, False, True)], indirect=True)
    def test_no_active_pokemon(self, evaluator: KeepPokemonAliveEvaluator, stimulus):
        strength = evaluator.evaluate(stimulus)
        assert strength == 0.0

    @pytest.mark.parametrize('stimulus', [(357, 714, True, False)], indirect=True)
    def test_no_available_switches(self, evaluator: KeepPokemonAliveEvaluator, stimulus):
        strength = evaluator.evaluate(stimulus)
        assert strength == 0.0


class TestKeepHealthyEvaluator:
    @pytest.fixture
    def stimulus(self, request) -> GroupedStimulus:
        hp = request.param[0]
        max_hp = request.param[1]
        has_available_switches = request.param[2]
        stimulus = {
            BattleConcept.AVAILABLE_SWITCHES: nd.MutableNumDict({}),
            BattleConcept.ACTIVE_POKEMON: nd.NumDict({GroupedChunkInstance('blissey', BattleConcept.ACTIVE_POKEMON,[cl.feature('hp', hp), cl.feature('max_hp', max_hp)]): 1.})
        }

        if has_available_switches:
            stimulus[BattleConcept.AVAILABLE_SWITCHES][cl.chunk('some_pokemon')] = 1.

        return stimulus

    @pytest.fixture
    def evaluator(self):
        return KeepHealthyEvaluator(0.8)

    @pytest.mark.parametrize('stimulus', [(571.2, 714, True)], indirect=True)
    def test_evaluate_full_health(self, evaluator: KeepHealthyEvaluator, stimulus):
        strength = evaluator.evaluate(stimulus)
        assert strength == 5.0

    @pytest.mark.parametrize('stimulus', [(1, 714, True)], indirect=True)
    def test_evaluate_one_hp(self, evaluator: KeepHealthyEvaluator, stimulus):
        strength = evaluator.evaluate(stimulus)
        assert strength < 0.05

    @pytest.mark.parametrize('stimulus', [(714, 714, True)], indirect=True)
    def test_evaluate_half_hp(self, evaluator: KeepHealthyEvaluator, stimulus):
        strength = evaluator.evaluate(stimulus)
        assert strength < 5.0

    @pytest.mark.parametrize('stimulus', [(357, 714, False)], indirect=True)
    def test_no_available_switches(self, evaluator: KeepPokemonAliveEvaluator, stimulus):
        strength = evaluator.evaluate(stimulus)
        assert strength == 0.0


class TestKeepTypeAdvantageDriveEvaluator:
    @pytest.fixture
    def stimulus(self, request) -> GroupedStimulus:
        is_force_switch = request.param
        return {
            BattleConcept.BATTLE: nd.NumDict({
                GroupedChunkInstance('metadata', BattleConcept.BATTLE, [cl.feature('force_switch', is_force_switch)]): 1.
            })
        }

    @pytest.fixture
    def evaluator(self):
        return KeepTypeAdvantageDriveEvaluator()

    @pytest.mark.parametrize('stimulus', [True], indirect=True)
    def test_evaluate_force_switch(self, evaluator: KeepTypeAdvantageDriveEvaluator, stimulus):
        strength = evaluator.evaluate(stimulus)
        assert strength == 5.0

    @pytest.mark.parametrize('stimulus', [False], indirect=True)
    def test_evaluate_not_force_switch(self, evaluator: KeepTypeAdvantageDriveEvaluator, stimulus):
        strength = evaluator.evaluate(stimulus)
        assert strength == 0.0


class TestRevealHiddenInformationDriveEvaluator:
    @pytest.fixture
    def stimulus(self) -> GroupedStimulus:
        return {
            BattleConcept.OPPONENT_ACTIVE_POKEMON: nd.NumDict({
                GroupedChunkInstance('dratini', BattleConcept.OPPONENT_ACTIVE_POKEMON,
                                     [cl.feature('move', 'wrap'), cl.feature('move', 'agility'), cl.feature('move', 'leer'), cl.feature('move', 'extremespeed'),
                                      cl.feature('ability', 'shedskin'), cl.feature('item', 'dragonscale'),
                                      cl.feature('fainted', False)]): 1.,
            }),
            BattleConcept.OPPONENT_TEAM: nd.NumDict({
                GroupedChunkInstance('beldum', BattleConcept.OPPONENT_TEAM,
                                     [cl.feature('move', 'takedown'),
                                      cl.feature('ability', 'clearbody'), cl.feature('item', None),
                                      cl.feature('fainted', False)]): 1.,
                GroupedChunkInstance('litwick', BattleConcept.OPPONENT_TEAM,
                                     [cl.feature('ability', None), cl.feature('item', 'focussash'),
                                      cl.feature('fainted', False)]): 1.
            })
        }

    @pytest.fixture
    def evaluator(self):
        return RevealHiddenInformationDriveEvaluator()

    def test_count_pokemon(self, evaluator: RevealHiddenInformationDriveEvaluator, stimulus):
        total, unknown = evaluator._count_unknown_pokemon(stimulus[BattleConcept.OPPONENT_ACTIVE_POKEMON], stimulus[BattleConcept.OPPONENT_TEAM])

        assert total == 6
        assert unknown == 3

    def test_count_moves(self, evaluator: RevealHiddenInformationDriveEvaluator, stimulus):
        total, unknown = evaluator._count_unknown_moves(6, stimulus[BattleConcept.OPPONENT_ACTIVE_POKEMON], stimulus[BattleConcept.OPPONENT_TEAM])

        assert total == 24
        assert unknown == 19

    def test_count_abilities(self, evaluator: RevealHiddenInformationDriveEvaluator, stimulus):
        total, unknown = evaluator._count_unknown_abilities(6, stimulus[BattleConcept.OPPONENT_ACTIVE_POKEMON], stimulus[BattleConcept.OPPONENT_TEAM])

        assert total == 6
        assert unknown == 4

    def test_count_items(self, evaluator: RevealHiddenInformationDriveEvaluator, stimulus):
        total, unknown = evaluator._count_unknown_items(6, stimulus[BattleConcept.OPPONENT_ACTIVE_POKEMON], stimulus[BattleConcept.OPPONENT_TEAM])

        assert total == 6
        assert unknown == 4

    def test_evaluate(self, evaluator: RevealHiddenInformationDriveEvaluator, stimulus):
        strength = evaluator.evaluate(stimulus)

        assert strength == 5 * 30/42


class TestConstantDriveEvaluator:
    def test_evaluate(self):
        constant_strength = 3.2
        evaluator = ConstantDriveEvaluator(constant_strength)
        strength = evaluator.evaluate({})

        assert strength == constant_strength
