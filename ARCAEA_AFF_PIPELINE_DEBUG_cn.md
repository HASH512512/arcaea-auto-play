# Arcaea AFF 新流水线调试指南

## 1. 新流水线概览

Arcaea AFF 流程现在被拆分为清晰的阶段：

1. 将 AFF 文本解析为 `ArcaeaChartIR`（`autoplay/parser/aff_ir_parser.py`）
2. 基于 `scenecontrol` 构建投影时间轴（`autoplay/analyzer/mode_analyzer.py`）
3. 求解为逻辑事件（`autoplay/solver/core.py` 中的 `LogicalTouchEvent`）
4. 将逻辑坐标投影为设备坐标（`autoplay/solver/coordinate.py` 中的 `CoordConv`）
5. 在运行时发送触摸事件（`autoplay/runtime/player.py`）

这种分层方式允许你从错误触摸输出反向追踪到解析层与谱面逻辑层。

## 2. 新解析器/求解器使用的坐标规则

实现遵循 `参考资料/谱面格式.md` 中的核心映射规则：

- AFF 浮点轨道 note 到 arc-x 的映射：`x = -0.5 + lane * 2`
- Arc 在逻辑空间中直接使用 AFF 的 `x/y`
- `enwidencamera` 会在求解阶段改变 sky 投影缩放
- `enwidenlanes` 会在时间轴阶段改变轨道 profile

如果输出看起来发生了视觉偏移，优先确认谱面使用的是整数轨道、浮点轨道，还是 arc。

## 3. 快速冒烟检查命令

在仓库根目录运行以下命令：

```bash
python -m py_compile autoplay/parser/aff_ir_parser.py autoplay/parser/aff_parser.py autoplay/analyzer/mode_analyzer.py autoplay/solver/core.py
```

```bash
python -c "from pathlib import Path; from autoplay.parser import parse_aff_chart; from autoplay.solver import CoordConv, solve_chart_auto; c=Path('tests/samples/basic_6k_scenecontrol.aff').read_text(encoding='utf-8'); chart=parse_aff_chart(c, designant_choice=True); conv=CoordConv((171,1350),(171,300),(2376,300),(2376,1350)); ev=solve_chart_auto(chart,conv); print('timestamps=',len(ev),'has_ir=',bool(chart.ir))"
```

## 4. 分阶段调试

### 4.1 解析阶段（`AFF -> ArcaeaChartIR`）

先检查解析输出：

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

如果这里有问题，不要先调 solver。

### 4.2 时间轴阶段（`scenecontrol -> mode timeline`）

```python
from autoplay.analyzer.mode_analyzer import ArcaeaTimelineAnalyzer

timeline = ArcaeaTimelineAnalyzer()
timeline.build(ir)

for t in [0, 500, 650, 1200, 1350]:
    print(t, timeline.lane_mode_at(t), timeline.sky_mode_at(t))
```

如果模式切换不正确，先修 analyzer 逻辑，再处理 solver。

### 4.3 逻辑求解阶段（`ChartIR -> LogicalTouchEvent`）

`autoplay/solver/core.py` 会把元数据写入最终 `TouchEvent`：

- `source_note_id`
- `source_type`
- `logical_tick`
- `logical_pos`

这些元数据就是反向定位问题的锚点。

## 5. 如何从错误触摸事件反查

当你在设备上看到错误触摸时，按以下流程排查。

### Step A: 定位可疑输出事件

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

### Step B: 在 `chart.ir` 里找到来源 note

```python
target_note_id = 3
for note in chart.ir.notes:
    if note.note_id == target_note_id:
        print(note)
        break
```

这样你就能确认问题来自哪个 `tap/hold/arc/arctap` 源数据。

### Step C: 校验该时刻的时间轴状态

```python
from autoplay.analyzer.mode_analyzer import ArcaeaTimelineAnalyzer

timeline = ArcaeaTimelineAnalyzer()
timeline.build(chart.ir)
tick = 700
print("lane_mode", timeline.lane_mode_at(tick))
print("sky_mode", timeline.sky_mode_at(tick))
```

如果模式不符合预期，问题在 scenecontrol 分析层。

### Step D: 快速判断问题层级

- 如果 `source_note_id` 指向了错误 note：解析器问题
- 如果 note 正确但 mode 错误：分析器问题
- 如果 note 和 mode 都正确但 logical_pos 错误：逻辑求解器问题
- 如果 logical_pos 正确但设备坐标错误：`CoordConv` / 屏幕标定问题

## 6. 常见故障模式

1. 浮点轨道 note 的 lane 错误
   - 先检查解析后的 lane 数值和浮点映射公式。
2. 4K/6K 切换出现提前或延后
   - 检查 analyzer 中 `scenecontrol` 的 duration 与半程切换点。
3. Arc 轨迹形状不对
   - 检查 easing 类型解析（`s`, `b`, `si`, `so`, `siso` 等）。
4. ArcTap 时序正确但位置错误
   - 检查 tap 时刻的 arc 插值和 sky 模式缩放。

## 7. 推荐调试顺序

务必按以下顺序排查，避免无效调试：

1. 解析器输出（`parse_aff_ir`）
2. 时间轴模式（`lane_mode_at` / `sky_mode_at`）
3. 逻辑事件元数据（`logical_tick`, `logical_pos`, `source_note_id`）
4. 最终像素事件（`event.pos`）
5. 运行时注入与设备表现

## 8. 扩展这套流水线时的注意事项

- 保持 parser 与 solver 解耦；不要在 solver 层解析文本。
- 为所有新增 note 类型保留 `TouchEvent` 反查元数据。
- 新增边界行为前先补测试样例，再做运行时优化。
