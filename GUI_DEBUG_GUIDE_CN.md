# ARCAEA GUI 调试教程（PySide6）

本文面向 `main_GUI.py`，目标是快速定位“点击 Start 后延迟”“不出事件”“设备链路异常”等问题。

## 1. 先理解 GUI 运行链路

当前 GUI 被拆成三段：

1. **控制链路预热**：启动 GUI 即后台执行 `prepare_device_controller()`，提前建立 ADB/scrcpy 通道。
2. **谱面预编译**：把 AFF 解析/分析/求解提前完成，得到 `events_by_time`（避免 Start 时再做重计算）。
3. **播放调度**：Start 仅触发 `run_touch_events(...)` 开始按时间发送触控事件。

如果第 1/2 步未完成，Start 会被拦截并提示。

---

## 2. 如何查看更多运行时 Debug 信息

### 2.1 GUI 内开启详细调度日志

在“设置”页，将调试开关切到 `ON`（Verbose scheduler debug logs）。

开启后会输出：

- 调度器装载信息（首个 tick、事件组数量、base_delay）
- 每次 dispatch 的 `tick`、`lateness`（迟到毫秒）、事件数量
- Start 到首个 dispatch 的端到端延迟（GUI 里单独输出）

这些日志都在右侧常显日志区。

### 2.2 关键日志关键词

- `[DEBUG] Start->first dispatch latency:`：你点击 Start 到第一批事件真正发送的延迟
- `[DEBUG] Scheduler armed:`：调度器启动参数
- `[DEBUG] Dispatch tick=... lateness=...`：每批事件的调度抖动
- `[ERROR] ADB/scrcpy preheat failed:`：设备预热失败
- `[ERROR] Prepare failed:`：解析/求解阶段失败

---

## 3. 出问题时怎么定位代码

## 3.1 Start 后依旧明显延迟

优先看：

1. `Start->first dispatch latency` 是否很大
2. `Prepare completed` 是否在 Start 前完成
3. `ADB/scrcpy preheat completed` 是否在 Start 前完成

对应代码位置：

- GUI 预热与预编译：`autoplay/gui/app.py`
- 调度器时间循环：`autoplay/runtime/player.py`

若 `Start->first dispatch latency` 很大但预热/预编译都完成，重点看：

- Windows 调度精度与系统负载
- `lateness` 是否持续累积（说明线程被抢占）

## 3.2 能运行但没有触控

先看监控页“当前/下一执行”的折叠详情：

- Note 类型与 tick 是否正确
- TouchEvent 的 `pointer/action/position` 是否合理

再看：

- `prepare_device_controller()` 是否成功
- `controller.touch(...)` 是否被调用（从 dispatch 日志与进度信息联动看）

## 3.3 解析正常但事件为空

关注：

- `Prepare failed: event build failed`
- designant 选项是否与谱面匹配

排查文件：

- `autoplay/parser/aff_parser.py`
- `autoplay/analyzer/mode_analyzer.py`
- `autoplay/solver/core.py`

---

## 4. 推荐调试流程（实战）

1. 启动 GUI：`python main_GUI.py`
2. 等待日志出现预热成功（ADB/scrcpy）
3. 在设置页保存一次配置并点击“预编译谱面”
4. 打开详细调度日志（ON）
5. 点击 Start，观察：
   - Start->first dispatch latency
   - Dispatch lateness
   - 监控页当前/下一执行详情
6. 若异常，按日志关键词反查到对应模块

---

## 5. 命令行辅助验证（建议）

每次改动后至少执行：

```bash
python -m py_compile main_GUI.py autoplay/gui/app.py autoplay/runtime/player.py
python -m pytest tests
```

如果怀疑算法链路问题，额外运行：

```bash
python autoplay/debug_pipeline.py
```

---

## 6. 当前 GUI 中最关键的观测点

- **右侧日志区（常显）**：看全链路时序和异常
- **概览页状态**：控制通道是否就绪、预编译是否就绪、当前偏移
- **监控页折叠详情**：当前与下一条 Note/TouchEvent 的完整技术字段

通过这三块信息，通常可以把问题快速归类到：

- 设备通道问题（ADB/scrcpy）
- 谱面解析/求解问题（parser/analyzer/solver）
- 运行时调度问题（runtime/player）
