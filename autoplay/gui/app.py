from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from PySide6.QtCore import QThread, Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from autoplay.analyzer import ModeAnalyzer
from autoplay.domain.arcaea_ir import ArcIR, HoldIR, TapIR
from autoplay.parser import (
    extract_delay_from_aff_content,
    has_designant_notes,
    parse_aff_chart,
)
from autoplay.runtime import (
    load_app_config,
    prepare_device_controller,
    run_touch_events,
    save_app_config,
)
from autoplay.runtime.player import FineTuneState
from autoplay.solver import CoordConv, solve_chart_auto


LEFT_MIN_WIDTH = 460
RIGHT_MIN_WIDTH = 440
WINDOW_MIN_WIDTH = LEFT_MIN_WIDTH + RIGHT_MIN_WIDTH
WINDOW_MIN_HEIGHT = 600
REF_OPENCV_DIR = Path("ref") / "opencv"


def _imread_unicode(path: Path, flags: int = cv2.IMREAD_COLOR):
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
    except OSError:
        return None
    if data.size == 0:
        return None
    return cv2.imdecode(data, flags)


TEXT = {
    "zh": {
        "window_title": "Arcaea Auto Play GUI",
        "language": "语言",
        "tab_status": "状态",
        "tab_settings": "设置",
        "chart_path": "谱面路径",
        "browse": "浏览",
        "top_left": "左上坐标",
        "top_right": "右上坐标",
        "bottom_left": "左下坐标",
        "bottom_right": "右下坐标",
        "fine_tune_step": "微调步长",
        "designant": "蚂蚁异象触控",
        "unset": "未设置",
        "enabled": "启用",
        "disabled": "禁用",
        "save_config": "保存配置",
        "reload_config": "重载配置",
        "prepare": "预编译谱面",
        "start": "开始",
        "stop": "停止",
        "step_plus": "+步进 (Z)",
        "step_minus": "-步进 (X)",
        "reset": "重置 (R)",
        "run_state": "运行状态",
        "controller": "控制通道",
        "prepare_state": "谱面准备",
        "offset": "微调偏移",
        "delay": "延迟",
        "idle": "空闲",
        "warming": "预热中",
        "ready": "就绪",
        "running": "运行中",
        "error": "错误",
        "summary_current": "当前执行",
        "summary_next": "下一执行",
        "none": "无",
        "select_aff": "选择 AFF 谱面文件",
        "config_error": "配置错误",
        "missing_chart_title": "缺少谱面",
        "missing_chart": "请先选择谱面文件",
        "chart_not_found": "谱面文件不存在: {path}",
        "read_error": "读取谱面失败: {error}",
        "designant_title": "蚂蚁异象",
        "designant_question": "当前谱面包含蚂蚁异象 note，是否启用触控？",
        "controller_not_ready": "控制通道尚未就绪，请等待预热完成。",
        "prepare_not_ready": "谱面尚未准备完成，请先点击“预编译谱面”或等待自动准备。",
        "prepare_mismatch": "设置已变更，正在重新预编译。请等待准备完成后再开始。",
        "log_warm_start": "[信息] 正在预热 ADB/scrcpy 通道...",
        "log_warm_ok": "[信息] ADB/scrcpy 预热完成",
        "log_warm_fail": "[错误] ADB/scrcpy 预热失败: {error}",
        "log_prepare_start": "[信息] 开始预编译谱面...",
        "log_prepare_ok": "[信息] 预编译完成，事件组数={count}，delay={delay:.3f}s",
        "log_prepare_fail": "[错误] 预编译失败: {error}",
        "log_config_saved": "[信息] 配置已保存",
        "log_play_start": "[信息] 播放任务已启动",
        "log_play_finish": "[信息] 播放完成",
        "log_stop": "[信息] 已请求停止",
        "detail_curr_note": "当前 Note 详情",
        "detail_curr_event": "当前 TouchEvent 详情",
        "detail_next_note": "下一 Note 详情",
        "detail_next_event": "下一 TouchEvent 详情",
        "log_clear": "清除日志",
        "log_limit": "日志最大条数",
        "debug_verbose": "输出详细调度日志",
        "debug_verbose_hint": "开启后会输出调度器装载、每次事件派发的延迟(lateness)以及首发延迟统计。",
        "opt_high_prio": "播放线程高优先级",
        "auto_start_cv": "视觉自动开始",
        "auto_start_hint": "自动识别是否进入可交互界面，并在首个 tap/hold 接近判定线时自动触发开始。",
        "auto_start_wait": "[信息] 视觉自动开始：等待游戏界面...",
        "auto_start_ready": "[信息] 已检测到游戏界面，等待首个地面 note 进入判定。",
        "auto_start_fire": "[信息] 自动开始条件满足，已触发播放",
        "auto_start_arc_todo": "[信息] 首 note 为 arc/arctap，仅完成第一层识别，第二层触发规则待下一轮实现。",
    },
    "en": {
        "window_title": "Arcaea Auto Play GUI",
        "language": "Language",
        "tab_status": "Status",
        "tab_settings": "Settings",
        "chart_path": "Chart Path",
        "browse": "Browse",
        "top_left": "top_left",
        "top_right": "top_right",
        "bottom_left": "bottom_left",
        "bottom_right": "bottom_right",
        "fine_tune_step": "Fine-tune Step",
        "designant": "Designant Touch",
        "unset": "Unset",
        "enabled": "Enabled",
        "disabled": "Disabled",
        "save_config": "Save Config",
        "reload_config": "Reload Config",
        "prepare": "Prepare Chart",
        "start": "Start",
        "stop": "Stop",
        "step_plus": "+step (Z)",
        "step_minus": "-step (X)",
        "reset": "Reset (R)",
        "run_state": "Run State",
        "controller": "Controller",
        "prepare_state": "Chart Ready",
        "offset": "Fine Offset",
        "delay": "Delay",
        "idle": "Idle",
        "warming": "Warming",
        "ready": "Ready",
        "running": "Running",
        "error": "Error",
        "summary_current": "Current",
        "summary_next": "Next",
        "none": "None",
        "select_aff": "Select AFF Chart File",
        "config_error": "Config Error",
        "missing_chart_title": "Missing Chart",
        "missing_chart": "Please select a chart file first",
        "chart_not_found": "Chart file not found: {path}",
        "read_error": "Failed to read chart: {error}",
        "designant_title": "Designant",
        "designant_question": "Current chart contains designant notes. Enable designant touch?",
        "controller_not_ready": "Controller is not ready yet. Wait until warmup is complete.",
        "prepare_not_ready": "Chart data is not prepared yet. Click Prepare Chart first or wait for auto preparation.",
        "prepare_mismatch": "Settings changed, re-preparing chart now. Start again after preparation completes.",
        "log_warm_start": "[INFO] Preheating ADB/scrcpy channel...",
        "log_warm_ok": "[INFO] ADB/scrcpy preheat completed",
        "log_warm_fail": "[ERROR] ADB/scrcpy preheat failed: {error}",
        "log_prepare_start": "[INFO] Preparing chart pipeline...",
        "log_prepare_ok": "[INFO] Prepare completed, groups={count}, delay={delay:.3f}s",
        "log_prepare_fail": "[ERROR] Prepare failed: {error}",
        "log_config_saved": "[INFO] Config saved",
        "log_play_start": "[INFO] Playback task started",
        "log_play_finish": "[INFO] Playback finished",
        "log_stop": "[INFO] Stop requested",
        "detail_curr_note": "Current Note Detail",
        "detail_curr_event": "Current TouchEvent Detail",
        "detail_next_note": "Next Note Detail",
        "detail_next_event": "Next TouchEvent Detail",
        "log_clear": "Clear Logs",
        "log_limit": "Log Max Entries",
        "debug_verbose": "Verbose scheduler debug logs",
        "debug_verbose_hint": "When enabled, outputs scheduler arm info, per-dispatch lateness, and start-to-first-dispatch latency.",
        "opt_high_prio": "High thread priority",
        "auto_start_cv": "Vision auto start",
        "auto_start_hint": "Automatically detects gameplay screen and starts when first tap/hold nears judgment line.",
        "auto_start_wait": "[INFO] Vision auto-start: waiting gameplay screen...",
        "auto_start_ready": "[INFO] Gameplay screen detected, waiting first ground note timing...",
        "auto_start_fire": "[INFO] Auto-start condition met, playback triggered",
        "auto_start_arc_todo": "[INFO] First note is arc/arctap; only stage-1 is active now. Stage-2 trigger will be finalized next round.",
    },
}


@dataclass(slots=True)
class RunConfig:
    chart_path: str
    bottom_left: tuple[int, int]
    top_left: tuple[int, int]
    top_right: tuple[int, int]
    bottom_right: tuple[int, int]
    fine_tune_step: int
    designant_choice: bool | None


@dataclass(slots=True)
class PreparedRunData:
    config_key: str
    run_config: RunConfig
    delay: float
    events_by_time: dict[int, list]
    note_meta: dict[int, dict[str, object]]
    first_ground_tick: int | None
    first_note_types: tuple[str, ...]


@dataclass(slots=True)
class VisionMetrics:
    panel_struct_score: float = 0.0
    panel_digit_count: int = 0
    panel_template_score: float = 0.0
    panel_pass: bool = False
    line_present: bool = False
    note_ratio: float = 0.0
    ground_pass: bool = False
    arc_cap_score: float = 0.0
    arc_pass: bool = False


def _coord_to_text(coord: tuple[int, int]) -> str:
    return f"{coord[0]},{coord[1]}"


def _parse_coord(text: str, label: str) -> tuple[int, int]:
    parts = text.strip().replace("，", ",").split(",")
    if len(parts) != 2:
        raise ValueError(f"{label} format must be x,y")
    return int(parts[0].strip()), int(parts[1].strip())


def _build_config_key(cfg: RunConfig) -> str:
    return "|".join(
        [
            cfg.chart_path,
            str(cfg.top_left),
            str(cfg.top_right),
            str(cfg.bottom_left),
            str(cfg.bottom_right),
            str(cfg.designant_choice),
        ]
    )


def _build_note_meta(chart) -> dict[int, dict[str, object]]:
    result: dict[int, dict[str, object]] = {}
    chart_ir = chart.ir
    if chart_ir is None:
        return result
    for note in chart_ir.notes:
        if isinstance(note, TapIR):
            result[note.note_id] = {
                "type": "tap",
                "tick": note.tick,
                "start": (note.lane, 0.0),
                "end": (note.lane, 0.0),
            }
        elif isinstance(note, HoldIR):
            result[note.note_id] = {
                "type": "hold",
                "tick": note.start,
                "start": (note.lane, 0.0),
                "end": (note.lane, 0.0),
                "end_tick": note.end,
            }
        elif isinstance(note, ArcIR):
            result[note.note_id] = {
                "type": "arc" if not note.trace_arc else "trace_arc",
                "tick": note.start,
                "start": (note.start_x, note.start_y),
                "end": (note.end_x, note.end_y),
                "end_tick": note.end,
            }
    return result


class CollapsibleSection(QWidget):
    def __init__(self, title: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.button = QToolButton()
        self.button.setText(title)
        self.button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.button.setArrowType(Qt.RightArrow)
        self.button.setCheckable(True)
        self.button.toggled.connect(self._toggle)

        self.content = QTextEdit()
        self.content.setReadOnly(True)
        self.content.setVisible(False)
        self.content.setMinimumHeight(88)

        layout.addWidget(self.button)
        layout.addWidget(self.content)

    def _toggle(self, checked: bool) -> None:
        self.button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self.content.setVisible(checked)

    def set_title(self, title: str) -> None:
        self.button.setText(title)

    def set_text(self, text: str) -> None:
        self.content.setPlainText(text)


class ControllerWarmupWorker(QThread):
    started_warmup = Signal()
    warmup_ok = Signal(object)
    warmup_fail = Signal(str)

    def __init__(self, max_fps: int, max_size: int) -> None:
        super().__init__()
        self.max_fps = max_fps
        self.max_size = max_size

    def run(self) -> None:
        self.started_warmup.emit()
        try:
            controller = prepare_device_controller(
                max_fps=self.max_fps,
                max_size=self.max_size,
            )
        except Exception as exc:
            self.warmup_fail.emit(str(exc))
            return
        self.warmup_ok.emit(controller)


class PrepareWorker(QThread):
    started_prepare = Signal()
    prepared_ok = Signal(object)
    prepared_fail = Signal(str)

    def __init__(self, run_config: RunConfig) -> None:
        super().__init__()
        self.run_config = run_config

    def run(self) -> None:
        self.started_prepare.emit()
        cfg = self.run_config
        try:
            chart_content = Path(cfg.chart_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            self.prepared_fail.emit(f"read_error:{exc}")
            return

        try:
            chart = parse_aff_chart(
                chart_content, designant_choice=cfg.designant_choice
            )
        except Exception as exc:
            self.prepared_fail.emit(f"parse_error:{exc}")
            return

        analyzer = ModeAnalyzer()
        analyzer.analyze_chart_for_6k(chart_content, chart)

        delay = extract_delay_from_aff_content(chart_content)
        if delay is None:
            self.prepared_fail.emit("delay_error")
            return

        converter = CoordConv(
            cfg.bottom_left, cfg.top_left, cfg.top_right, cfg.bottom_right
        )
        events = solve_chart_auto(chart, converter)
        if not events:
            self.prepared_fail.emit("event_error")
            return

        first_ground_tick: int | None = None
        first_tick = min(events.keys())
        first_types = {str(event.source_type) for event in events[first_tick]}
        for tick in sorted(events.keys()):
            for event in events[tick]:
                if event.source_type in {"tap", "hold"}:
                    first_ground_tick = tick
                    break
            if first_ground_tick is not None:
                break

        payload = PreparedRunData(
            config_key=_build_config_key(cfg),
            run_config=cfg,
            delay=delay,
            events_by_time=events,
            note_meta=_build_note_meta(chart),
            first_ground_tick=first_ground_tick,
            first_note_types=tuple(sorted(first_types)),
        )
        self.prepared_ok.emit(payload)


class PlaybackWorker(QThread):
    log_message = Signal(str)
    started_playback = Signal()
    finished_playback = Signal(bool, str)
    progress = Signal(object)

    def __init__(
        self,
        prepared: PreparedRunData,
        controller,
        debug_verbose: bool,
        optimize_high_priority: bool,
        optimize_timer_resolution: bool,
    ) -> None:
        super().__init__()
        self.prepared = prepared
        self.controller = controller
        self.debug_verbose = debug_verbose
        self.optimize_high_priority = optimize_high_priority
        self.optimize_timer_resolution = optimize_timer_resolution
        self.state: FineTuneState | None = None

    def current_offset(self) -> float:
        if self.state is None:
            return 0.0
        return self.state.current_offset()

    def nudge_plus(self) -> None:
        if self.state is None:
            return
        offset = self.state.increment()
        self.log_message.emit(
            f"[Fine-tune] Advance {self.prepared.run_config.fine_tune_step}ms, current offset: {offset:.3f}s"
        )

    def nudge_minus(self) -> None:
        if self.state is None:
            return
        offset = self.state.decrement()
        self.log_message.emit(
            f"[Fine-tune] Delay {self.prepared.run_config.fine_tune_step}ms, current offset: {offset:.3f}s"
        )

    def reset_offset(self) -> None:
        if self.state is None:
            return
        offset = self.state.reset()
        self.log_message.emit(f"[Fine-tune] Offset reset: {offset:.3f}s")

    def stop_playback(self) -> None:
        if self.state is not None:
            self.state.input_listener_active = False

    def _on_progress(
        self,
        curr_tick: int,
        curr_events: list,
        next_tick: int | None,
        next_events: list | None,
    ) -> None:
        curr_event = curr_events[0] if curr_events else None
        next_event = next_events[0] if next_events else None
        self.progress.emit(
            {
                "curr_tick": curr_tick,
                "curr_event": curr_event,
                "next_tick": next_tick,
                "next_event": next_event,
                "curr_size": len(curr_events),
                "next_size": len(next_events or []),
                "note_meta": self.prepared.note_meta,
            }
        )

    def run(self) -> None:
        self.state = FineTuneState(self.prepared.run_config.fine_tune_step)
        self.state.input_listener_active = True
        self.started_playback.emit()

        run_touch_events(
            self.prepared.events_by_time,
            self.prepared.delay,
            self.state,
            controller=self.controller,
            log=self.log_message.emit,
            on_progress=self._on_progress,
            debug=self.debug_verbose,
            optimize_high_priority=self.optimize_high_priority,
            optimize_timer_resolution=self.optimize_timer_resolution,
        )
        self.finished_playback.emit(True, "ok")


class AutoPlayWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.locale = "zh"
        self.app_config = load_app_config()

        self.controller = None
        self.controller_ready = False
        self.prepared: PreparedRunData | None = None

        self.worker: PlaybackWorker | None = None
        self.prepare_worker: PrepareWorker | None = None
        self.warmup_worker: ControllerWarmupWorker | None = None

        self.log_lines: list[str] = []
        self.log_limit = 500
        self._start_click_time: float | None = None
        self._first_dispatch_logged = False
        self._ui_right_templates = self._load_score_panel_templates()
        self._arc_cap_template = self._load_arc_cap_template()
        self._vision_metrics = VisionMetrics()
        self.stream_max_fps = 60
        self.stream_max_size = 960

        self._build_ui()
        self._load_config_to_form()
        self._apply_texts()

        self.offset_timer = QTimer(self)
        self.offset_timer.setInterval(80)
        self.offset_timer.timeout.connect(self._refresh_offset)

        self.auto_start_timer = QTimer(self)
        self.auto_start_timer.setInterval(16)
        self.auto_start_timer.timeout.connect(self._poll_auto_start)
        self._auto_start_stage = "idle"

        self._start_warmup()
        self._request_prepare(auto=True)

    def _t(self, key: str, **kwargs) -> str:
        return TEXT[self.locale][key].format(**kwargs)

    def _build_ui(self) -> None:
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(1360, 840)

        root = QWidget(self)
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)

        splitter = QSplitter(Qt.Horizontal)
        root_layout.addWidget(splitter)

        left = QWidget()
        left.setMinimumWidth(LEFT_MIN_WIDTH)
        left_layout = QVBoxLayout(left)

        top_row = QHBoxLayout()
        self.language_label = QLabel()
        self.language_combo = QComboBox()
        self.language_combo.addItem("中文", "zh")
        self.language_combo.addItem("English", "en")
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        top_row.addStretch()
        top_row.addWidget(self.language_label)
        top_row.addWidget(self.language_combo)
        left_layout.addLayout(top_row)

        self.tabs = QTabWidget()
        self.status_page = QWidget()
        self.settings_page = QWidget()
        self.tabs.addTab(self.status_page, "")
        self.tabs.addTab(self.settings_page, "")
        left_layout.addWidget(self.tabs)

        self._build_status_page()
        self._build_settings_page()

        self.control_group = QGroupBox()
        control_layout = QGridLayout(self.control_group)
        self.start_btn = QPushButton()
        self.stop_btn = QPushButton()
        self.plus_btn = QPushButton()
        self.minus_btn = QPushButton()
        self.reset_btn = QPushButton()

        self.plus_btn.setShortcut("Z")
        self.minus_btn.setShortcut("X")
        self.reset_btn.setShortcut("R")

        self.start_btn.clicked.connect(self._start_playback)
        self.stop_btn.clicked.connect(self._stop_playback)
        self.plus_btn.clicked.connect(self._fine_tune_plus)
        self.minus_btn.clicked.connect(self._fine_tune_minus)
        self.reset_btn.clicked.connect(self._fine_tune_reset)

        control_layout.addWidget(self.start_btn, 0, 0)
        control_layout.addWidget(self.stop_btn, 0, 1)
        control_layout.addWidget(self.plus_btn, 1, 0)
        control_layout.addWidget(self.minus_btn, 1, 1)
        control_layout.addWidget(self.reset_btn, 1, 2)
        left_layout.addWidget(self.control_group)

        right = QWidget()
        right.setMinimumWidth(RIGHT_MIN_WIDTH)
        right_layout = QVBoxLayout(right)
        log_top = QHBoxLayout()
        log_top.addStretch()
        self.clear_log_btn = QPushButton()
        self.clear_log_btn.clicked.connect(self._clear_logs)
        log_top.addWidget(self.clear_log_btn)
        right_layout.addLayout(log_top)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        right_layout.addWidget(self.log_output)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self._set_running_ui(False)

    def _build_status_page(self) -> None:
        layout = QVBoxLayout(self.status_page)

        summary_group = QGroupBox()
        summary_form = QFormLayout(summary_group)
        self.run_state_key = QLabel()
        self.controller_key = QLabel()
        self.prepare_key = QLabel()
        self.offset_key = QLabel()
        self.delay_key = QLabel()

        self.run_state_label = QLabel()
        self.controller_state_label = QLabel()
        self.prepare_state_label = QLabel()
        self.offset_label = QLabel("0.000s")
        self.delay_label = QLabel(f"{self.app_config.delay:.3f}s")
        summary_form.addRow(self.run_state_key, self.run_state_label)
        summary_form.addRow(self.controller_key, self.controller_state_label)
        summary_form.addRow(self.prepare_key, self.prepare_state_label)
        summary_form.addRow(self.offset_key, self.offset_label)
        summary_form.addRow(self.delay_key, self.delay_label)

        monitor_group = QGroupBox()
        monitor_layout = QVBoxLayout(monitor_group)
        self.curr_title = QLabel()
        self.curr_line1 = QLabel("-")
        self.curr_line2 = QLabel("-")
        self.next_title = QLabel()
        self.next_line1 = QLabel("-")
        self.next_line2 = QLabel("-")

        monitor_layout.addWidget(self.curr_title)
        monitor_layout.addWidget(self.curr_line1)
        monitor_layout.addWidget(self.curr_line2)
        monitor_layout.addSpacing(8)
        monitor_layout.addWidget(self.next_title)
        monitor_layout.addWidget(self.next_line1)
        monitor_layout.addWidget(self.next_line2)

        self.curr_note_detail = CollapsibleSection("")
        self.curr_event_detail = CollapsibleSection("")
        self.next_note_detail = CollapsibleSection("")
        self.next_event_detail = CollapsibleSection("")
        monitor_layout.addWidget(self.curr_note_detail)
        monitor_layout.addWidget(self.curr_event_detail)
        monitor_layout.addWidget(self.next_note_detail)
        monitor_layout.addWidget(self.next_event_detail)

        layout.addWidget(summary_group)
        layout.addWidget(monitor_group)
        layout.addStretch()

    def _build_settings_page(self) -> None:
        layout = QVBoxLayout(self.settings_page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        group = QGroupBox()
        form = QFormLayout(group)

        chart_row = QHBoxLayout()
        self.chart_path_edit = QLineEdit()
        self.browse_btn = QPushButton()
        self.browse_btn.clicked.connect(self._choose_chart_file)
        chart_row.addWidget(self.chart_path_edit)
        chart_row.addWidget(self.browse_btn)
        chart_widget = QWidget()
        chart_widget.setLayout(chart_row)

        self.chart_path_label = QLabel()
        form.addRow(self.chart_path_label, chart_widget)

        coord_group = QGroupBox()
        coord_grid = QGridLayout(coord_group)
        self.top_left_label = QLabel()
        self.top_right_label = QLabel()
        self.bottom_left_label = QLabel()
        self.bottom_right_label = QLabel()
        self.top_left_edit = QLineEdit()
        self.top_right_edit = QLineEdit()
        self.bottom_left_edit = QLineEdit()
        self.bottom_right_edit = QLineEdit()

        coord_grid.addWidget(self.top_left_label, 0, 0)
        coord_grid.addWidget(self.top_left_edit, 0, 1)
        coord_grid.addWidget(self.top_right_label, 0, 2)
        coord_grid.addWidget(self.top_right_edit, 0, 3)
        coord_grid.addWidget(self.bottom_left_label, 1, 0)
        coord_grid.addWidget(self.bottom_left_edit, 1, 1)
        coord_grid.addWidget(self.bottom_right_label, 1, 2)
        coord_grid.addWidget(self.bottom_right_edit, 1, 3)
        form.addRow(coord_group)

        mixed_row = QHBoxLayout()
        self.fine_tune_label = QLabel()
        self.step_spin = QSpinBox()
        self.step_spin.setRange(1, 1000)
        self.step_spin.setSuffix(" ms")
        self.designant_label = QLabel()
        self.designant_combo = QComboBox()
        self.designant_combo.addItems(["", "", ""])
        mixed_row.addWidget(self.fine_tune_label)
        mixed_row.addWidget(self.step_spin)
        mixed_row.addSpacing(20)
        mixed_row.addWidget(self.designant_label)
        mixed_row.addWidget(self.designant_combo)
        mixed_widget = QWidget()
        mixed_widget.setLayout(mixed_row)
        form.addRow(mixed_widget)

        action_row = QHBoxLayout()
        self.save_btn = QPushButton()
        self.reload_btn = QPushButton()
        self.prepare_btn = QPushButton()
        self.stream_fps_label = QLabel("Stream FPS")
        self.stream_fps_spin = QSpinBox()
        self.stream_fps_spin.setRange(30, 120)
        self.stream_fps_spin.setValue(self.stream_max_fps)
        self.stream_size_label = QLabel("Stream max_size")
        self.stream_size_spin = QSpinBox()
        self.stream_size_spin.setRange(640, 1440)
        self.stream_size_spin.setSingleStep(80)
        self.stream_size_spin.setValue(self.stream_max_size)
        self.log_limit_label = QLabel()
        self.log_limit_spin = QSpinBox()
        self.log_limit_spin.setRange(50, 5000)
        self.log_limit_spin.setValue(self.log_limit)

        self.save_btn.clicked.connect(self._on_save_clicked)
        self.reload_btn.clicked.connect(self._on_reload_clicked)
        self.prepare_btn.clicked.connect(lambda: self._request_prepare(auto=False))

        action_row.addWidget(self.save_btn)
        action_row.addWidget(self.reload_btn)
        action_row.addWidget(self.prepare_btn)
        action_row.addWidget(self.stream_fps_label)
        action_row.addWidget(self.stream_fps_spin)
        action_row.addWidget(self.stream_size_label)
        action_row.addWidget(self.stream_size_spin)
        action_row.addWidget(self.log_limit_label)
        action_row.addWidget(self.log_limit_spin)
        action_widget = QWidget()
        action_widget.setLayout(action_row)
        form.addRow(action_widget)

        self.debug_verbose_label = QLabel()
        self.debug_verbose_combo = QComboBox()
        self.debug_verbose_combo.addItem("OFF", False)
        self.debug_verbose_combo.addItem("ON", True)
        self.debug_verbose_hint = QLabel()
        self.debug_verbose_hint.setWordWrap(True)
        debug_row = QHBoxLayout()
        debug_row.addWidget(self.debug_verbose_label)
        debug_row.addWidget(self.debug_verbose_combo)
        debug_widget = QWidget()
        debug_widget.setLayout(debug_row)
        form.addRow(debug_widget)
        form.addRow(self.debug_verbose_hint)

        self.opt_high_prio_check = QCheckBox()
        self.opt_high_prio_check.setChecked(False)
        self.auto_start_cv_check = QCheckBox()
        self.auto_start_cv_check.setChecked(False)
        self.auto_start_cv_check.toggled.connect(self._on_auto_start_toggled)
        opt_row = QHBoxLayout()
        opt_row.addWidget(self.opt_high_prio_check)
        opt_row.addWidget(self.auto_start_cv_check)
        opt_widget = QWidget()
        opt_widget.setLayout(opt_row)
        form.addRow(opt_widget)

        self.auto_start_hint = QLabel()
        self.auto_start_hint.setWordWrap(True)
        form.addRow(self.auto_start_hint)

        self.ui_template_threshold_label = QLabel("UI template threshold")
        self.ui_template_threshold_spin = QDoubleSpinBox()
        self.ui_template_threshold_spin.setRange(0.10, 0.95)
        self.ui_template_threshold_spin.setSingleStep(0.01)
        self.ui_template_threshold_spin.setValue(0.42)

        self.ui_digit_count_label = QLabel("UI digit min count")
        self.ui_digit_count_spin = QSpinBox()
        self.ui_digit_count_spin.setRange(1, 20)
        self.ui_digit_count_spin.setValue(7)

        self.ground_note_ratio_label = QLabel("Ground note ratio")
        self.ground_note_ratio_spin = QDoubleSpinBox()
        self.ground_note_ratio_spin.setRange(0.005, 0.50)
        self.ground_note_ratio_spin.setSingleStep(0.005)
        self.ground_note_ratio_spin.setValue(0.045)

        self.arc_cap_threshold_label = QLabel("Arc cap threshold")
        self.arc_cap_threshold_spin = QDoubleSpinBox()
        self.arc_cap_threshold_spin.setRange(0.10, 0.95)
        self.arc_cap_threshold_spin.setSingleStep(0.01)
        self.arc_cap_threshold_spin.setValue(0.44)

        self.overlay_debug_check = QCheckBox("Vision overlay")
        self.overlay_debug_check.setChecked(False)
        self.overlay_detach_check = QCheckBox("Detach overlay window")
        self.overlay_detach_check.setChecked(True)
        self.overlay_detach_check.toggled.connect(self._on_overlay_detach_toggled)
        self.overlay_preview_label = QLabel("preview")
        self.overlay_preview_label.setMinimumSize(300, 170)
        self.overlay_preview_label.setStyleSheet("background:#111; color:#bbb;")
        self.overlay_preview_label.setAlignment(Qt.AlignCenter)

        self.overlay_window = QWidget(None)
        self.overlay_window.setWindowFlag(Qt.Window, True)
        self.overlay_window.setWindowTitle("Vision Overlay")
        overlay_layout = QVBoxLayout(self.overlay_window)
        self.overlay_window_label = QLabel("preview")
        self.overlay_window_label.setMinimumSize(720, 420)
        self.overlay_window_label.setStyleSheet("background:#000; color:#bbb;")
        self.overlay_window_label.setAlignment(Qt.AlignCenter)
        overlay_layout.addWidget(self.overlay_window_label)
        self.overlay_window.resize(920, 560)
        self.overlay_window.hide()

        self.ui_x0_spin = QDoubleSpinBox()
        self.ui_y0_spin = QDoubleSpinBox()
        self.ui_x1_spin = QDoubleSpinBox()
        self.ui_y1_spin = QDoubleSpinBox()
        self.ground_x0_spin = QDoubleSpinBox()
        self.ground_y0_spin = QDoubleSpinBox()
        self.ground_x1_spin = QDoubleSpinBox()
        self.ground_y1_spin = QDoubleSpinBox()
        self.arc_x0_spin = QDoubleSpinBox()
        self.arc_y0_spin = QDoubleSpinBox()
        self.arc_x1_spin = QDoubleSpinBox()
        self.arc_y1_spin = QDoubleSpinBox()

        for spin in (
            self.ui_x0_spin,
            self.ui_y0_spin,
            self.ui_x1_spin,
            self.ui_y1_spin,
            self.ground_x0_spin,
            self.ground_y0_spin,
            self.ground_x1_spin,
            self.ground_y1_spin,
            self.arc_x0_spin,
            self.arc_y0_spin,
            self.arc_x1_spin,
            self.arc_y1_spin,
        ):
            spin.setRange(0.0, 1.0)
            spin.setSingleStep(0.005)
            spin.setDecimals(3)

        self.ui_x0_spin.setValue(0.66)
        self.ui_y0_spin.setValue(0.02)
        self.ui_x1_spin.setValue(0.995)
        self.ui_y1_spin.setValue(0.20)

        self.ground_x0_spin.setValue(0.12)
        self.ground_y0_spin.setValue(1310 / 1440)
        self.ground_x1_spin.setValue(0.88)
        self.ground_y1_spin.setValue(1345 / 1440)

        self.arc_x0_spin.setValue(0.18)
        self.arc_y0_spin.setValue(0.22)
        self.arc_x1_spin.setValue(0.82)
        self.arc_y1_spin.setValue(0.80)

        roi_group = QGroupBox("ROI")
        roi_grid = QGridLayout(roi_group)
        roi_grid.addWidget(QLabel("UI x0,y0,x1,y1"), 0, 0)
        roi_grid.addWidget(self.ui_x0_spin, 0, 1)
        roi_grid.addWidget(self.ui_y0_spin, 0, 2)
        roi_grid.addWidget(self.ui_x1_spin, 0, 3)
        roi_grid.addWidget(self.ui_y1_spin, 0, 4)

        roi_grid.addWidget(QLabel("Ground x0,y0,x1,y1"), 1, 0)
        roi_grid.addWidget(self.ground_x0_spin, 1, 1)
        roi_grid.addWidget(self.ground_y0_spin, 1, 2)
        roi_grid.addWidget(self.ground_x1_spin, 1, 3)
        roi_grid.addWidget(self.ground_y1_spin, 1, 4)

        roi_grid.addWidget(QLabel("Arc x0,y0,x1,y1"), 2, 0)
        roi_grid.addWidget(self.arc_x0_spin, 2, 1)
        roi_grid.addWidget(self.arc_y0_spin, 2, 2)
        roi_grid.addWidget(self.arc_x1_spin, 2, 3)
        roi_grid.addWidget(self.arc_y1_spin, 2, 4)

        self.roi_values_label = QLabel("roi_values")
        self.roi_values_label.setWordWrap(True)

        form.addRow(self.ui_template_threshold_label, self.ui_template_threshold_spin)
        form.addRow(self.ui_digit_count_label, self.ui_digit_count_spin)
        form.addRow(self.ground_note_ratio_label, self.ground_note_ratio_spin)
        form.addRow(self.arc_cap_threshold_label, self.arc_cap_threshold_spin)
        form.addRow(self.overlay_debug_check)
        form.addRow(self.overlay_detach_check)
        form.addRow(self.overlay_preview_label)
        form.addRow(roi_group)
        form.addRow(self.roi_values_label)

        scroll_layout.addWidget(group)
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def _apply_texts(self) -> None:
        self.setWindowTitle(self._t("window_title"))
        self.language_label.setText(self._t("language"))
        self.tabs.setTabText(0, self._t("tab_status"))
        self.tabs.setTabText(1, self._t("tab_settings"))

        self.control_group.setTitle("")

        self.run_state_key.setText(self._t("run_state"))
        self.controller_key.setText(self._t("controller"))
        self.prepare_key.setText(self._t("prepare_state"))
        self.offset_key.setText(self._t("offset"))
        self.delay_key.setText(self._t("delay"))

        self.curr_title.setText(self._t("summary_current"))
        self.next_title.setText(self._t("summary_next"))
        self.curr_note_detail.set_title(self._t("detail_curr_note"))
        self.curr_event_detail.set_title(self._t("detail_curr_event"))
        self.next_note_detail.set_title(self._t("detail_next_note"))
        self.next_event_detail.set_title(self._t("detail_next_event"))

        self.start_btn.setText(self._t("start"))
        self.stop_btn.setText(self._t("stop"))
        self.plus_btn.setText(self._t("step_plus"))
        self.minus_btn.setText(self._t("step_minus"))
        self.reset_btn.setText(self._t("reset"))

        self.chart_path_label.setText(self._t("chart_path"))
        self.browse_btn.setText(self._t("browse"))
        self.top_left_label.setText(self._t("top_left"))
        self.top_right_label.setText(self._t("top_right"))
        self.bottom_left_label.setText(self._t("bottom_left"))
        self.bottom_right_label.setText(self._t("bottom_right"))
        self.fine_tune_label.setText(self._t("fine_tune_step"))
        self.designant_label.setText(self._t("designant"))
        self.designant_combo.setItemText(0, self._t("unset"))
        self.designant_combo.setItemText(1, self._t("enabled"))
        self.designant_combo.setItemText(2, self._t("disabled"))
        self.save_btn.setText(self._t("save_config"))
        self.reload_btn.setText(self._t("reload_config"))
        self.prepare_btn.setText(self._t("prepare"))

        self.clear_log_btn.setText(self._t("log_clear"))
        self.stream_fps_label.setText("Stream FPS")
        self.stream_size_label.setText("Stream max_size")
        self.log_limit_label.setText(self._t("log_limit"))
        self.debug_verbose_label.setText(self._t("debug_verbose"))
        self.debug_verbose_hint.setText(self._t("debug_verbose_hint"))
        self.opt_high_prio_check.setText(self._t("opt_high_prio"))
        self.auto_start_cv_check.setText(self._t("auto_start_cv"))
        self.auto_start_hint.setText(self._t("auto_start_hint"))
        self.ui_template_threshold_label.setText("UI template threshold")
        self.ui_digit_count_label.setText("UI digit min count")
        self.ground_note_ratio_label.setText("Ground note ratio")
        self.arc_cap_threshold_label.setText("Arc cap threshold")
        self.overlay_detach_check.setText("Detach overlay window")

        self.run_state_label.setText(self._t("idle"))
        self.controller_state_label.setText(
            self._t("ready") if self.controller_ready else self._t("warming")
        )
        self.prepare_state_label.setText(
            self._t("ready") if self.prepared is not None else self._t("warming")
        )

    def _append_log(self, text: str) -> None:
        self.log_limit = (
            int(self.log_limit_spin.value())
            if hasattr(self, "log_limit_spin")
            else self.log_limit
        )
        self.log_lines.append(text)
        if len(self.log_lines) > self.log_limit:
            overflow = len(self.log_lines) - self.log_limit
            self.log_lines = self.log_lines[overflow:]
        self.log_output.setPlainText("\n".join(self.log_lines))
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )

    def _clear_logs(self) -> None:
        self.log_lines.clear()
        self.log_output.clear()

    def _format_note(
        self, event, note_meta: dict[int, dict[str, object]]
    ) -> tuple[str, str, str]:
        if event is None:
            return self._t("none"), self._t("none"), self._t("none")
        source_note_id = getattr(event, "source_note_id", None)
        meta = (
            note_meta.get(source_note_id, {}) if isinstance(source_note_id, int) else {}
        )
        note_type = meta.get("type", getattr(event, "source_type", "unknown"))
        tick = meta.get("tick", getattr(event, "logical_tick", "?"))
        line1 = f"note_type={note_type}; note_tick={tick}"
        line2 = (
            f"note_start={meta.get('start', 'n/a')}; note_end={meta.get('end', 'n/a')}"
        )
        detail = "\n".join(
            [
                f"note_id: {source_note_id}",
                f"note_type: {note_type}",
                f"tick: {tick}",
                f"start_coord: {meta.get('start', 'n/a')}",
                f"end_coord: {meta.get('end', 'n/a')}",
                f"end_tick: {meta.get('end_tick', 'n/a')}",
            ]
        )
        return line1, line2, detail

    def _format_event(
        self, event, tick: int | None, group_size: int
    ) -> tuple[str, str, str]:
        if event is None:
            return self._t("none"), self._t("none"), self._t("none")
        line1 = f"event_tick={tick}; event_pointer={event.pointer}; event_action={event.action.name}"
        line2 = f"event_position={event.pos}; event_group_size={group_size}"
        detail = "\n".join(
            [
                f"tick: {tick}",
                f"pointer: {event.pointer}",
                f"action: {event.action.name}",
                f"position: {event.pos}",
                f"logical_tick: {event.logical_tick}",
                f"logical_pos: {event.logical_pos}",
                f"source_note_id: {event.source_note_id}",
                f"source_type: {event.source_type}",
            ]
        )
        return line1, line2, detail

    def _on_progress(self, payload: dict) -> None:
        if not self._first_dispatch_logged and self._start_click_time is not None:
            elapsed_ms = (time.perf_counter() - self._start_click_time) * 1000
            self._append_log(
                f"[DEBUG] Start->first dispatch latency: {elapsed_ms:.2f}ms"
            )
            self._first_dispatch_logged = True

        note_meta = payload.get("note_meta", {})
        curr_event = payload.get("curr_event")
        next_event = payload.get("next_event")

        curr_note_l1, curr_note_l2, curr_note_detail = self._format_note(
            curr_event, note_meta
        )
        curr_evt_l1, curr_evt_l2, curr_evt_detail = self._format_event(
            curr_event,
            payload.get("curr_tick"),
            payload.get("curr_size", 0),
        )
        next_note_l1, next_note_l2, next_note_detail = self._format_note(
            next_event, note_meta
        )
        next_evt_l1, next_evt_l2, next_evt_detail = self._format_event(
            next_event,
            payload.get("next_tick"),
            payload.get("next_size", 0),
        )

        self.curr_line1.setText(curr_note_l1)
        self.curr_line2.setText(curr_evt_l1)
        self.next_line1.setText(next_note_l1)
        self.next_line2.setText(next_evt_l1)

        self.curr_note_detail.set_text(curr_note_detail + "\n" + curr_note_l2)
        self.curr_event_detail.set_text(curr_evt_detail)
        self.next_note_detail.set_text(next_note_detail + "\n" + next_note_l2)
        self.next_event_detail.set_text(next_evt_detail)

    def _load_score_panel_templates(self) -> list[np.ndarray]:
        templates: list[np.ndarray] = []
        for name in ("uiright.png", "uiright_2.png"):
            path = REF_OPENCV_DIR / name
            img = _imread_unicode(path, cv2.IMREAD_COLOR)
            if img is not None:
                templates.append(img)
        return templates

    def _load_arc_cap_template(self) -> np.ndarray | None:
        path = REF_OPENCV_DIR / "Playfield" / "Note" / "arc_cap.png"
        return _imread_unicode(path, cv2.IMREAD_UNCHANGED)

    def _template_match_max(
        self,
        image: np.ndarray,
        template: np.ndarray,
        scales: tuple[float, ...],
        method: int = cv2.TM_CCOEFF_NORMED,
    ) -> float:
        best = -1.0
        ih, iw = image.shape[:2]
        for scale in scales:
            resized = cv2.resize(
                template, None, fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR
            )
            th, tw = resized.shape[:2]
            if th < 8 or tw < 8 or th >= ih or tw >= iw:
                continue
            result = cv2.matchTemplate(image, resized, method)
            _, max_val, _, _ = cv2.minMaxLoc(result)
            if max_val > best:
                best = max_val
        return best

    def _shape_match_score(self, image: np.ndarray, template: np.ndarray) -> float:
        img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        tpl_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        img_edge = cv2.Canny(img_gray, 60, 160)
        tpl_edge = cv2.Canny(tpl_gray, 60, 160)

        img_cnts, _ = cv2.findContours(
            img_edge, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        tpl_cnts, _ = cv2.findContours(
            tpl_edge, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not img_cnts or not tpl_cnts:
            return 0.0

        img_big = max(img_cnts, key=cv2.contourArea)
        tpl_big = max(tpl_cnts, key=cv2.contourArea)
        dist = cv2.matchShapes(img_big, tpl_big, cv2.CONTOURS_MATCH_I1, 0.0)
        return max(0.0, 1.0 - min(1.0, float(dist)))

    def _color_hist_score(self, image: np.ndarray, template: np.ndarray) -> float:
        img_hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        tpl_hsv = cv2.cvtColor(template, cv2.COLOR_BGR2HSV)
        h_bins = 30
        s_bins = 32
        img_hist = cv2.calcHist(
            [img_hsv], [0, 1], None, [h_bins, s_bins], [0, 180, 0, 256]
        )
        tpl_hist = cv2.calcHist(
            [tpl_hsv], [0, 1], None, [h_bins, s_bins], [0, 180, 0, 256]
        )
        cv2.normalize(img_hist, img_hist)
        cv2.normalize(tpl_hist, tpl_hist)
        score = cv2.compareHist(img_hist, tpl_hist, cv2.HISTCMP_CORREL)
        return max(0.0, min(1.0, float((score + 1.0) * 0.5)))

    def _roi_from_spin(
        self, frame: np.ndarray, x0_spin, y0_spin, x1_spin, y1_spin
    ) -> tuple[int, int, int, int]:
        h, w = frame.shape[:2]
        x0 = int(w * float(x0_spin.value()))
        y0 = int(h * float(y0_spin.value()))
        x1 = int(w * float(x1_spin.value()))
        y1 = int(h * float(y1_spin.value()))
        x0, x1 = sorted((max(0, x0), min(w, x1)))
        y0, y1 = sorted((max(0, y0), min(h, y1)))
        return x0, y0, x1, y1

    def _is_gameplay_screen(self, frame: np.ndarray) -> bool:
        x0, y0, x1, y1 = self._roi_from_spin(
            frame,
            self.ui_x0_spin,
            self.ui_y0_spin,
            self.ui_x1_spin,
            self.ui_y1_spin,
        )
        roi = frame[y0:y1, x0:x1]
        if roi.size == 0:
            return False

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 60, 140)
        contours, _ = cv2.findContours(
            edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        pentagon_like = False
        pentagon_score = 0.0
        for contour in contours:
            peri = cv2.arcLength(contour, True)
            if peri < 80:
                continue
            approx = cv2.approxPolyDP(contour, 0.03 * peri, True)
            if len(approx) in {5, 6}:
                area = cv2.contourArea(contour)
                if area > (roi.shape[0] * roi.shape[1] * 0.015):
                    pentagon_like = True
                    pentagon_score = max(
                        pentagon_score, float(area) / float(roi.shape[0] * roi.shape[1])
                    )
                    break

        _, bin_digits = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)
        digit_contours, _ = cv2.findContours(
            bin_digits, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        digit_like_count = 0
        for contour in digit_contours:
            x, y, cw, ch = cv2.boundingRect(contour)
            if ch < roi.shape[0] * 0.20 or ch > roi.shape[0] * 0.92:
                continue
            if cw < 3 or cw > roi.shape[1] * 0.20:
                continue
            ratio = cw / float(ch)
            if 0.15 <= ratio <= 0.85:
                digit_like_count += 1

        min_digits = int(self.ui_digit_count_spin.value())
        if not (pentagon_like and digit_like_count >= min_digits):
            self._vision_metrics.panel_struct_score = pentagon_score
            self._vision_metrics.panel_digit_count = digit_like_count
            self._vision_metrics.panel_template_score = 0.0
            self._vision_metrics.panel_pass = False
            return False

        if not self._ui_right_templates:
            self._vision_metrics.panel_struct_score = pentagon_score
            self._vision_metrics.panel_digit_count = digit_like_count
            self._vision_metrics.panel_template_score = 0.0
            self._vision_metrics.panel_pass = True
            return True
        roi_bgr = roi
        scales = (0.7, 0.8, 0.9, 1.0, 1.1, 1.2)
        template_scores: list[float] = []
        shape_scores: list[float] = []
        color_scores: list[float] = []
        for tpl in self._ui_right_templates:
            template_scores.append(self._template_match_max(roi_bgr, tpl, scales))
            shape_scores.append(self._shape_match_score(roi_bgr, tpl))
            resized_tpl = cv2.resize(
                tpl,
                (roi_bgr.shape[1], roi_bgr.shape[0]),
                interpolation=cv2.INTER_LINEAR,
            )
            color_scores.append(self._color_hist_score(roi_bgr, resized_tpl))

        best_tpl = max(template_scores) if template_scores else 0.0
        best_shape = max(shape_scores) if shape_scores else 0.0
        best_color = max(color_scores) if color_scores else 0.0
        fused = 0.60 * best_tpl + 0.25 * best_shape + 0.15 * best_color

        passed = fused >= float(self.ui_template_threshold_spin.value())
        self._vision_metrics.panel_struct_score = pentagon_score
        self._vision_metrics.panel_digit_count = digit_like_count
        self._vision_metrics.panel_template_score = fused
        self._vision_metrics.panel_pass = passed
        return passed

    def _is_first_ground_note_on_judgment(self, frame: np.ndarray) -> bool:
        if self.prepared is None or self.prepared.first_ground_tick is None:
            return False
        x0, y0, x1, y1 = self._roi_from_spin(
            frame,
            self.ground_x0_spin,
            self.ground_y0_spin,
            self.ground_x1_spin,
            self.ground_y1_spin,
        )
        roi = frame[y0:y1, x0:x1]
        if roi.size == 0:
            return False

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        edge = cv2.Canny(blur, 50, 150)
        lines = cv2.HoughLinesP(
            edge,
            1,
            np.pi / 180,
            threshold=45,
            minLineLength=int(roi.shape[1] * 0.55),
            maxLineGap=12,
        )
        has_judgment_line = lines is not None and len(lines) >= 1

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        sat = hsv[:, :, 1]
        val = hsv[:, :, 2]
        note_mask = (sat > 85) & (val > 105)
        note_ratio = float(note_mask.sum()) / float(note_mask.size)

        passed = has_judgment_line and note_ratio > float(
            self.ground_note_ratio_spin.value()
        )
        self._vision_metrics.line_present = bool(has_judgment_line)
        self._vision_metrics.note_ratio = note_ratio
        self._vision_metrics.ground_pass = passed
        return passed

    def _is_arc_cap_triggered(self, frame: np.ndarray) -> bool:
        if self._arc_cap_template is None:
            return False

        x0, y0, x1, y1 = self._roi_from_spin(
            frame,
            self.arc_x0_spin,
            self.arc_y0_spin,
            self.arc_x1_spin,
            self.arc_y1_spin,
        )
        roi = frame[y0:y1, x0:x1]
        if roi.size == 0:
            return False

        if self._arc_cap_template.ndim == 3 and self._arc_cap_template.shape[2] == 4:
            bgr = self._arc_cap_template[:, :, :3]
            alpha = self._arc_cap_template[:, :, 3]
            mask = (alpha > 20).astype(np.uint8) * 255
            cap_template = cv2.bitwise_and(bgr, bgr, mask=mask)
        else:
            cap_template = self._arc_cap_template

        score = self._template_match_max(
            roi,
            cap_template,
            scales=(0.45, 0.55, 0.65, 0.75, 0.9, 1.0, 1.15),
        )
        shape_score = self._shape_match_score(
            roi,
            cv2.resize(
                cap_template,
                (roi.shape[1], roi.shape[0]),
                interpolation=cv2.INTER_LINEAR,
            ),
        )
        color_score = self._color_hist_score(
            roi,
            cv2.resize(
                cap_template,
                (roi.shape[1], roi.shape[0]),
                interpolation=cv2.INTER_LINEAR,
            ),
        )
        fused = 0.65 * score + 0.20 * shape_score + 0.15 * color_score
        passed = fused >= float(self.arc_cap_threshold_spin.value())
        self._vision_metrics.arc_cap_score = fused
        self._vision_metrics.arc_pass = passed
        return passed

    def _update_overlay_preview(self, frame: np.ndarray) -> None:
        if not self.overlay_debug_check.isChecked():
            self.overlay_window.hide()
            return

        overlay = frame.copy()
        h, w = overlay.shape[:2]
        ui_rect = self._roi_from_spin(
            frame,
            self.ui_x0_spin,
            self.ui_y0_spin,
            self.ui_x1_spin,
            self.ui_y1_spin,
        )
        gd_rect = self._roi_from_spin(
            frame,
            self.ground_x0_spin,
            self.ground_y0_spin,
            self.ground_x1_spin,
            self.ground_y1_spin,
        )
        arc_rect = self._roi_from_spin(
            frame,
            self.arc_x0_spin,
            self.arc_y0_spin,
            self.arc_x1_spin,
            self.arc_y1_spin,
        )

        cv2.rectangle(
            overlay,
            (ui_rect[0], ui_rect[1]),
            (ui_rect[2], ui_rect[3]),
            (0, 220, 255),
            2,
        )
        cv2.rectangle(
            overlay,
            (gd_rect[0], gd_rect[1]),
            (gd_rect[2], gd_rect[3]),
            (80, 255, 80),
            2,
        )
        cv2.rectangle(
            overlay,
            (arc_rect[0], arc_rect[1]),
            (arc_rect[2], arc_rect[3]),
            (255, 120, 80),
            2,
        )

        lines = [
            f"stage={self._auto_start_stage}",
            f"decode_fps={self.controller.get_decode_fps():.1f}"
            if self.controller is not None
            else "decode_fps=n/a",
            f"ui pass={self._vision_metrics.panel_pass} struct={self._vision_metrics.panel_struct_score:.3f} digits={self._vision_metrics.panel_digit_count} tpl={self._vision_metrics.panel_template_score:.3f}",
            f"ground pass={self._vision_metrics.ground_pass} line={self._vision_metrics.line_present} ratio={self._vision_metrics.note_ratio:.3f}",
            f"arc pass={self._vision_metrics.arc_pass} cap={self._vision_metrics.arc_cap_score:.3f}",
        ]
        y = 28
        for line in lines:
            cv2.putText(
                overlay,
                line,
                (18, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (30, 250, 255),
                2,
                cv2.LINE_AA,
            )
            y += 24

        rgb = cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)
        qimg = QImage(
            rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format_RGB888
        )
        pix = QPixmap.fromImage(qimg).scaled(
            self.overlay_preview_label.width(),
            self.overlay_preview_label.height(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        self.overlay_preview_label.setPixmap(pix)

        self.roi_values_label.setText(
            "UI=({:.3f},{:.3f},{:.3f},{:.3f}) Ground=({:.3f},{:.3f},{:.3f},{:.3f}) Arc=({:.3f},{:.3f},{:.3f},{:.3f})".format(
                float(self.ui_x0_spin.value()),
                float(self.ui_y0_spin.value()),
                float(self.ui_x1_spin.value()),
                float(self.ui_y1_spin.value()),
                float(self.ground_x0_spin.value()),
                float(self.ground_y0_spin.value()),
                float(self.ground_x1_spin.value()),
                float(self.ground_y1_spin.value()),
                float(self.arc_x0_spin.value()),
                float(self.arc_y0_spin.value()),
                float(self.arc_x1_spin.value()),
                float(self.arc_y1_spin.value()),
            )
        )

        if self.overlay_detach_check.isChecked():
            self.overlay_window.show()
            pix2 = QPixmap.fromImage(qimg).scaled(
                self.overlay_window_label.width(),
                self.overlay_window_label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.overlay_window_label.setPixmap(pix2)
        else:
            self.overlay_window.hide()

    def _on_overlay_detach_toggled(self, checked: bool) -> None:
        if not checked:
            self.overlay_window.hide()

    def _poll_auto_start(self) -> None:
        if not self.auto_start_cv_check.isChecked():
            self.auto_start_timer.stop()
            self._auto_start_stage = "idle"
            return
        if self.worker is not None and self.worker.isRunning():
            self.auto_start_timer.stop()
            self._auto_start_stage = "idle"
            return
        if self.controller is None or self.prepared is None:
            return

        frame = self.controller.get_latest_frame(copy_frame=True)
        if frame is None:
            return

        self._update_overlay_preview(frame)

        if self._auto_start_stage == "idle":
            self._append_log(self._t("auto_start_wait"))
            self._auto_start_stage = "wait_ui"

        if self._auto_start_stage == "wait_ui":
            if self._is_gameplay_screen(frame):
                if self.prepared is not None:
                    first_types = set(self.prepared.first_note_types)
                    if first_types and first_types.issubset(
                        {"arc", "arctap", "zero_arc"}
                    ):
                        self._append_log(self._t("auto_start_ready"))
                        self._auto_start_stage = "wait_arc_cap"
                        return
                self._append_log(self._t("auto_start_ready"))
                self._auto_start_stage = "wait_note"
            return

        if self._auto_start_stage == "wait_arc_cap" and self._is_arc_cap_triggered(
            frame
        ):
            self._append_log(self._t("auto_start_fire"))
            self.auto_start_timer.stop()
            self._auto_start_stage = "idle"
            self._start_playback()
            return

        if (
            self._auto_start_stage == "wait_note"
            and self._is_first_ground_note_on_judgment(frame)
        ):
            self._append_log(self._t("auto_start_fire"))
            self.auto_start_timer.stop()
            self._auto_start_stage = "idle"
            self._start_playback()

    def _on_auto_start_toggled(self, checked: bool) -> None:
        if not checked:
            self.auto_start_timer.stop()
            self._auto_start_stage = "idle"
            return
        if (
            self.controller_ready
            and self.prepared is not None
            and not self.auto_start_timer.isActive()
        ):
            self.auto_start_timer.start()

    def _on_language_changed(self) -> None:
        self.locale = self.language_combo.currentData()
        self._apply_texts()

    def _choose_chart_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, self._t("select_aff"), "", "All Files (*.*)"
        )
        if file_path:
            self.chart_path_edit.setText(file_path)
            self._on_save_clicked()

    def _load_config_to_form(self) -> None:
        self.app_config = load_app_config()
        cfg = self.app_config.global_config
        vision = self.app_config.vision
        self.chart_path_edit.setText(cfg.chart_path)
        self.top_left_edit.setText(_coord_to_text(cfg.top_left))
        self.top_right_edit.setText(_coord_to_text(cfg.top_right))
        self.bottom_left_edit.setText(_coord_to_text(cfg.bottom_left))
        self.bottom_right_edit.setText(_coord_to_text(cfg.bottom_right))
        self.step_spin.setValue(cfg.fine_tune_step)
        if cfg.designant_choice is None:
            self.designant_combo.setCurrentIndex(0)
        elif cfg.designant_choice:
            self.designant_combo.setCurrentIndex(1)
        else:
            self.designant_combo.setCurrentIndex(2)
        self.delay_label.setText(f"{self.app_config.delay:.3f}s")

        self.stream_max_fps = int(vision.stream_max_fps)
        self.stream_max_size = int(vision.stream_max_size)
        self.stream_fps_spin.setValue(self.stream_max_fps)
        self.stream_size_spin.setValue(self.stream_max_size)
        self.ui_template_threshold_spin.setValue(float(vision.ui_template_threshold))
        self.ui_digit_count_spin.setValue(int(vision.ui_digit_min_count))
        self.ground_note_ratio_spin.setValue(float(vision.ground_note_ratio))
        self.arc_cap_threshold_spin.setValue(float(vision.arc_cap_threshold))
        self.overlay_detach_check.setChecked(bool(vision.overlay_detached))

        self.ui_x0_spin.setValue(float(vision.ui_roi[0]))
        self.ui_y0_spin.setValue(float(vision.ui_roi[1]))
        self.ui_x1_spin.setValue(float(vision.ui_roi[2]))
        self.ui_y1_spin.setValue(float(vision.ui_roi[3]))
        self.ground_x0_spin.setValue(float(vision.ground_roi[0]))
        self.ground_y0_spin.setValue(float(vision.ground_roi[1]))
        self.ground_x1_spin.setValue(float(vision.ground_roi[2]))
        self.ground_y1_spin.setValue(float(vision.ground_roi[3]))
        self.arc_x0_spin.setValue(float(vision.arc_roi[0]))
        self.arc_y0_spin.setValue(float(vision.arc_roi[1]))
        self.arc_x1_spin.setValue(float(vision.arc_roi[2]))
        self.arc_y1_spin.setValue(float(vision.arc_roi[3]))

    def _save_form_to_config(self) -> bool:
        cfg = self.app_config.global_config
        vision = self.app_config.vision
        try:
            cfg.chart_path = self.chart_path_edit.text().strip()
            cfg.top_left = _parse_coord(self.top_left_edit.text(), "top_left")
            cfg.top_right = _parse_coord(self.top_right_edit.text(), "top_right")
            cfg.bottom_left = _parse_coord(self.bottom_left_edit.text(), "bottom_left")
            cfg.bottom_right = _parse_coord(
                self.bottom_right_edit.text(), "bottom_right"
            )
            cfg.fine_tune_step = int(self.step_spin.value())

            vision.stream_max_fps = int(self.stream_fps_spin.value())
            vision.stream_max_size = int(self.stream_size_spin.value())
            vision.ui_template_threshold = float(
                self.ui_template_threshold_spin.value()
            )
            vision.ui_digit_min_count = int(self.ui_digit_count_spin.value())
            vision.ground_note_ratio = float(self.ground_note_ratio_spin.value())
            vision.arc_cap_threshold = float(self.arc_cap_threshold_spin.value())
            vision.overlay_detached = bool(self.overlay_detach_check.isChecked())
            vision.ui_roi = (
                float(self.ui_x0_spin.value()),
                float(self.ui_y0_spin.value()),
                float(self.ui_x1_spin.value()),
                float(self.ui_y1_spin.value()),
            )
            vision.ground_roi = (
                float(self.ground_x0_spin.value()),
                float(self.ground_y0_spin.value()),
                float(self.ground_x1_spin.value()),
                float(self.ground_y1_spin.value()),
            )
            vision.arc_roi = (
                float(self.arc_x0_spin.value()),
                float(self.arc_y0_spin.value()),
                float(self.arc_x1_spin.value()),
                float(self.arc_y1_spin.value()),
            )
        except ValueError as exc:
            QMessageBox.critical(self, self._t("config_error"), str(exc))
            return False

        cfg.designant_choice = {0: None, 1: True, 2: False}[
            self.designant_combo.currentIndex()
        ]
        save_app_config(self.app_config)
        self._append_log(self._t("log_config_saved"))
        return True

    def _collect_run_config(self) -> RunConfig | None:
        if not self._save_form_to_config():
            return None
        cfg = self.app_config.global_config
        chart_path = cfg.chart_path.strip()
        if not chart_path:
            QMessageBox.warning(
                self, self._t("missing_chart_title"), self._t("missing_chart")
            )
            return None
        if not Path(chart_path).exists():
            QMessageBox.warning(
                self,
                self._t("missing_chart_title"),
                self._t("chart_not_found", path=chart_path),
            )
            return None

        try:
            chart_content = Path(chart_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            QMessageBox.critical(
                self, self._t("config_error"), self._t("read_error", error=exc)
            )
            return None

        designant_choice = cfg.designant_choice
        if has_designant_notes(chart_content) and designant_choice is None:
            answer = QMessageBox.question(
                self,
                self._t("designant_title"),
                self._t("designant_question"),
                QMessageBox.Yes | QMessageBox.No,
            )
            designant_choice = answer == QMessageBox.Yes
            cfg.designant_choice = designant_choice
            save_app_config(self.app_config)

        return RunConfig(
            chart_path=chart_path,
            bottom_left=cfg.bottom_left,
            top_left=cfg.top_left,
            top_right=cfg.top_right,
            bottom_right=cfg.bottom_right,
            fine_tune_step=cfg.fine_tune_step,
            designant_choice=designant_choice,
        )

    def _collect_form_config_fast(self) -> RunConfig | None:
        try:
            chart_path = self.chart_path_edit.text().strip()
            top_left = _parse_coord(self.top_left_edit.text(), "top_left")
            top_right = _parse_coord(self.top_right_edit.text(), "top_right")
            bottom_left = _parse_coord(self.bottom_left_edit.text(), "bottom_left")
            bottom_right = _parse_coord(self.bottom_right_edit.text(), "bottom_right")
            step = int(self.step_spin.value())
        except ValueError as exc:
            QMessageBox.critical(self, self._t("config_error"), str(exc))
            return None
        designant_choice = {0: None, 1: True, 2: False}[
            self.designant_combo.currentIndex()
        ]
        return RunConfig(
            chart_path=chart_path,
            bottom_left=bottom_left,
            top_left=top_left,
            top_right=top_right,
            bottom_right=bottom_right,
            fine_tune_step=step,
            designant_choice=designant_choice,
        )

    def _start_warmup(self) -> None:
        self.warmup_worker = ControllerWarmupWorker(
            max_fps=self.stream_max_fps,
            max_size=self.stream_max_size,
        )
        self.warmup_worker.started_warmup.connect(self._on_warmup_start)
        self.warmup_worker.warmup_ok.connect(self._on_warmup_ok)
        self.warmup_worker.warmup_fail.connect(self._on_warmup_fail)
        self.warmup_worker.start()

    def _request_prepare(self, auto: bool) -> None:
        run_config = self._collect_run_config()
        if run_config is None:
            self.prepare_state_label.setText(self._t("error"))
            return

        self.prepare_worker = PrepareWorker(run_config)
        self.prepare_worker.started_prepare.connect(self._on_prepare_start)
        self.prepare_worker.prepared_ok.connect(self._on_prepare_ok)
        self.prepare_worker.prepared_fail.connect(self._on_prepare_fail)
        if not auto:
            self._append_log(self._t("log_prepare_start"))
        self.prepare_worker.start()

    def _on_save_clicked(self) -> None:
        old_fps = self.stream_max_fps
        old_size = self.stream_max_size
        new_fps = int(self.stream_fps_spin.value())
        new_size = int(self.stream_size_spin.value())

        self.stream_max_fps = new_fps
        self.stream_max_size = new_size

        if (old_fps, old_size) != (self.stream_max_fps, self.stream_max_size):
            self._append_log(
                f"[INFO] Restarting scrcpy stream with max_fps={self.stream_max_fps}, max_size={self.stream_max_size}"
            )
            if self.controller is not None:
                try:
                    self.controller.close()
                except Exception:
                    pass
            self.controller = None
            self.controller_ready = False
            self._start_warmup()

        if self._save_form_to_config():
            self._request_prepare(auto=False)

    def _on_reload_clicked(self) -> None:
        self._load_config_to_form()
        self._request_prepare(auto=False)

    def _set_running_ui(self, running: bool) -> None:
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.plus_btn.setEnabled(running)
        self.minus_btn.setEnabled(running)
        self.reset_btn.setEnabled(running)

    def _refresh_offset(self) -> None:
        if self.worker is None:
            self.offset_label.setText("0.000s")
            return
        self.offset_label.setText(f"{self.worker.current_offset():.3f}s")

    def _start_playback(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        if not self.controller_ready or self.controller is None:
            QMessageBox.warning(self, self._t("error"), self._t("controller_not_ready"))
            return

        current_cfg = self._collect_form_config_fast()
        if current_cfg is None:
            return
        if self.prepared is None:
            QMessageBox.warning(self, self._t("error"), self._t("prepare_not_ready"))
            return
        if self.prepared.config_key != _build_config_key(current_cfg):
            self._request_prepare(auto=False)
            QMessageBox.information(self, self._t("error"), self._t("prepare_mismatch"))
            return

        self.worker = PlaybackWorker(
            self.prepared,
            self.controller,
            debug_verbose=bool(self.debug_verbose_combo.currentData()),
            optimize_high_priority=self.opt_high_prio_check.isChecked(),
            optimize_timer_resolution=False,
        )
        self.worker.log_message.connect(self._append_log)
        self.worker.started_playback.connect(self._on_play_started)
        self.worker.finished_playback.connect(self._on_play_finished)
        self.worker.progress.connect(self._on_progress)

        self._append_log(self._t("log_play_start"))
        self._start_click_time = time.perf_counter()
        self._first_dispatch_logged = False
        self.worker.start()

    def _stop_playback(self) -> None:
        if self.worker is None:
            return
        self._append_log(self._t("log_stop"))
        self.worker.stop_playback()

    def _fine_tune_plus(self) -> None:
        if self.worker is not None:
            self.worker.nudge_plus()

    def _fine_tune_minus(self) -> None:
        if self.worker is not None:
            self.worker.nudge_minus()

    def _fine_tune_reset(self) -> None:
        if self.worker is not None:
            self.worker.reset_offset()

    def _on_play_started(self) -> None:
        self.run_state_label.setText(self._t("running"))
        self._set_running_ui(True)
        self.offset_timer.start()

    def _on_play_finished(self, success: bool, _token: str) -> None:
        self.offset_timer.stop()
        self._set_running_ui(False)
        self.run_state_label.setText(self._t("idle") if success else self._t("error"))
        if success:
            self._append_log(self._t("log_play_finish"))

    def _on_warmup_start(self) -> None:
        self.controller_state_label.setText(self._t("warming"))
        self._append_log(self._t("log_warm_start"))

    def _on_warmup_ok(self, controller) -> None:
        self.controller = controller
        self.controller_ready = True
        self.controller_state_label.setText(self._t("ready"))
        self._append_log(self._t("log_warm_ok"))

    def _on_warmup_fail(self, error: str) -> None:
        self.controller = None
        self.controller_ready = False
        self.controller_state_label.setText(self._t("error"))
        self._append_log(self._t("log_warm_fail", error=error))

    def _on_prepare_start(self) -> None:
        self.prepare_state_label.setText(self._t("warming"))
        self._append_log(self._t("log_prepare_start"))

    def _on_prepare_ok(self, prepared: PreparedRunData) -> None:
        self.prepared = prepared
        self.app_config.delay = prepared.delay
        save_app_config(self.app_config)
        self.delay_label.setText(f"{prepared.delay:.3f}s")
        self.prepare_state_label.setText(self._t("ready"))
        self._append_log(
            self._t(
                "log_prepare_ok",
                count=len(prepared.events_by_time),
                delay=prepared.delay,
            )
        )
        if (
            self.auto_start_cv_check.isChecked()
            and not self.auto_start_timer.isActive()
        ):
            self.auto_start_timer.start()

    def _on_prepare_fail(self, token: str) -> None:
        self.prepared = None
        self.prepare_state_label.setText(self._t("error"))
        if token.startswith("read_error:"):
            msg = self._t("read_error", error=token.split(":", 1)[1])
        elif token.startswith("parse_error:"):
            msg = token.split(":", 1)[1]
        elif token == "delay_error":
            msg = "delay detect failed"
        elif token == "event_error":
            msg = "event build failed"
        else:
            msg = token
        self._append_log(self._t("log_prepare_fail", error=msg))


def run_gui() -> None:
    app = QApplication.instance() or QApplication([])
    window = AutoPlayWindow()
    window.show()
    app.exec()
