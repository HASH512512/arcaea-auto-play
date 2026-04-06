from pathlib import Path

from autoplay.analyzer import ModeAnalyzer
from autoplay.parser import parse_aff_chart
from autoplay.solver import (
    CoordConv,
    build_logical_events_for_chart,
    solve_4k,
    solve_6k,
)


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


def test_arc_move_pointer_uses_arc_color() -> None:
    content = "\n".join(
        [
            "AudioOffset:0",
            "Title:arc_color_pointer",
            "",
            "arc(1000,1400,0.10,0.90,s,0.20,0.80,1,none,false);",
            "arc(1500,2000,0.90,0.10,s,0.80,0.20,3,none,false);",
        ]
    )
    chart = parse_aff_chart(content, designant_choice=True)
    events = solve_4k(chart, _converter())

    arc_events = [
        event
        for items in events.values()
        for event in items
        if event.source_type == "arc"
    ]
    assert arc_events

    pointers_by_note: dict[int, set[int]] = {}
    for event in arc_events:
        assert event.source_note_id is not None
        pointers_by_note.setdefault(event.source_note_id, set()).add(event.pointer)

    assert pointers_by_note[1] == {5001}
    assert pointers_by_note[2] == {5003}


def test_arctap_pointer_allocation_is_unchanged() -> None:
    chart = parse_aff_chart(_sample("with_arctap.aff"), designant_choice=True)
    events = solve_4k(chart, _converter())

    arctap_events = [
        event
        for items in events.values()
        for event in items
        if event.source_type == "arctap"
    ]
    assert len(arctap_events) == 4
    assert {event.pointer for event in arctap_events} == {1000, 1001}


def test_same_tick_arc_head_arctap_conflict_removes_arctap_events() -> None:
    content = "\n".join(
        [
            "AudioOffset:0",
            "Title:same_tick_conflict",
            "",
            "arc(1000,1600,0.10,0.90,s,0.20,0.80,1,none,false)[arctap(1000),arctap(1300)];",
        ]
    )
    chart = parse_aff_chart(content, designant_choice=True)
    events = solve_4k(chart, _converter())

    tick_1000 = events.get(1000, [])
    assert tick_1000
    assert not any(event.source_type == "arctap" for event in tick_1000)
    assert any(
        event.source_type == "arc" and event.action.name == "DOWN"
        for event in tick_1000
    )

    tick_1012 = events.get(1012, [])
    assert not any(event.source_type == "arctap" for event in tick_1012)

    tick_1300 = events.get(1300, [])
    assert any(
        event.source_type == "arctap" and event.action.name == "DOWN"
        for event in tick_1300
    )


def test_connected_same_color_arcs_do_not_lift_at_boundary() -> None:
    content = "\n".join(
        [
            "AudioOffset:0",
            "Title:connected_same_color_arcs",
            "",
            "arc(1000,1400,0.10,0.50,s,0.20,0.60,1,none,false);",
            "arc(1400,1800,0.50,0.90,s,0.60,0.80,1,none,false);",
        ]
    )
    chart = parse_aff_chart(content, designant_choice=True)
    events = solve_4k(chart, _converter())

    boundary_events = events.get(1400, [])
    assert not any(
        event.source_type == "arc" and event.action.name == "DOWN"
        for event in boundary_events
    )
    assert not any(
        event.source_type == "arc" and event.action.name == "UP"
        for event in boundary_events
    )

    all_arc_events = [
        event
        for items in events.values()
        for event in items
        if event.source_type == "arc"
    ]
    down_count = sum(1 for event in all_arc_events if event.action.name == "DOWN")
    up_count = sum(1 for event in all_arc_events if event.action.name == "UP")
    assert down_count == 1
    assert up_count == 1


def test_connected_same_color_arcs_keep_pointer_without_xy_match() -> None:
    content = "\n".join(
        [
            "AudioOffset:0",
            "Title:connected_same_color_arcs_without_xy_match",
            "",
            "arc(1000,1400,0.10,0.30,s,0.20,0.40,1,none,false);",
            "arc(1400,1800,0.80,0.95,s,0.75,0.90,1,none,false);",
        ]
    )
    chart = parse_aff_chart(content, designant_choice=True)
    events = solve_4k(chart, _converter())

    boundary_events = events.get(1400, [])
    assert not any(
        event.source_type == "arc" and event.action.name == "DOWN"
        for event in boundary_events
    )
    assert not any(
        event.source_type == "arc" and event.action.name == "UP"
        for event in boundary_events
    )

    all_arc_events = [
        event
        for items in events.values()
        for event in items
        if event.source_type == "arc"
    ]
    down_count = sum(1 for event in all_arc_events if event.action.name == "DOWN")
    up_count = sum(1 for event in all_arc_events if event.action.name == "UP")
    assert down_count == 1
    assert up_count == 1


def test_enwidencamera_projects_arc_logical_space_to_screen_space() -> None:
    content = "\n".join(
        [
            "AudioOffset:0",
            "Title:enwidencamera_projection",
            "",
            "scenecontrol(0,enwidencamera,0.00,1);",
            "arc(1000,1000,-1.00,-1.00,s,1.61,1.61,0,none,false);",
            "arc(1200,1200,2.00,2.00,s,1.61,1.61,0,none,false);",
        ]
    )
    chart = parse_aff_chart(content, designant_choice=True)
    logical_events = build_logical_events_for_chart(chart)

    zero_arc_down_events = [
        event
        for event in logical_events
        if event.source_type == "zero_arc" and event.action.name == "DOWN"
    ]
    assert len(zero_arc_down_events) == 2

    first = next(event for event in zero_arc_down_events if event.tick == 1000)
    second = next(event for event in zero_arc_down_events if event.tick == 1200)

    assert first.x == -0.5
    assert first.y == 1.0
    assert second.x == 1.5
    assert second.y == 1.0


def test_enwidencamera_transition_generates_arc_move_for_fixed_logical_x() -> None:
    content = "\n".join(
        [
            "AudioOffset:0",
            "Title:enwidencamera_transition_move",
            "",
            "scenecontrol(1000,enwidencamera,1000.00,1);",
            "arc(1000,2000,0.00,0.00,s,0.50,0.50,1,none,false);",
        ]
    )
    chart = parse_aff_chart(content, designant_choice=True)
    logical_events = build_logical_events_for_chart(chart)

    arc_events = [
        event
        for event in logical_events
        if event.source_type == "arc" and event.action.name != "UP"
    ]
    assert arc_events

    x_by_tick = {event.tick: event.x for event in arc_events}
    assert 1000 in x_by_tick
    assert x_by_tick[1000] == 0.0

    move_events = [event for event in arc_events if event.action.name == "MOVE"]
    assert move_events
    assert any(event.x != x_by_tick[1000] for event in move_events)
