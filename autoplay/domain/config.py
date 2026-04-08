from __future__ import annotations

from dataclasses import dataclass, field


DEFAULT_BOTTOM_LEFT = (171, 1350)
DEFAULT_TOP_LEFT = (171, 300)
DEFAULT_TOP_RIGHT = (2376, 300)
DEFAULT_BOTTOM_RIGHT = (2376, 1350)


@dataclass(slots=True)
class GlobalConfig:
    bottom_left: tuple[int, int] = DEFAULT_BOTTOM_LEFT
    top_left: tuple[int, int] = DEFAULT_TOP_LEFT
    top_right: tuple[int, int] = DEFAULT_TOP_RIGHT
    bottom_right: tuple[int, int] = DEFAULT_BOTTOM_RIGHT
    chart_path: str = ""
    fine_tune_step: int = 10
    designant_choice: bool | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "GlobalConfig":
        return cls(
            bottom_left=tuple(data.get("bottom_left", DEFAULT_BOTTOM_LEFT)),
            top_left=tuple(data.get("top_left", DEFAULT_TOP_LEFT)),
            top_right=tuple(data.get("top_right", DEFAULT_TOP_RIGHT)),
            bottom_right=tuple(data.get("bottom_right", DEFAULT_BOTTOM_RIGHT)),
            chart_path=str(data.get("chart_path", "")),
            fine_tune_step=int(data.get("fine_tune_step", 10)),
            designant_choice=data.get("designant_choice"),
        )

    def to_dict(self) -> dict:
        return {
            "bottom_left": list(self.bottom_left),
            "top_left": list(self.top_left),
            "top_right": list(self.top_right),
            "bottom_right": list(self.bottom_right),
            "chart_path": self.chart_path,
            "fine_tune_step": self.fine_tune_step,
            "designant_choice": self.designant_choice,
        }


@dataclass(slots=True)
class VisionConfig:
    ui_roi: tuple[float, float, float, float] = (0.66, 0.02, 0.995, 0.20)
    ground_roi: tuple[float, float, float, float] = (
        0.12,
        1310 / 1440,
        0.88,
        1345 / 1440,
    )
    arc_roi: tuple[float, float, float, float] = (0.18, 0.22, 0.82, 0.80)
    ui_template_threshold: float = 0.42
    ui_digit_min_count: int = 7
    ground_note_ratio: float = 0.045
    arc_cap_threshold: float = 0.44
    stream_max_fps: int = 60
    stream_max_size: int = 960
    stream_bitrate_enabled: bool = False
    stream_bitrate_mbps: int = 8
    overlay_enabled: bool = False
    overlay_detached: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "VisionConfig":
        return cls(
            ui_roi=tuple(data.get("ui_roi", (0.66, 0.02, 0.995, 0.20))),
            ground_roi=tuple(
                data.get("ground_roi", (0.12, 1310 / 1440, 0.88, 1345 / 1440))
            ),
            arc_roi=tuple(data.get("arc_roi", (0.18, 0.22, 0.82, 0.80))),
            ui_template_threshold=float(data.get("ui_template_threshold", 0.42)),
            ui_digit_min_count=int(data.get("ui_digit_min_count", 7)),
            ground_note_ratio=float(data.get("ground_note_ratio", 0.045)),
            arc_cap_threshold=float(data.get("arc_cap_threshold", 0.44)),
            stream_max_fps=int(data.get("stream_max_fps", 60)),
            stream_max_size=int(data.get("stream_max_size", 960)),
            stream_bitrate_enabled=bool(data.get("stream_bitrate_enabled", False)),
            stream_bitrate_mbps=int(data.get("stream_bitrate_mbps", 8)),
            overlay_enabled=bool(data.get("overlay_enabled", False)),
            overlay_detached=bool(data.get("overlay_detached", True)),
        )

    def to_dict(self) -> dict:
        return {
            "ui_roi": list(self.ui_roi),
            "ground_roi": list(self.ground_roi),
            "arc_roi": list(self.arc_roi),
            "ui_template_threshold": self.ui_template_threshold,
            "ui_digit_min_count": self.ui_digit_min_count,
            "ground_note_ratio": self.ground_note_ratio,
            "arc_cap_threshold": self.arc_cap_threshold,
            "stream_max_fps": self.stream_max_fps,
            "stream_max_size": self.stream_max_size,
            "stream_bitrate_enabled": self.stream_bitrate_enabled,
            "stream_bitrate_mbps": self.stream_bitrate_mbps,
            "overlay_enabled": self.overlay_enabled,
            "overlay_detached": self.overlay_detached,
        }


@dataclass(slots=True)
class AppConfig:
    global_config: GlobalConfig
    delay: float = 0.0
    vision: VisionConfig = field(default_factory=VisionConfig)

    @classmethod
    def default(cls) -> "AppConfig":
        return cls(global_config=GlobalConfig(), delay=0.0, vision=VisionConfig())

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        global_data = data.get("global", {})
        return cls(
            global_config=GlobalConfig.from_dict(global_data),
            delay=float(data.get("delay", 0.0)),
            vision=VisionConfig.from_dict(data.get("vision", {})),
        )

    def to_dict(self) -> dict:
        return {
            "global": self.global_config.to_dict(),
            "delay": self.delay,
            "vision": self.vision.to_dict(),
        }
