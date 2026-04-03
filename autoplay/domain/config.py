from __future__ import annotations

from dataclasses import dataclass


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
class AppConfig:
    global_config: GlobalConfig
    delay: float = 0.0

    @classmethod
    def default(cls) -> "AppConfig":
        return cls(global_config=GlobalConfig(), delay=0.0)

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        global_data = data.get("global", {})
        return cls(
            global_config=GlobalConfig.from_dict(global_data),
            delay=float(data.get("delay", 0.0)),
        )

    def to_dict(self) -> dict:
        return {
            "global": self.global_config.to_dict(),
            "delay": self.delay,
        }
