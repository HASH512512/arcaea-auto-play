ARCAEA Auto Play Project, originally based on arcaea-sap.

## Disclaimer

This project is for learning and communication only.
Any dispute caused by malicious use is unrelated to this repository.

## Environment Requirements

- Python `3.11` (recommended; newer versions may fail)
- `adb` available in `PATH`
- `scrcpy-server-v*.jar` in project root

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run

- English CLI: `python main_EN.py`
- Chinese CLI: `python main_CN.py`
- GUI entry (PySide6): `python main_GUI.py`

## GUI Features (PySide6)

`main_GUI.py` provides GUI workflow aligned with CLI capabilities:

- Config editor: `chart_path`, 4 corner coordinates, `fine_tune_step`, `designant_choice`
- Playback controls: `Start`, `Stop`, `+step`, `-step`, `Reset`
- Runtime status: run state, fine-tune offset, auto-detected `delay`
- Log panel: playback logs and error details

Note: GUI and CLI share the same parser/analyzer/solver/runtime core and `auto_arcaea_config.json` keys.

## Refactor Status (v4)

The project has been modernized into layered modules while preserving legacy behavior:

- `autoplay/domain`: pure models for chart/config/errors
- `autoplay/parser`: AFF parser and scan helpers
- `autoplay/analyzer`: scenecontrol and 4K/6K segment analysis
- `autoplay/solver`: unified 4K/6K core solver with profiles
- `autoplay/runtime`: config persistence and touch-event runtime
- `autoplay/cli`: shared CN/EN workflow and prompts

Compatibility entry files are retained:

- `chart.py`
- `solve.py`
- `sixk_solve.py`
- `sixk_manager.py`

## Validation

Syntax check:

```bash
python -m py_compile main_EN.py main_CN.py chart.py solve.py sixk_solve.py sixk_manager.py control.py easing.py algo\algo_base.py autoplay\cli\app.py autoplay\parser\aff_parser.py autoplay\analyzer\mode_analyzer.py autoplay\solver\core.py autoplay\runtime\player.py autoplay\domain\chart.py autoplay\domain\config.py
```

Regression tests:

```bash
python -m pytest tests
```

## Tests Coverage

`tests/samples/` and test modules cover at least these scenarios:

- basic 4K chart
- basic 6K with `scenecontrol`
- `timinggroup`
- `arctap`
- `designant` handling
- zero-length arc edge case
- malformed/invalid AFF lines
