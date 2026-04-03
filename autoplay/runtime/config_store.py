from __future__ import annotations

import json

from autoplay.domain.config import AppConfig

CONFIG_FILE = "auto_arcaea_config.json"


def load_app_config(config_file: str = CONFIG_FILE) -> AppConfig:
    try:
        with open(config_file, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
            return AppConfig.from_dict(payload)
    except FileNotFoundError:
        return AppConfig.default()
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        return AppConfig.default()


def save_app_config(config: AppConfig, config_file: str = CONFIG_FILE) -> None:
    with open(config_file, "w", encoding="utf-8") as handle:
        json.dump(config.to_dict(), handle, indent=2, ensure_ascii=False)
