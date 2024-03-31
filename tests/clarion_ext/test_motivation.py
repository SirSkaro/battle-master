from typing import Dict, Callable, Mapping, Any

import pyClarion as cl
from pyClarion import nd
import pytest

from battlemaster.adapters.clarion_adapter import BattleConcept
from battlemaster.clarion_ext.attention import GroupedChunk
from battlemaster.clarion_ext.motivation import (
    drive, DoDamageDriveEvaluator, KoOpponentDriveEvaluator, DriveStrength, GroupedStimulus
)


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
