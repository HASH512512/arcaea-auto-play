from __future__ import annotations

from autoplay.runtime.player import _read_hotkey_edges


def test_read_hotkey_edges_triggers_on_key_down_edge() -> None:
    vk_to_command = {0x5A: "z", 0x58: "x", 0x52: "r"}
    previous_state = {vk: False for vk in vk_to_command}

    sequence = {
        0x5A: [0, 0x8000, 0x8000, 0],
        0x58: [0, 0, 0, 0],
        0x52: [0, 0, 0x8000, 0],
    }
    step = {"value": 0}

    def fake_get_async_key_state(vk: int) -> int:
        idx = step["value"]
        return sequence[vk][idx]

    commands_0 = _read_hotkey_edges(
        fake_get_async_key_state, previous_state, vk_to_command
    )
    step["value"] = 1
    commands_1 = _read_hotkey_edges(
        fake_get_async_key_state, previous_state, vk_to_command
    )
    step["value"] = 2
    commands_2 = _read_hotkey_edges(
        fake_get_async_key_state, previous_state, vk_to_command
    )
    step["value"] = 3
    commands_3 = _read_hotkey_edges(
        fake_get_async_key_state, previous_state, vk_to_command
    )

    assert commands_0 == []
    assert commands_1 == ["z"]
    assert commands_2 == ["r"]
    assert commands_3 == []
