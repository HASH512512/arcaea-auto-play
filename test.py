from __future__ import annotations

import argparse
from pathlib import Path

from autoplay.debug_pipeline import generate_debug_artifacts
from autoplay.runtime import CONFIG_FILE, load_app_config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run local debug pipeline and export JSON/Markdown files."
    )
    parser.add_argument(
        "--chart",
        default="tests/samples/steganography_cut/3.aff",
        help="Path to input AFF chart file",
    )
    parser.add_argument(
        "--designant",
        choices=["true", "false"],
        default="true",
        help="Whether designant notes are enabled",
    )
    parser.add_argument(
        "--out-json",
        default="debug/test_pipeline_snapshot.json",
        help="Path to output JSON snapshot file",
    )
    parser.add_argument(
        "--out-md",
        default="debug/test_pipeline_report.md",
        help="Path to output markdown report file",
    )
    parser.add_argument(
        "--config-file",
        default=str(CONFIG_FILE),
        help="Path to app config file for screen calibration",
    )
    args = parser.parse_args()

    app_config = load_app_config(args.config_file)
    cfg = app_config.global_config
    converter_points = (
        cfg.bottom_left,
        cfg.top_left,
        cfg.top_right,
        cfg.bottom_right,
    )

    snapshot = generate_debug_artifacts(
        chart_path=Path(args.chart),
        designant_choice=(args.designant == "true"),
        out_json=Path(args.out_json),
        out_md=Path(args.out_md),
        converter_points=converter_points,
    )

    stats = snapshot.get("stats", {})
    print("Debug pipeline export complete.")
    print("notes:", stats.get("notes", 0))
    print("logical events:", stats.get("logical_events", 0))
    print("touch events:", stats.get("touch_events_total", 0))
    print("converter points:", converter_points)
    print("json:", args.out_json)
    print("markdown:", args.out_md)


if __name__ == "__main__":
    main()
