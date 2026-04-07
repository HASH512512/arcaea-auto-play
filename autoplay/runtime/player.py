from __future__ import annotations

import threading
import time
import queue

from control import DeviceController


class FineTuneState:
    def __init__(self, step_ms: int) -> None:
        self.step_ms = step_ms
        self.time_offset = 0.0
        self.time_lock = threading.Lock()
        self.input_listener_active = False
        self.automation_started = False

    def increment(self) -> float:
        with self.time_lock:
            self.time_offset += self.step_ms / 1000.0
            return self.time_offset

    def decrement(self) -> float:
        with self.time_lock:
            self.time_offset -= self.step_ms / 1000.0
            return self.time_offset

    def reset(self) -> float:
        with self.time_lock:
            self.time_offset = 0.0
            return self.time_offset

    def current_offset(self) -> float:
        with self.time_lock:
            return self.time_offset


def _read_hotkey_edges(
    get_async_key_state,
    previous_state: dict[int, bool],
    vk_to_command: dict[int, str],
) -> list[str]:
    commands: list[str] = []
    for vk, command in vk_to_command.items():
        is_down = bool(get_async_key_state(vk) & 0x8000)
        was_down = previous_state[vk]
        previous_state[vk] = is_down
        if is_down and not was_down:
            commands.append(command)
    return commands


def start_input_listener(state: FineTuneState, on_command) -> threading.Thread:
    command_queue: queue.Queue[str] = queue.Queue()

    def stdin_reader() -> None:
        while state.input_listener_active:
            try:
                text = input()
            except (EOFError, KeyboardInterrupt):
                break

            command = text.strip().lower()[:1]
            if command in {"z", "x", "r"}:
                command_queue.put(command)

    def input_listener() -> None:
        while state.input_listener_active:
            try:
                if not state.automation_started:
                    time.sleep(0.1)
                    continue

                try:
                    command = command_queue.get_nowait()
                except queue.Empty:
                    time.sleep(0.01)
                    continue

                on_command(command)
            except (EOFError, KeyboardInterrupt, SystemExit):
                break
            except Exception as exc:
                print(f"[Input listener error] {exc}")
                break

    stdin_thread = threading.Thread(target=stdin_reader, daemon=True)
    stdin_thread.start()

    listener_thread = threading.Thread(target=input_listener, daemon=True)
    listener_thread.start()
    return listener_thread


def prepare_device_controller() -> DeviceController:
    return DeviceController(server_dir=".")


def run_touch_events(
    events_by_time: dict[int, list],
    base_delay: float,
    state: FineTuneState,
    controller: DeviceController | None = None,
) -> None:
    sorted_events = sorted(events_by_time.items())
    if not sorted_events:
        print("[Error] No touch events generated")
        return

    if controller is None:
        controller = prepare_device_controller()
    event_iter = iter(sorted_events)

    try:
        ms, events = next(event_iter)
    except StopIteration:
        print("[Warning] Event sequence terminated unexpectedly")
        return

    state.automation_started = True
    start_time = time.time() + base_delay
    print("[INFO] Auto play started")

    try:
        while state.input_listener_active:
            now = (time.time() - start_time + state.current_offset()) * 1000
            if now >= ms:
                for event in events:
                    x, y = event.pos
                    controller.touch(x, y, event.action, event.pointer)
                try:
                    ms, events = next(event_iter)
                except StopIteration:
                    break
            else:
                time.sleep(0.001)
    except (KeyboardInterrupt, SystemExit):
        print("[INFO] User interrupted execution")
    except Exception as exc:
        print(f"[ERROR] Execution error: {exc}")
    finally:
        state.input_listener_active = False
        state.automation_started = False
