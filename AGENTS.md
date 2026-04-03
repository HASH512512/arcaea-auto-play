# AGENTS.md

## Scope

- Applies to the repository root: `D:\Code\arcaeaSapRef\ARCAEA.AUTO.PLAY`.
- Use this file as the default operating guide for coding agents in this repo.
- This is a Windows-oriented Python 3.11 script project for parsing Arcaea AFF charts and sending Android touch events.

## Repo Layout

- `main_CN.py`: Chinese interactive entry point.
- `main_EN.py`: English interactive entry point.
- `chart.py`: compatibility export for domain chart models.
- `solve.py`: compatibility entry for 4K solver.
- `sixk_solve.py`: compatibility entry for 6K solver.
- `sixk_manager.py`: compatibility class alias for mode analyzer.
- `control.py`: ADB + scrcpy server integration and low-level touch injection.
- `easing.py`: interpolation and easing math.
- `algo/algo_base.py`: shared enums, geometry helpers, serializable touch types.
- `auto_arcaea_config.json`: runtime configuration and saved user state.
- `autoplay/domain/`: pure data definitions (chart/config/errors).
- `autoplay/parser/`: AFF parser and chart scanning utilities.
- `autoplay/analyzer/`: `scenecontrol` and 4K/6K mode segment analysis.
- `autoplay/solver/`: unified 4K/6K event solver core.
- `autoplay/runtime/`: config persistence and runtime playback loop.
- `autoplay/cli/`: unified CLI flow with CN/EN text layer.
- `tests/`: parser/analyzer/solver regression tests and AFF samples.

## Environment

- Preferred interpreter: `python 3.11`.
- The README explicitly recommends 3.11 and warns that newer versions can fail.
- Required external tools:
  - `adb` must be installed and available on `PATH`.
  - A `scrcpy-server-v*.jar` file must exist in the repo root.
- Python dependencies are pinned in `requirements.txt`.

## Setup Commands

- Create a venv:
  - `python -m venv .venv`
- Activate in PowerShell:
  - `.\.venv\Scripts\Activate.ps1`
- Activate in `cmd.exe`:
  - `.venv\Scripts\activate.bat`
- Install dependencies:
  - `python -m pip install -r requirements.txt`
- Check interpreter version:
  - `python --version`
- When possible, prefer the venv interpreter explicitly:
  - `.\.venv\Scripts\python.exe --version`

## Run Commands

- Run the Chinese CLI:
  - `python main_CN.py`
- Run the English CLI:
  - `python main_EN.py`
- Smoke-test device discovery / controller wiring:
  - `python control.py`
- Smoke-test coordinate conversion:
  - `python solve.py`
- Smoke-test easing functions:
  - `python easing.py`

## Build / Lint / Test

- There is no formal build system in this repo.
- There is no checked-in lint configuration for `ruff`, `flake8`, `black`, `isort`, `pylint`, `mypy`, or `pyright`.
- Automated regression tests are provided in `tests/` and run with `pytest`.
- Do not claim a command exists unless it is actually present in the codebase.

## Validation Commands That Work Today

- Compile every Python file for syntax validation:
  - `python -m compileall .`
- Compile one file:
  - `python -m py_compile chart.py`
- Compile the main code paths explicitly:
  - `python -m py_compile main_EN.py main_CN.py chart.py solve.py sixk_solve.py sixk_manager.py control.py easing.py algo\algo_base.py autoplay\cli\app.py autoplay\parser\aff_parser.py autoplay\analyzer\mode_analyzer.py autoplay\solver\core.py autoplay\runtime\player.py autoplay\domain\chart.py autoplay\domain\config.py`
- Run regression tests:
  - `python -m pytest tests`
- Use module smoke tests when changing isolated logic:
  - `python solve.py`
  - `python control.py`
  - `python easing.py`

## Single-Test Guidance

- Single file: `python -m pytest tests/test_parser.py`
- Single test by keyword: `python -m pytest tests/test_solver.py -k zero_length`
- Single exact test: `python -m pytest tests/test_analyzer.py::test_mode_analyzer_builds_segments`

## Platform Notes

- This project is written primarily for Windows.
- `msvcrt` is used in `main_CN.py` and `main_EN.py`, so interactive input is Windows-specific.
- The README notes that PowerShell on Windows 11 can behave badly for manual interactive runs; prefer `cmd.exe` if keyboard handling is unreliable.
- Avoid making Linux portability changes unless the user asks for them.

## Config Rules

- Treat `auto_arcaea_config.json` as a persistent runtime file, not a disposable sample.
- Preserve existing keys and meanings:
  - `global.bottom_left`
  - `global.top_left`
  - `global.top_right`
  - `global.bottom_right`
  - `global.chart_path`
  - `global.fine_tune_step`
  - `global.designant_choice`
  - `delay`
- Do not rename config keys casually; the interactive flow and parser behavior rely on them.

## Coding Style

- Follow the current Python style of the surrounding file.
- Prefer small targeted edits over broad refactors.
- Preserve the script-oriented architecture unless there is a concrete reason to restructure it.
- Keep user-facing Chinese text in `main_CN.py` and English text in `main_EN.py`.
- Match nearby logging and prompt style when editing output strings.

## Imports

- Order imports as: standard library, third-party, local modules.
- Prefer absolute local imports already used in the repo, for example `from chart import Chart`.
- Avoid adding relative imports unless a file already uses them.
- Avoid function-local imports unless they are intentionally deferred.

## Formatting

- Use 4-space indentation.
- Keep code readable; there is no enforced formatter, so preserve existing style where practical.
- Keep structured config and coordinate literals expanded when that improves clarity.
- Preserve UTF-8 file handling where the repo already expects it.

## Types

- Keep or add type hints when they clarify interfaces or data structures.
- Prefer Python 3.11 typing syntax in new code, such as `str | None` and `list[ArcTap]`.
- Prefer built-in generic types over `typing.List` / `typing.Dict` in new code.
- Do not add excessive type ceremony to simple local variables.

## Naming

- Functions and modules: `snake_case`.
- Classes and enums: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- Keep existing domain terminology stable: `designant`, `arctap`, `timinggroup`, `fine_tune_step`.
- Do not rename core public classes like `Chart`, `Arc`, `Tap`, `Hold`, `DeviceController`, or `SixKModeManager` without a strong reason.

## Error Handling

- Prefer narrow `except` clauses over bare `except:` in new code.
- Handle expected failures explicitly: missing files, invalid JSON, malformed AFF lines, decode errors, and ADB / scrcpy startup failures.
- For user-facing CLI flows, print a concise actionable message and return early.
- Preserve intentional parser control-flow exceptions, especially `IGNORE_DESIGNANT_LINE` in `chart.py`.
- Be careful changing existing permissive parsing logic; compatibility matters more than elegance here.

## State And Concurrency

- `main_CN.py` and `main_EN.py` rely on module-level mutable state such as `time_offset`, `base_delay`, `time_lock`, `input_listener_active`, and `automation_started`.
- Keep thread interactions simple.
- Guard shared timing state with `time_lock`.
- Do not introduce new background threads unless they are clearly necessary.

## Parser / Solver Edits

- Treat `chart.py`, `solve.py`, and `sixk_solve.py` as high-risk files.
- Parser implementation is now in `autoplay/parser/aff_parser.py` and keeps permissive `eval`-based behavior for AFF compatibility.
- Keep 4K and 6K behavior aligned when modifying shared event-generation rules.
- Preserve pointer-ID behavior unless a redesign is part of the task.
- After parser or solver changes, run at least `python -m py_compile` plus a targeted smoke test.

## Documentation Maintenance

- If you add tests, linting, or a build tool, update this file with exact commands.
- If you change runtime behavior or setup assumptions, update `README.md`, `README_EN.md`, and this file together.
- Do not add new dependencies or tooling unless the task requires it.

## Cursor / Copilot Rules

- No `.cursorrules` file was found during analysis.
- No `.cursor/rules/` directory was found during analysis.
- No `.github/copilot-instructions.md` file was found during analysis.
- If any of those files are added later, treat them as supplemental higher-priority instructions and merge the relevant guidance here.

### 通用开发约束

1. 不得采用只解决局部问题的补丁式修改而忽视整体设计与全局优化
2. 不得引入过多用于中间通信的中间状态以免降低可读性并形成循环依赖
3. 不得为过渡场景编写大量防御性代码以免掩盖主逻辑并增加维护成本
4. 不得只追求功能完成而忽略架构设计
5. 不得省略必要注释，代码必须对他人和未来维护者可理解
6. 不得编写难以阅读的代码，必须保持结构简单清晰并添加解释性注释
7. 不得违反 SOLID 与 DRY 原则，必须保持职责单一并避免逻辑重复
8. 不得维护复杂的中间状态，仅允许保留最小必要的核心数据
9. 不得依赖外部或临时中间状态驱动 UI，所有 UI 状态必须从核心数据推导
10. 不得通过隐式或间接方式变更状态，状态变化应直接更新数据并由框架重新计算
11. 不得编写过量的防御性代码，应通过清晰的数据约束与边界设计解决问题
12. 不得保留未被使用的变量和函数
13. 不得将状态提升或集中到不必要的层级，状态应在最接近使用的位置管理
14. 不得在业务代码中直接依赖具体实现细节或硬编码外部服务
15. 不得在核心业务逻辑中混入 IO、网络、数据库等副作用操作
16. 不得形成隐式依赖，如依赖调用顺序、全局初始化或副作用时序
17. 不得吞掉异常或使用空 catch 掩盖错误
18. 不得将异常作为正常控制流的一部分
19. 不得返回语义不清或混用的错误结果（如 null / undefined / false）
20. 不得在多个位置同时维护同一份事实数据
21. 不得在未定义生命周期和失效策略的情况下缓存状态
22. 不得跨请求共享可变状态，除非明确设计为并发安全
23. 不得使用语义模糊或误导性的命名
24. 不得让单个函数或模块承担多个不相关语义
25. 不得引入非必要的时间耦合或隐含时间假设
26. 不得在关键路径中引入不可控的复杂度或隐式状态机
27. 不得臆测接口行为，必须先查询文档、定义或源码
28. 不得在需求、边界或输入输出不清晰的情况下直接实现
29. 不得基于猜测实现业务逻辑，必须与人类确认需求并留痕
30. 不得在未评估现有实现的情况下新增接口或模块
31. 不得跳过验证流程，必须编写并执行测试用例
32. 不得触碰架构红线或绕过既有设计规范
33. 不得假装理解需求或技术细节，不清楚时必须明确说明
34. 不得在缺乏上下文理解的情况下直接修改代码，必须基于整体结构审慎重构

### 现代化重构指导

- 本仓库默认已进入适合系统性重构的阶段；除非用户明确要求只做局部修补，否则优先考虑在兼容旧行为的前提下重建更清晰的架构。
- 默认优先采用“现代化 Python 重构”而不是立即迁移到其他主语言；优先解决架构、边界、测试和可维护性问题，而不是单纯追求技术栈新颖。
- 重构目标优先级：行为稳定 > 架构清晰 > 可测试性 > 可读性 > 扩展性 > 技术栈升级。
- 不得脱离旧行为约束一次性推倒重写；应先建立行为基线，再逐步替换实现。
- 如果某个历史行为看起来不优雅，也不要默认删除；先判断它是缺陷、兼容包袱，还是经过实战调优的必要行为。

### 推荐目标架构

- 优先按职责拆分为清晰层次，建议至少包含：`domain`、`parser`、`analyzer`、`solver`、`runtime`、`cli`。
- `domain`：只放谱面模型、事件模型、模式区段、配置模型、错误类型等纯数据定义。
- `parser`：只负责将 AFF 文本解析为领域对象，不得读取配置、不得询问用户、不得写回文件。
- `analyzer`：负责 `scenecontrol`、4K/6K 区段分析、谱面统计和中间分析结果。
- `solver`：负责将 `Chart + 模式区段 + 坐标配置` 转为触控事件序列；应尽量设计为纯函数。
- `runtime`：负责时间调度、ADB/scrcpy 连接、设备注入、微调输入等副作用逻辑。
- `cli`：负责命令行交互、语言文案、文件选择、配置编辑、用户确认。
- 不得再让入口脚本承担解析、模式分析、求解、设备执行的所有细节。

### 重构边界约束

- 解析层和求解层默认必须尽可能纯函数化，避免依赖全局变量、标准输入、配置文件和设备状态。
- 不得在数据模型构造函数内执行 IO、副作用或用户交互。
- 不得继续将 `designant_choice` 的用户确认逻辑放在 `chart.py` 中；该逻辑应位于 `cli` 或配置决策层。
- 不得长期维护两份几乎相同的中英文入口；语言差异应下沉为文案层，而不是业务流程复制。
- 不得长期维护两份高度重复的 4K/6K 求解主流程；优先重构为“一套核心流程 + profile/config 差异”。
- 不得继续通过 `hasattr()` 猜测 note 类型；应以稳定的数据模型和显式分派为准。
- 不得继续依赖“删掉 `scenecontrol` 再单独正则分析”的分裂流程；重构后应纳入统一解析/分析链路。

### 兼容性要求

- 以下内容默认视为高兼容性要求，除非用户明确允许改变：AFF 解析语义、`timinggroup` 处理、`designant` 行为、4K/6K 切换规则、指针 ID 分配、关键触控时序、已有配置键。
- `auto_arcaea_config.json` 中既有键名默认继续兼容，尤其是：`global.bottom_left`、`global.top_left`、`global.top_right`、`global.bottom_right`、`global.chart_path`、`global.fine_tune_step`、`global.designant_choice`、`delay`。
- 允许重构配置加载方式，但不应无理由破坏已有配置文件的兼容读取。
- 如果必须改变配置结构，应提供迁移策略或兼容读取逻辑，并同步更新文档。

### 测试与验证要求

- 在重构 `chart.py`、`solve.py`、`sixk_solve.py`、`sixk_manager.py`、`control.py` 前，优先建立行为基线和最小可重复验证路径。
- 至少为以下场景建立样例和回归验证：普通 4K、普通 6K、含 `timinggroup`、含 `scenecontrol`、含 `arctap`、含 `designant`、零长度或极短 arc、异常/边界 AFF 行。
- parser 重构时，优先比较解析结果是否一致。
- solver 重构时，优先比较事件时间戳、事件数量、事件类型、指针 ID、关键坐标和起止动作是否一致。
- runtime 改动时，至少验证设备连接、事件发送、基础延迟、微调输入、启动/结束流程和异常路径。
- 在没有测试基线前，不要先做大规模格式化、重命名或目录迁移。

### 推荐工程化升级

- 当仓库开始进入稳定重构阶段时，可以引入最小必要的现代工具链，例如：`pytest`、`ruff`、`pyright` 或 `mypy`。
- 推荐顺序：先测试，再 lint/format，再更强类型检查。
- 可引入 `dataclass`、更清晰的类型别名、枚举和专用错误类型，以提升领域建模质量。
- 可以将脚本式结构逐步收敛为包结构，但要控制迁移范围，避免一次性重命名过多核心模块。

### AI 协作准则

- AI 在重构前应优先完成逆向梳理：模块依赖、数据流、领域对象、隐式约束、高风险兼容点；不要在上下文不足时直接大改。
- AI 更适合执行“可验证的小步重构”，例如：提取纯函数、拆分模块、补测试、统一重复逻辑、比较新旧输出差异。
- 对高风险文件的改动必须先理解现有行为，再实施重构。
- AI 不得一次性输出脱离旧行为基线的大重写结果并假定其正确。
- 使用 AI 时，优先明确：目标模块、不能破坏的行为、允许修改的文件、验收标准、测试方式。
- 如果 AI 发现当前代码存在疑似缺陷，也不要在没有验证基线前顺手连带大改相关逻辑。

### 建议重构 TODO

- Phase 1: 建立代表性 AFF 样例集合，并为 parser/solver 生成基线快照。
- Phase 2: 引入自动化测试框架，至少覆盖 parser、mode analyzer、solver 的核心路径。
- Phase 3: 提取统一领域模型，消除通过字段存在性判断 note 类型的做法。
- Phase 4: 将 `designant` 交互和配置写入从 `chart.py` 移出，恢复 parser 纯度。
- Phase 5: 合并中英文入口主流程，只保留一份业务逻辑和多语言文案层。
- Phase 6: 将 4K/6K 求解器合并为统一核心流程 + 差异化 profile/config。
- Phase 7: 将 `scenecontrol` 纳入统一解析/分析链路，消除“删除后另行正则分析”的分裂流程。
- Phase 8: 收口运行时全局状态，建立明确的 runner/runtime abstraction。
- Phase 9: 在基线测试保护下，逐步替换 `eval` 解析实现。
- Phase 10: 同步更新 `README.md`、`README_EN.md` 和本文件中的新架构说明与验证命令。
