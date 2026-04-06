# VSCode 断点调试傻瓜教程（专门排查 Arcaea 输入失效）

这份教程按“完全新手”写，目标是帮你定位：

- 为什么某些 note 没有触发触摸
- 为什么多条 arc 几乎同时出现时会漏按
- pointer（手指 ID）是否冲突
- DOWN/UP 间隔是否太短导致设备丢事件

---

## 1. 先准备环境

1. 打开项目根目录。
2. 确保依赖安装完成：

```bash
python -m pip install -r requirements.txt
```

3. 在 VSCode 安装 Python 扩展（微软官方那个）。

---

## 2. 创建 VSCode 调试配置

在项目根目录新建 `.vscode/launch.json`：

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Run main_EN.py",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/main_EN.py",
      "console": "integratedTerminal",
      "justMyCode": true
    }
  ]
}
```

然后在“运行和调试”里选择 `Run main_EN.py`。

---

## 3. 必打断点位置（重点）

请在以下位置打断点：

1. `autoplay/solver/core.py` 中 `_build_logical_events()` 的 `append_event(...)` 调用附近
2. `autoplay/solver/core.py` 中 `_project_to_touch_events()` 里 `TouchEvent(...)` 构造处
3. `autoplay/runtime/player.py` 中 `controller.touch(x, y, event.action, event.pointer)` 这一行

这三层分别对应：

- 逻辑事件是否正确生成
- 逻辑坐标到屏幕坐标是否正确
- 最终是否真的发送到设备

---

## 4. 看哪些变量（照着看就行）

断住后，在 VSCode 的 VARIABLES / WATCH 面板看：

- `event.pointer`
- `event.action`
- `event.logical_tick`
- `event.logical_pos`
- `event.source_note_id`
- `event.source_type`

建议把下面这些加到 WATCH：

- `event.pointer`
- `event.action.name`
- `event.logical_tick`
- `event.source_note_id`

---

## 5. 如何判断 pointer（手指 ID）冲突

你要检查同一时间点附近是否发生这些情况：

1. 不同音符事件用了同一个 `pointer`
2. 同一个 `pointer` 出现了异常顺序：
   - `UP` 出现在 `DOWN` 前
   - `DOWN` 和 `UP` 几乎同一时刻（间隔太小）

当前代码中：

- arc 主体 pointer 使用 `5000 + note_id`
- arctap pointer 使用独立区间 `1000~2000`

如果你在断点里看到重复或顺序异常，就能直接定位到 solver 逻辑层。

---

## 6. 如何判断“按下抬起过快”导致失效

重点看同一 pointer 的 DOWN 和 UP 的 tick 差：

- 太小（例如 1~2ms）在真实设备链路上容易丢
- 当前已提高到约 `12ms` 级别（arctap / zero-length arc）

如果你仍怀疑过快：

1. 在 `_build_logical_events()` 给对应 note 断点
2. 看 `tap_tick`、`tap_tick + 12` 是否合理
3. 运行一段有问题谱面，观察是否所有失效都集中在极短间隔事件

---

## 7. 快速定位“是哪一层错了”

按顺序判断：

1. `LogicalTouchEvent` 就错了 -> solver 错
2. 逻辑事件对，但 `TouchEvent.pos` 错 -> 坐标投影错
3. `TouchEvent` 对，但设备无反应 -> runtime/scrcpy 发送层问题

不要跳步，按这个顺序排查最快。

---

## 8. 复现“多色 arc 几乎相接失效”的建议方法

1. 先用你那张问题谱面（例如 steganography）
2. 把断点打在 `controller.touch(...)`
3. 当画面出现问题段时，按 F10 单步几次
4. 记录连续 20~40 个事件的：
   - tick
   - pointer
   - action
5. 检查是否存在：
   - 同 tick 大量 UP/DOWN 交叉
   - 相同 pointer 被不同 note 抢占

---

## 9. 常见误区

1. 只看最终屏幕位置，不看 pointer 和 action 顺序
2. 一上来就改 parser，实际上是 runtime 发送顺序问题
3. 忽略输入焦点，导致键盘监听命令没进程序

---

## 10. 你当前版本已经做的关键修复

1. 键盘监听改为 `keyboard`，并限制终端聚焦时才响应
2. 启动前预初始化 `DeviceController`，避免回车后初始化耗时扰动
3. arc 主体 pointer 改为按 `note_id` 唯一分配，降低多色 arc 交错冲突
4. 极短事件（如 arctap / zero-length arc）UP 延后到约 12ms，降低丢输入概率

如果后续你抓到一段具体失效日志（tick/pointer/action 三列），我可以直接帮你判断是“pointer 冲突”还是“时序太挤”。
