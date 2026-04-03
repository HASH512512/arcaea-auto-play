from __future__ import annotations

import re

from autoplay.domain.chart import Arc, Chart, Hold, Tap, TimingGroup


class ModeAnalyzer:
    """Analyze scenecontrol events and build 4K/6K segments."""

    def __init__(self) -> None:
        self.camera_events: list[tuple[int, float, int]] = []
        self.lanes_events: list[tuple[int, float, int]] = []
        self.max_time = 0

    def analyze_chart_for_6k(self, chart_content: str, chart: Chart | None = None) -> tuple[list[tuple[int, int]], list[tuple[int, int]], int]:
        camera_matches = re.finditer(r"scenecontrol\((\d+),enwidencamera,([\d\.]+),(\d)\);", chart_content)
        lanes_matches = re.finditer(r"scenecontrol\((\d+),enwidenlanes,([\d\.]+),(\d)\);", chart_content)

        self.camera_events = self._extract_events(camera_matches)
        self.lanes_events = self._extract_events(lanes_matches)

        camera_intervals = self._process_events(self.camera_events)
        lanes_intervals = self._process_events(self.lanes_events)

        if chart is not None:
            self.max_time = self._get_max_time(chart)

        return camera_intervals, lanes_intervals, self.max_time

    def _extract_events(self, matches) -> list[tuple[int, float, int]]:
        events = []
        for match in matches:
            events.append((int(match.group(1)), float(match.group(2)), int(match.group(3))))
        return sorted(events, key=lambda item: item[0])

    def _process_events(self, events: list[tuple[int, float, int]]) -> list[tuple[int, int]]:
        intervals: list[tuple[int, int]] = []
        starts = [event for event in events if event[2] == 1]
        ends = [event for event in events if event[2] == 0]

        for index, start in enumerate(starts):
            if index >= len(ends):
                break
            end = ends[index]
            start_time = start[0] + int(start[1] / 2)
            end_time = end[0] + int(end[1] / 2)
            intervals.append((start_time, end_time))

        return intervals

    def create_segments(self, events: list[tuple[int, float, int]]) -> list[tuple[int, int, str]]:
        segments: list[tuple[int, int, str]] = []
        current_mode = "4k"
        current_time = 0

        if not events:
            return [(0, self.max_time, "4k")]

        for time_ms, duration_ms, event_type in events:
            if current_time < time_ms:
                segments.append((current_time, time_ms, current_mode))
                current_time = time_ms

            half_time = time_ms + int(duration_ms / 2)
            if current_time < half_time:
                segments.append((current_time, half_time, current_mode))
                current_time = half_time

            current_mode = "6k" if event_type == 1 else "4k"

        if current_time < self.max_time:
            segments.append((current_time, self.max_time, current_mode))

        return segments

    def get_sky_segments(self) -> list[tuple[int, int, str]]:
        return self.create_segments(self.camera_events)

    def get_ground_segments(self) -> list[tuple[int, int, str]]:
        return self.create_segments(self.lanes_events)

    def collect_notes_by_segments(self, chart: Chart, segments: list[tuple[int, int, str]], note_type: str) -> dict[tuple[int, int, str], list]:
        grouped: dict[tuple[int, int, str], list] = {}

        for segment in segments:
            start, end, _ = segment
            notes_in_segment = []
            for note in chart.notes:
                if isinstance(note, TimingGroup):
                    continue

                if isinstance(note, Arc):
                    note_time = note.start
                    is_allowed = note_type in {"arc", "all"}
                elif isinstance(note, Tap):
                    note_time = note.tick
                    is_allowed = note_type in {"tap", "ground", "all"}
                elif isinstance(note, Hold):
                    note_time = note.start
                    is_allowed = note_type in {"hold", "ground", "all"}
                else:
                    continue

                if is_allowed and start <= note_time <= end:
                    notes_in_segment.append(note)

            grouped[segment] = notes_in_segment

        return grouped

    def split_and_solve_chart(self, chart: Chart, converter, solve_4k, solve_6k) -> dict[int, list]:
        all_events: dict[int, list] = {}

        sky_notes = self.collect_notes_by_segments(chart, self.get_sky_segments(), "arc")
        ground_notes = self.collect_notes_by_segments(chart, self.get_ground_segments(), "ground")

        for segment_map in (sky_notes, ground_notes):
            for (_, _, mode), notes in segment_map.items():
                if not notes:
                    continue
                segment_chart = Chart(notes, chart.options)
                segment_events = solve_6k(segment_chart, converter) if mode == "6k" else solve_4k(segment_chart, converter)
                for time_ms, events in segment_events.items():
                    all_events.setdefault(time_ms, []).extend(events)

        return all_events

    def _get_max_time(self, chart: Chart) -> int:
        max_time = 0

        def walk(notes) -> None:
            nonlocal max_time
            for note in notes:
                if isinstance(note, TimingGroup):
                    walk(note.notes)
                elif isinstance(note, Arc) or isinstance(note, Hold):
                    max_time = max(max_time, note.end)
                elif isinstance(note, Tap):
                    max_time = max(max_time, note.tick)

        walk(chart.notes)
        return max_time
