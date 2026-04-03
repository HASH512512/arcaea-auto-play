from pathlib import Path

import pytest

from autoplay.domain import Arc, Chart, Hold, Tap
from autoplay.domain.errors import MissingDesignantChoiceError
from autoplay.parser import parse_aff_chart


SAMPLES = Path(__file__).parent / "samples"


def _sample(name: str) -> str:
    return (SAMPLES / name).read_text(encoding="utf-8")


def test_parse_basic_chart() -> None:
    chart = parse_aff_chart(_sample("basic_4k.aff"), designant_choice=True)
    assert isinstance(chart, Chart)
    assert len(chart.notes) == 3
    assert isinstance(chart.notes[0], Tap)
    assert isinstance(chart.notes[1], Hold)
    assert isinstance(chart.notes[2], Arc)


def test_parse_designant_requires_choice() -> None:
    with pytest.raises(MissingDesignantChoiceError):
        parse_aff_chart(_sample("with_designant.aff"), designant_choice=None)


def test_parse_designant_skips_when_disabled() -> None:
    chart = parse_aff_chart(_sample("with_designant.aff"), designant_choice=False)
    assert chart.notes == []


def test_parse_invalid_lines_still_keeps_valid_notes() -> None:
    chart = parse_aff_chart(_sample("invalid_lines.aff"), designant_choice=True)
    assert any(isinstance(note, Tap) for note in chart.notes)
