# Arcaea AFF New Pipeline Debug Guide

## 1. New pipeline overview

The Arcaea AFF flow is now split into explicit stages:

1. Parse AFF text into `ArcaeaChartIR` (`autoplay/parser/aff_ir_parser.py`)
2. Build projection timeline from `scenecontrol` (`autoplay/analyzer/mode_analyzer.py`)
3. Solve into logical events (`LogicalTouchEvent` in `autoplay/solver/core.py`)
4. Project logical coordinates into device coordinates (`CoordConv` in `autoplay/solver/coordinate.py`)
5. Send touch events at runtime (`autoplay/runtime/player.py`)

This separation allows reverse tracing from bad touch output back to parser and chart logic.

## 2. Coordinate rules used by the new parser/solver

The implementation follows `参考资料/谱面格式.md` core mapping rules:

- AFF float lane note to arc-x mapping: `x = -0.5 + lane * 2`
- Arc uses AFF `x/y` directly in logical space
- `enwidencamera` changes sky projection scale in solver stage
- `enwidenlanes` changes lane profile at timeline stage

If output looks visually shifted, first confirm whether the chart is using integer lanes, float lanes, or arcs.

## 3. Quick smoke check commands

Use these in repository root:

```bash
python -m py_compile autoplay/parser/aff_ir_parser.py autoplay/parser/aff_parser.py autoplay/analyzer/mode_analyzer.py autoplay/solver/core.py
```

```bash
python -c "from pathlib import Path; from autoplay.parser import parse_aff_chart; from autoplay.solver import CoordConv, solve_chart_auto; c=Path('tests/samples/basic_6k_scenecontrol.aff').read_text(encoding='utf-8'); chart=parse_aff_chart(c, designant_choice=True); conv=CoordConv((171,1350),(171,300),(2376,300),(2376,1350)); ev=solve_chart_auto(chart,conv); print('timestamps=',len(ev),'has_ir=',bool(chart.ir))"
```

## 4. Stage-by-stage debugging

### 4.1 Parser stage (`AFF -> ArcaeaChartIR`)

Inspect parser output first:

```python
from pathlib import Path
from autoplay.parser import parse_aff_ir

content = Path("tests/samples/basic_6k_scenecontrol.aff").read_text(encoding="utf-8")
ir = parse_aff_ir(content, designant_choice=True)

print(ir.options)
print("timings:", len(ir.timings))
print("notes:", len(ir.notes))
print("scenecontrols:", [(s.tick, s.control_type, s.param1, s.param2) for s in ir.scene_controls])
```

If this is wrong, do not debug solver yet.

### 4.2 Timeline stage (`scenecontrol -> mode timeline`)

```python
from autoplay.analyzer.mode_analyzer import ArcaeaTimelineAnalyzer

timeline = ArcaeaTimelineAnalyzer()
timeline.build(ir)

for t in [0, 500, 650, 1200, 1350]:
    print(t, timeline.lane_mode_at(t), timeline.sky_mode_at(t))
```

If mode transitions are wrong, fix analyzer logic before touching solver.

### 4.3 Logical solver stage (`ChartIR -> LogicalTouchEvent`)

`autoplay/solver/core.py` stores metadata into final `TouchEvent`:

- `source_note_id`
- `source_type`
- `logical_tick`
- `logical_pos`

This metadata is the reverse-trace anchor.

## 5. How to reverse trace a wrong touch event

When you see a wrong touch on device, use this workflow.

### Step A: Locate suspicious output event

```python
from pathlib import Path
from autoplay.parser import parse_aff_chart
from autoplay.solver import CoordConv, solve_chart_auto

content = Path("tests/samples/basic_6k_scenecontrol.aff").read_text(encoding="utf-8")
chart = parse_aff_chart(content, designant_choice=True)
conv = CoordConv((171,1350),(171,300),(2376,300),(2376,1350))
events = solve_chart_auto(chart, conv)

for tick in sorted(events):
    for ev in events[tick]:
        # Example: filter by pointer or time window
        if 680 <= tick <= 760:
            print(
                tick,
                ev.action.name,
                ev.pointer,
                ev.pos,
                ev.source_note_id,
                ev.source_type,
                ev.logical_tick,
                ev.logical_pos,
            )
```

### Step B: Find source note in `chart.ir`

```python
target_note_id = 3
for note in chart.ir.notes:
    if note.note_id == target_note_id:
        print(note)
        break
```

Now you know whether the issue comes from `tap/hold/arc/arctap` source data.

### Step C: Verify timeline at that tick

```python
from autoplay.analyzer.mode_analyzer import ArcaeaTimelineAnalyzer

timeline = ArcaeaTimelineAnalyzer()
timeline.build(chart.ir)
tick = 700
print("lane_mode", timeline.lane_mode_at(tick))
print("sky_mode", timeline.sky_mode_at(tick))
```

If mode is unexpected, bug is in scenecontrol analysis.

### Step D: Determine bug layer quickly

- If `source_note_id` points to wrong note: parser issue
- If note is correct but mode wrong: analyzer issue
- If note and mode correct but logical_pos wrong: logical solver issue
- If logical_pos correct but device pos wrong: `CoordConv`/screen calibration issue

## 6. Common failure patterns

1. Wrong lane for float lane notes
   - Check parser lane value and float mapping formula first.
2. 4K/6K switch appears delayed or early
   - Inspect `scenecontrol` duration and half-duration switch point in analyzer.
3. Arc path shape looks wrong
   - Verify easing type parse (`s`, `b`, `si`, `so`, `siso`, etc.).
4. ArcTap timing correct but position wrong
   - Verify arc interpolation and sky mode scaling at tap tick.

## 7. Recommended debug order

Always follow this order to avoid wasting time:

1. Parser (`parse_aff_ir`) output
2. Timeline modes (`lane_mode_at` / `sky_mode_at`)
3. Logical event metadata (`logical_tick`, `logical_pos`, `source_note_id`)
4. Final projected pixel events (`event.pos`)
5. Runtime injection and device behavior

## 8. Notes for extending this pipeline

- Keep parser and solver separate; do not parse text in solver layer.
- Preserve reverse trace metadata in `TouchEvent` for all new note types.
- Add test samples for every new chart edge case before optimizing runtime.
