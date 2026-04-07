ARCAEA 自动游玩项目，基于 arcaea-sap 演进。

## 免责声明

本项目仅供学习交流使用。
任何恶意使用导致的纠纷与本项目无关。

## 环境要求

- Python `3.11`（推荐，更新版本可能报错）
- `adb` 已安装并配置到 `PATH`
- 根目录存在 `scrcpy-server-v*.jar`

安装依赖：

```bash
python -m pip install -r requirements.txt
```

## 启动方式

- 中文入口：`python main_CN.py`
- 英文入口：`python main_EN.py`
- GUI 入口（PySide6）：`python main_GUI.py`

## GUI 功能（PySide6）

`main_GUI.py` 提供与 CLI 对齐的核心能力：

- 配置编辑：`chart_path`、四角坐标、`fine_tune_step`、`designant_choice`
- 执行控制：`Start`、`Stop`、`+step`、`-step`、`Reset`
- 状态展示：运行状态、当前微调偏移、自动识别 `delay`
- 日志面板：展示播放过程和异常信息

说明：GUI 与 CLI 共用同一套 parser/analyzer/solver/runtime 逻辑与 `auto_arcaea_config.json` 配置键。

## 重构状态（v4）

项目已按职责重构为分层架构，同时保留旧行为兼容：

- `autoplay/domain`：谱面/配置/错误等纯数据模型
- `autoplay/parser`：AFF 解析与扫描工具
- `autoplay/analyzer`：`scenecontrol` 与 4K/6K 区段分析
- `autoplay/solver`：统一 4K/6K 核心求解流程（profile 差异）
- `autoplay/runtime`：配置持久化与触控事件运行时
- `autoplay/cli`：中英文共用主流程，文案按语言分层

以下兼容入口文件仍保留：

- `chart.py`
- `solve.py`
- `sixk_solve.py`
- `sixk_manager.py`

## 验证命令

语法编译检查：

```bash
python -m py_compile main_EN.py main_CN.py chart.py solve.py sixk_solve.py sixk_manager.py control.py easing.py algo\algo_base.py autoplay\cli\app.py autoplay\parser\aff_parser.py autoplay\analyzer\mode_analyzer.py autoplay\solver\core.py autoplay\runtime\player.py autoplay\domain\chart.py autoplay\domain\config.py
```

回归测试：

```bash
python -m pytest tests
```

## 测试覆盖

`tests/samples/` 和测试模块当前覆盖以下关键场景：

- 普通 4K
- 含 `scenecontrol` 的普通 6K
- 含 `timinggroup`
- 含 `arctap`
- 含 `designant`
- 零长度 arc 边界
- 异常/非法 AFF 行
