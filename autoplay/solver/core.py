from __future__ import annotations

import math
from dataclasses import dataclass

from algo.algo_base import TouchAction
from autoplay.domain.chart import Arc, Chart, Hold, Tap, TimingGroup
from autoplay.solver.events import TouchEvent


@dataclass(slots=True)
class SolverProfile:
    lane_start: float
    lane_scale: float
    lane_offset: float
    sky_y_scale: float
    arc_x_scale: float
    arc_x_offset: float

    def map_ground_x(self, track: int) -> float:
        return self.lane_start + track * self.lane_scale

    def map_arc_x(self, x: float) -> float:
        return x * self.arc_x_scale + self.arc_x_offset


PROFILE_4K = SolverProfile(
    lane_start=-0.75,
    lane_scale=0.5,
    lane_offset=0.1,
    sky_y_scale=1.0,
    arc_x_scale=1.0,
    arc_x_offset=0.0,
)

PROFILE_6K = SolverProfile(
    lane_start=-0.5 / 1.5,
    lane_scale=0.5 / 1.5,
    lane_offset=0.0,
    sky_y_scale=1.6,
    arc_x_scale=1.0 / 1.36,
    arc_x_offset=(0.5 - 0.5 * (1.0 / 1.36)),
)


def _rotate_point(x: float, y: float, anglex: int, angley: int) -> tuple[float, float]:
    ax = math.radians(anglex / 10)
    ay = math.radians(angley / 10)

    y_rot = y * math.cos(ax) - math.sin(ax)
    z_rot = y * math.sin(ax) + math.cos(ax)
    x_rot = x * math.cos(ay) + z_rot * math.sin(ay)
    return x_rot, y_rot


def _generate_events(chart: Chart, converter, profile: SolverProfile) -> dict[int, list[TouchEvent]]:
    result: dict[int, list[TouchEvent]] = {}
    current_arctap_id = 1000
    arc_search_range = 5
    zero_length_arcs: dict[int, dict] = {}

    def ins(ms: int, ev: TouchEvent) -> None:
        result.setdefault(ms, []).append(ev)

    def process_note(note, group_properties: dict | None = None) -> None:
        nonlocal current_arctap_id

        properties = group_properties or {}
        if properties.get("noinput", False):
            return

        anglex = int(properties.get("anglex", 0))
        angley = int(properties.get("angley", 0))

        if isinstance(note, Arc):
            if note.start == note.end:
                if note.trace_arc:
                    return
                pointer_id = note.color + 5
                zero_length_arcs[note.end] = {
                    "pointer_id": pointer_id,
                    "start_x": profile.map_arc_x(note.start_x),
                    "end_x": profile.map_arc_x(note.end_x),
                    "start_y": note.start_y,
                    "end_y": note.end_y,
                }
                return

            corrected_start_x = profile.map_arc_x(note.start_x)
            corrected_end_x = profile.map_arc_x(note.end_x)

            start_x, start_y = _rotate_point(corrected_start_x, note.start_y, anglex, angley)
            end_x, end_y = _rotate_point(corrected_end_x, note.end_y, anglex, angley)

            start = (start_x, start_y / profile.sky_y_scale, 1)
            end = (end_x, end_y / profile.sky_y_scale, 1)
            delta = note.end - note.start

            if note.trace_arc:
                for tap in note.taps:
                    t = (tap.tick - note.start) / delta
                    px, py, _ = note.easing.value(start, end, t)
                    px, py = converter(px, py)
                    ins(tap.tick, TouchEvent((round(px), round(py)), TouchAction.DOWN, current_arctap_id))
                    ins(tap.tick + 2, TouchEvent((round(px), round(py)), TouchAction.UP, current_arctap_id))
                    current_arctap_id += 1
                    if current_arctap_id > 2000:
                        current_arctap_id = 1000
                return

            pointer_id = note.color + 5
            compensation_needed = False
            compensation_x = 0.0
            compensation_y = 0.0

            if note.start in zero_length_arcs:
                zero_arc_info = zero_length_arcs[note.start]
                if zero_arc_info["pointer_id"] == pointer_id:
                    move_dx = zero_arc_info["end_x"] - zero_arc_info["start_x"]
                    move_dy = zero_arc_info["end_y"] - zero_arc_info["start_y"]
                    compensation_x = -move_dx * 0.1
                    compensation_y = -move_dy * 0.1
                    compensation_needed = True
                    del zero_length_arcs[note.start]

            px, py, _ = note.easing.value(start, end, 0)
            px, py = converter(px, py)
            ins(note.start, TouchEvent((round(px), round(py)), TouchAction.DOWN, pointer_id))

            for tck in range(note.start - arc_search_range, note.start + arc_search_range + 1):
                if tck not in result:
                    continue
                for index, event in enumerate(result[tck]):
                    if event.pointer == pointer_id and event.action == TouchAction.UP:
                        result[tck].pop(index)
                        result[note.start].pop(-1)
                        ins(note.start, TouchEvent((round(px), round(py)), TouchAction.MOVE, pointer_id))
                        break
                else:
                    continue
                break

            if compensation_needed:
                comp_px, comp_py = converter(corrected_start_x + compensation_x, note.start_y + compensation_y)
                ins(note.start + 5, TouchEvent((round(comp_px), round(comp_py)), TouchAction.MOVE, pointer_id))
                ins(note.start + 10, TouchEvent((round(px), round(py)), TouchAction.MOVE, pointer_id))

            for tap in note.taps:
                t = (tap.tick - note.start) / delta
                px, py, _ = note.easing.value(start, end, t)
                px, py = converter(px, py)
                tap_pointer = current_arctap_id
                ins(tap.tick, TouchEvent((round(px), round(py)), TouchAction.DOWN, tap_pointer))
                ins(tap.tick + 10, TouchEvent((round(px), round(py)), TouchAction.UP, tap_pointer))
                current_arctap_id += 1
                if current_arctap_id > 2000:
                    current_arctap_id = 1000

            sample_points: list[int] = []
            min_step = 10
            if delta > 100:
                steps = max(5, delta // 20)
                for idx in range(steps + 1):
                    sample_points.append(note.start + int(idx * delta / steps))
            else:
                steps = max(2, math.ceil(delta / min_step))
                for idx in range(steps + 1):
                    sample_points.append(note.start + int(idx * delta / steps))

            for tick in sample_points:
                t = max(0.0, min(1.0, (tick - note.start) / delta))
                px, py, _ = note.easing.value(start, end, t)
                if anglex != 0 or angley != 0:
                    px, py = _rotate_point(px, py, anglex, angley)
                px, py = converter(px, py)
                if tick != note.start:
                    ins(tick, TouchEvent((round(px), round(py)), TouchAction.MOVE, pointer_id))

            px, py, _ = note.easing.value(start, end, 1)
            px, py = converter(px, py)
            ins(note.end, TouchEvent((round(px), round(py)), TouchAction.UP, pointer_id))

            for tck in range(note.end - arc_search_range, note.end + arc_search_range + 1):
                if tck not in result:
                    continue
                for index, event in enumerate(result[tck]):
                    if event.pointer == pointer_id and event.action == TouchAction.DOWN:
                        result[tck].pop(index)
                        result[note.end].pop(-1)
                        ins(tck, TouchEvent((round(px), round(py)), TouchAction.MOVE, pointer_id))
                        break
                else:
                    continue
                break
            return

        if isinstance(note, Tap):
            note_x = profile.map_ground_x(note.track)
            if profile.lane_offset != 0:
                offset_direction = (note_x - 0.5) / abs(note_x - 0.5)
                note_x -= profile.lane_offset * offset_direction
            px, py = converter(note_x, 0)
            ins(note.tick, TouchEvent((round(px), round(py)), TouchAction.DOWN, note.track))
            ins(note.tick + 20, TouchEvent((round(px), round(py)), TouchAction.UP, note.track))
            return

        if isinstance(note, Hold):
            note_x = profile.map_ground_x(note.track)
            if profile.lane_offset != 0:
                offset_direction = (note_x - 0.5) / abs(note_x - 0.5)
                note_x -= profile.lane_offset * offset_direction
            px, py = converter(note_x, 0)
            hold_pointer = note.track + 100
            ins(note.start, TouchEvent((round(px), round(py)), TouchAction.DOWN, hold_pointer))
            ins(note.end, TouchEvent((round(px), round(py)), TouchAction.UP, hold_pointer))

    def process_timing_group(group: TimingGroup) -> None:
        for item in group.notes:
            if isinstance(item, TimingGroup):
                process_timing_group(item)
            else:
                process_note(item, group.properties)

    for note in chart.notes:
        if isinstance(note, TimingGroup):
            process_timing_group(note)
        else:
            process_note(note)

    return result


def solve_4k(chart: Chart, converter) -> dict[int, list[TouchEvent]]:
    return _generate_events(chart, converter, PROFILE_4K)


def solve_6k(chart: Chart, converter) -> dict[int, list[TouchEvent]]:
    return _generate_events(chart, converter, PROFILE_6K)
