from __future__ import annotations

import threading
import time

from autoplay.cli.app import _normalize_quick_edit_choice


def count_enter_presses_for_quick_edit(inputs: list[str]) -> int | None:
    for idx, raw in enumerate(inputs, start=1):
        if _normalize_quick_edit_choice(raw):
            return idx
    return None


def _parse_fine_tune_command(raw: str) -> str:
    text = raw.strip().lower()
    return text[:1] if text[:1] in {"z", "x", "r"} else ""


def count_enter_presses_for_fine_tune(inputs: list[str], target: str) -> int | None:
    target_normalized = target.strip().lower()[:1]
    if target_normalized not in {"z", "x", "r"}:
        raise ValueError("target must be one of z/x/r")
    for idx, raw in enumerate(inputs, start=1):
        if _parse_fine_tune_command(raw) == target_normalized:
            return idx
    return None


def _drain_commands_with_queue(
    inputs: list[str],
    active_seconds: float = 0.1,
) -> list[str]:
    queue: list[str] = []
    lock = threading.Lock()
    state = {"active": True}

    feed = iter(inputs)

    def stdin_reader() -> None:
        while state["active"]:
            try:
                raw = next(feed)
            except StopIteration:
                break
            cmd = _parse_fine_tune_command(raw)
            if cmd:
                with lock:
                    queue.append(cmd)
            time.sleep(0.001)

    consumed: list[str] = []

    def input_listener() -> None:
        deadline = time.time() + active_seconds
        while time.time() < deadline:
            with lock:
                if queue:
                    consumed.append(queue.pop(0))
            time.sleep(0.001)

    reader = threading.Thread(target=stdin_reader)
    listener = threading.Thread(target=input_listener)
    reader.start()
    listener.start()
    reader.join()
    state["active"] = False
    listener.join()
    return consumed


def test_quick_edit_expected_enter_count() -> None:
    assert count_enter_presses_for_quick_edit(["", "1"]) == 2
    assert count_enter_presses_for_quick_edit(["2"]) == 1
    assert count_enter_presses_for_quick_edit(["abc", "4"]) == 2


def test_fine_tune_expected_enter_count() -> None:
    assert count_enter_presses_for_fine_tune(["", " ", "z"], "z") == 3
    assert count_enter_presses_for_fine_tune(["x"], "x") == 1
    assert count_enter_presses_for_fine_tune(["a", "r"], "r") == 2


def test_fine_tune_queue_drains_first_valid_command() -> None:
    consumed = _drain_commands_with_queue(["", "z", "x"])
    assert consumed
    assert consumed[0] == "z"
