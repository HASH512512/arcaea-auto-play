from pathlib import Path

from autoplay.analyzer import ModeAnalyzer
from autoplay.parser import parse_aff_chart
from autoplay.solver import CoordConv, solve_4k, solve_6k


SAMPLES = Path(__file__).parent / "samples"


def _sample(name: str) -> str:
    return (SAMPLES / name).read_text(encoding="utf-8")


def _converter() -> CoordConv:
    return CoordConv((171, 1350), (171, 300), (2376, 300), (2376, 1350))


def test_solver_4k_generates_touch_events() -> None:
    chart = parse_aff_chart(_sample("basic_4k.aff"), designant_choice=True)
    events = solve_4k(chart, _converter())
    assert events
    all_actions = {event.action.name for items in events.values() for event in items}
    assert "DOWN" in all_actions
    assert "UP" in all_actions


def test_solver_6k_generates_touch_events() -> None:
    chart = parse_aff_chart(_sample("basic_6k_scenecontrol.aff"), designant_choice=True)
    events = solve_6k(chart, _converter())
    assert events


def test_split_and_solve_combines_modes() -> None:
    content = _sample("basic_6k_scenecontrol.aff")
    chart = parse_aff_chart(content, designant_choice=True)
    analyzer = ModeAnalyzer()
    analyzer.analyze_chart_for_6k(content, chart)
    merged = analyzer.split_and_solve_chart(chart, _converter(), solve_4k, solve_6k)
    assert merged


def test_zero_length_arc_does_not_break_solver() -> None:
    chart = parse_aff_chart(_sample("edge_zero_length_arc.aff"), designant_choice=True)
    events = solve_4k(chart, _converter())
    assert events
