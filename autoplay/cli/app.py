from __future__ import annotations

import ctypes
import time
from pathlib import Path
from tkinter import Tk
from tkinter.filedialog import askopenfilename


from autoplay.analyzer import ModeAnalyzer
from autoplay.parser import (
    extract_delay_from_aff_content,
    has_designant_notes,
    parse_aff_chart,
)
from autoplay.runtime import (
    prepare_device_controller,
    load_app_config,
    run_touch_events,
    save_app_config,
)
from autoplay.runtime.player import FineTuneState, start_input_listener
from autoplay.solver import CoordConv, solve_chart_auto


TEXT = {
    "en": {
        "title": "Arcaea Auto Play Script v4.0.0",
        "choose_file": "Select AFF Chart File",
        "first_choose": "First use or chart path not configured, please select chart file",
        "no_file": "No file selected, exiting program",
        "chart_set": "Chart path set to: {path}",
        "read_error": "Failed to read chart file: {error}",
        "delay_error": "Error: no valid note times found, cannot determine delay",
        "chart_error": "Chart loading failed: {error}",
        "delay_ok": "Delay adjusted to: {delay} seconds",
        "config_head": "Current Configuration:",
        "config_chart": "Chart Path: {path}",
        "config_step": "Fine-tune Step: {step} milliseconds",
        "has_designant": "Current chart contains notes specific to designant phenomenon",
        "designant_enabled": "Designant touch: execute touch",
        "designant_disabled": "Designant touch: do not execute touch",
        "designant_unset": "Designant touch: not configured",
        "quick_edit": "Quick Parameter Edit:",
        "quick_1": "[1] Edit Coordinates",
        "quick_2": "[2] Chart Path",
        "quick_3": "[3] Fine-tune Settings",
        "quick_4": "[4] Configure designant touch",
        "quick_hint": "Press corresponding number key to edit, other keys to skip...",
        "coord_intro": "Please set four coordinates in order (press Enter to keep current value)",
        "coord_updated": "Coordinates updated",
        "step_prompt": "Enter new fine-tune step (milliseconds, integer): ",
        "step_invalid": "Invalid input, must be positive integer",
        "step_updated": "Fine-tune step updated to: {step} milliseconds",
        "designant_question": "Are you playing designant? (y/n): ",
        "designant_choice_true": "Designant mode enabled",
        "designant_choice_false": "Designant mode disabled, designant notes will be ignored",
        "automation_head": "Fine-tuning control:",
        "automation_plus": "  Press Z: Advance {step} milliseconds",
        "automation_minus": "  Press X: Delay {step} milliseconds",
        "automation_zero": "  Press R: Reset fine-tuning offset",
        "ready": "Ready, press Enter to start...",
        "done": "Execution completed, exiting in 3 seconds...",
        "event_empty": "No touch events generated",
        "unknown_cmd": "[Hint] Unknown command: {cmd}, available commands: z, x, r",
        "fine_plus": "[Fine-tune] Advance {step}ms, current offset: {offset:.3f}s",
        "fine_minus": "[Fine-tune] Delay {step}ms, current offset: {offset:.3f}s",
        "fine_reset": "[Fine-tune] Offset reset: {offset:.3f}s",
    },
    "zh": {
        "title": "Arcaea自动打歌脚本 v4.0.0",
        "choose_file": "选择AFF谱面文件",
        "first_choose": "首次使用或未配置谱面路径，请选择谱面文件",
        "no_file": "未选择文件，程序退出",
        "chart_set": "已设置谱面路径: {path}",
        "read_error": "读取谱面文件失败: {error}",
        "delay_error": "错误：未找到有效音符时间，无法确定延迟",
        "chart_error": "谱面加载失败: {error}",
        "delay_ok": "已调整延迟为: {delay}秒",
        "config_head": "当前配置：",
        "config_chart": "谱面路径：{path}",
        "config_step": "微调延迟：{step}毫秒",
        "has_designant": "当前谱面包含蚂蚁异象(designant)特有note",
        "designant_enabled": "蚂蚁异象触控：执行触控",
        "designant_disabled": "蚂蚁异象触控：不执行触控",
        "designant_unset": "蚂蚁异象触控：尚未配置",
        "quick_edit": "参数快捷编辑：",
        "quick_1": "[1] 编辑坐标",
        "quick_2": "[2] 谱面路径",
        "quick_3": "[3] 微调设置",
        "quick_4": "[4] 配置是否触控蚂蚁异象",
        "quick_hint": "按对应数字键编辑，其他键跳过...",
        "coord_intro": "请按顺序设置四个坐标（按回车保持当前值）",
        "coord_updated": "坐标已更新",
        "step_prompt": "请输入新的微调延迟（毫秒，整数）：",
        "step_invalid": "输入无效，必须为正整数",
        "step_updated": "微调延迟已更新为：{step}毫秒",
        "designant_question": "您是否在游玩蚂蚁异象？(y/n): ",
        "designant_choice_true": "已启用蚂蚁异象模式",
        "designant_choice_false": "已禁用蚂蚁异象模式，将忽略蚂蚁异象note",
        "automation_head": "微调控制:",
        "automation_plus": "  按 Z : 提前{step}毫秒",
        "automation_minus": "  按 X : 延后{step}毫秒",
        "automation_zero": "  按 R : 重置微调偏移",
        "ready": "准备就绪，按回车开始...",
        "done": "执行完毕，3秒后自动退出...",
        "event_empty": "未生成任何触控事件",
        "unknown_cmd": "[提示] 未知命令: {cmd}，可用命令: z, x, r",
        "fine_plus": "[微调] 提前{step}毫秒，当前偏移: {offset:.3f}秒",
        "fine_minus": "[微调] 延后{step}毫秒，当前偏移: {offset:.3f}秒",
        "fine_reset": "[微调] 偏移已重置: {offset:.3f}秒",
    },
}


def _text(locale: str, key: str, **kwargs) -> str:
    return TEXT[locale][key].format(**kwargs)


def _is_console_focused() -> bool:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    return user32.GetForegroundWindow() == kernel32.GetConsoleWindow()


def _focus_console_window() -> None:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    hwnd = kernel32.GetConsoleWindow()
    if hwnd:
        user32.SetForegroundWindow(hwnd)


def _clear_console_input_buffer() -> None:
    kernel32 = ctypes.windll.kernel32
    std_input_handle = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE
    if std_input_handle:
        kernel32.FlushConsoleInputBuffer(std_input_handle)


def _prompt_quick_edit_choice() -> str:
    # Use a non-echo timed key reader so no stray characters are left
    # in the console input line.
    user32 = ctypes.windll.user32
    key_to_option = {
        0x31: "1",  # top-row 1
        0x32: "2",
        0x33: "3",
        0x34: "4",
        0x61: "1",  # numpad 1
        0x62: "2",
        0x63: "3",
        0x64: "4",
    }
    watched = list(key_to_option.keys()) + [0x0D]  # Enter

    # Debounce held keys from previous stages.
    previous_state = {vk: bool(user32.GetAsyncKeyState(vk) & 0x8000) for vk in watched}

    _clear_console_input_buffer()

    start = time.time()
    while time.time() - start < 5.0:
        if not _is_console_focused():
            time.sleep(0.02)
            continue

        for vk in watched:
            is_down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
            was_down = previous_state[vk]
            previous_state[vk] = is_down

            if is_down and not was_down:
                _clear_console_input_buffer()
                if vk == 0x0D:
                    return ""
                return key_to_option[vk]

        time.sleep(0.01)

    _clear_console_input_buffer()
    return ""


def _wait_for_enter_key() -> None:
    # Keep start confirmation scoped to focused console and avoid
    # background global hook behavior.
    user32 = ctypes.windll.user32
    enter_keys = (0x0D,)  # Enter

    previous_state = {
        vk: bool(user32.GetAsyncKeyState(vk) & 0x8000) for vk in enter_keys
    }

    _clear_console_input_buffer()
    while True:
        if not _is_console_focused():
            time.sleep(0.02)
            continue

        vk = 0x0D
        is_down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
        was_down = previous_state[vk]
        previous_state[vk] = is_down

        if is_down and not was_down:
            _clear_console_input_buffer()
            return

        time.sleep(0.01)


def _choose_aff_file(locale: str) -> str:
    root = Tk()
    root.withdraw()
    file_path = askopenfilename(
        title=_text(locale, "choose_file"),
        filetypes=[("Chart files", "*.*")],
    )
    root.destroy()
    return file_path


def _input_coord(prompt: str, default: tuple[int, int]) -> tuple[int, int]:
    while True:
        try:
            _clear_console_input_buffer()
            print(f"{prompt} ({default}): ", end="", flush=True)
            raw = input().strip()
            if not raw:
                return default
            x, y = map(int, raw.replace("，", ",").split(","))
            return x, y
        except (ValueError, IndexError):
            print("Format error")


def _read_chart_file(chart_path: str) -> str:
    with open(chart_path, "r", encoding="utf-8") as handle:
        return handle.read()


def _ensure_designant_choice(
    locale: str, chart_content: str, app_config
) -> bool | None:
    has_designant = has_designant_notes(chart_content)
    if not has_designant:
        return app_config.global_config.designant_choice

    if app_config.global_config.designant_choice is None:
        _clear_console_input_buffer()
        answer = input(_text(locale, "designant_question")).strip().lower()
        app_config.global_config.designant_choice = answer == "y"
        if app_config.global_config.designant_choice:
            print(_text(locale, "designant_choice_true"))
        else:
            print(_text(locale, "designant_choice_false"))
    return app_config.global_config.designant_choice


def _show_config(locale: str, app_config, chart_content: str | None) -> None:
    cfg = app_config.global_config
    print("\n" + _text(locale, "config_head"))
    print(_text(locale, "config_chart", path=cfg.chart_path))
    print(_text(locale, "config_step", step=cfg.fine_tune_step))

    if chart_content is not None and has_designant_notes(chart_content):
        print(_text(locale, "has_designant"))
        if cfg.designant_choice is True:
            print(_text(locale, "designant_enabled"))
        elif cfg.designant_choice is False:
            print(_text(locale, "designant_disabled"))
        else:
            print(_text(locale, "designant_unset"))


def _quick_edit(locale: str, app_config) -> None:
    cfg = app_config.global_config

    chart_content = None
    if cfg.chart_path and Path(cfg.chart_path).exists():
        try:
            chart_content = _read_chart_file(cfg.chart_path)
        except OSError:
            chart_content = None

    has_designant = bool(chart_content and has_designant_notes(chart_content))

    print("\n" + _text(locale, "quick_edit"))
    print(_text(locale, "quick_1"))
    print(_text(locale, "quick_2"))
    print(_text(locale, "quick_3"))
    if has_designant:
        print(_text(locale, "quick_4"))
    print(_text(locale, "quick_hint"))

    _focus_console_window()
    key = _prompt_quick_edit_choice()

    if key == "1":
        print(_text(locale, "coord_intro"))
        cfg.bottom_left = _input_coord("bottom_left", cfg.bottom_left)
        cfg.top_left = _input_coord("top_left", cfg.top_left)
        cfg.top_right = _input_coord("top_right", cfg.top_right)
        cfg.bottom_right = _input_coord("bottom_right", cfg.bottom_right)
        save_app_config(app_config)
        print(_text(locale, "coord_updated"))
    elif key == "2":
        chart_path = _choose_aff_file(locale)
        if chart_path:
            cfg.chart_path = chart_path
            save_app_config(app_config)
            print(_text(locale, "chart_set", path=chart_path))
    elif key == "3":
        _clear_console_input_buffer()
        raw = input(_text(locale, "step_prompt")).strip()
        try:
            step = int(raw)
            if step <= 0:
                raise ValueError
            cfg.fine_tune_step = step
            save_app_config(app_config)
            print(_text(locale, "step_updated", step=step))
        except ValueError:
            print(_text(locale, "step_invalid"))
    elif key == "4" and has_designant:
        if cfg.designant_choice is None:
            _clear_console_input_buffer()
            answer = input(_text(locale, "designant_question")).strip().lower()
            cfg.designant_choice = answer == "y"
        else:
            cfg.designant_choice = not cfg.designant_choice
        save_app_config(app_config)
        print(
            _text(locale, "designant_choice_true")
            if cfg.designant_choice
            else _text(locale, "designant_choice_false")
        )


def _run(locale: str, app_config) -> None:
    cfg = app_config.global_config
    if not cfg.chart_path:
        print(_text(locale, "first_choose"))
        selected = _choose_aff_file(locale)
        if not selected:
            print(_text(locale, "no_file"))
            return
        cfg.chart_path = selected
        save_app_config(app_config)
        print(_text(locale, "chart_set", path=selected))

    _quick_edit(locale, app_config)

    try:
        chart_content = _read_chart_file(cfg.chart_path)
    except (OSError, UnicodeDecodeError) as exc:
        print(_text(locale, "read_error", error=exc))
        return

    designant_choice = _ensure_designant_choice(locale, chart_content, app_config)
    save_app_config(app_config)

    try:
        chart = parse_aff_chart(chart_content, designant_choice=designant_choice)
    except Exception as exc:
        print(_text(locale, "chart_error", error=exc))
        return

    analyzer = ModeAnalyzer()
    analyzer.analyze_chart_for_6k(chart_content, chart)

    delay = extract_delay_from_aff_content(chart_content)
    if delay is None:
        print(_text(locale, "delay_error"))
        return

    app_config.delay = delay
    save_app_config(app_config)
    print(_text(locale, "delay_ok", delay=delay))

    converter = CoordConv(
        cfg.bottom_left, cfg.top_left, cfg.top_right, cfg.bottom_right
    )
    all_events = solve_chart_auto(chart, converter)
    if not all_events:
        print(_text(locale, "event_empty"))
        return

    print("\n" + "=" * 40)
    print(_text(locale, "automation_head"))
    print(_text(locale, "automation_plus", step=cfg.fine_tune_step))
    print(_text(locale, "automation_minus", step=cfg.fine_tune_step))
    print(_text(locale, "automation_zero", step=cfg.fine_tune_step))
    print("=" * 40)
    _show_config(locale, app_config, chart_content)

    state = FineTuneState(cfg.fine_tune_step)

    def on_command(command: str) -> None:
        if command == "z":
            offset = state.increment()
            print(_text(locale, "fine_plus", step=cfg.fine_tune_step, offset=offset))
        elif command == "x":
            offset = state.decrement()
            print(_text(locale, "fine_minus", step=cfg.fine_tune_step, offset=offset))
        elif command == "r":
            offset = state.reset()
            print(_text(locale, "fine_reset", offset=offset))
        elif command:
            print(_text(locale, "unknown_cmd", cmd=command))

    state.input_listener_active = True
    start_input_listener(state, on_command)

    print("\n[INFO] Initializing device control channel...")
    try:
        controller = prepare_device_controller()
    except Exception as exc:
        print(f"[ERROR] Failed to initialize device controller: {exc}")
        state.input_listener_active = False
        return

    print("\n" + _text(locale, "ready"))
    _focus_console_window()
    _wait_for_enter_key()
    run_touch_events(all_events, app_config.delay, state, controller=controller)


def run_cli(locale: str) -> None:
    app_config = load_app_config()
    print("=" * 40)
    print(_text(locale, "title"))
    print("=" * 40)
    _run(locale, app_config)
    print("\n" + _text(locale, "done"))
    time.sleep(3)
