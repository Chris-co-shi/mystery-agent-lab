# Mystery Agent Lab

一个用于学习和实验 **AI 剧本杀 / 推理游戏 Agent** 的轻量级项目。

本项目不追求一开始就做复杂的 Web 平台、多玩家房间或商业化系统，而是先从一个可运行、可测试、可迭代的 CLI 剧本杀闭环开始，逐步演进出 AI NPC、线索系统、推理判定、会话记录、剧本管理和调查节奏管理等核心能力。

---

## 1. 项目定位

Mystery Agent Lab 是一个面向学习和工程实践的 AI 剧本杀实验项目。

当前重点：

- 剧本结构建模与 JSON 加载
- CLI 单人游玩闭环
- 玩家搜索线索、询问 NPC、提交最终推理
- LLM 驱动 NPC 回答
- NPC 回答安全边界
- 会话记录与问答历史
- 调查轮次管理

后续方向：

- 更强的 NPC 记忆与上下文管理
- 更完整的主持人 Agent
- 剧本生成与剧本管理后台
- Web API / Web UI
- 多玩家协作推理

---

## 2. 当前版本状态

### v0.1.0 - CLI Playable

完成最小可玩闭环：加载剧本、展示背景和角色、搜索线索、询问 NPC、提交最终推理、规则判定与真相复盘。

### v0.1.1 - CLI 可玩性与剧本管理增强

完成多剧本加载、`ScriptRepository` 抽象、CLI 交互提示优化、线索搜索反馈优化、NPC 回答安全边界和会话记录能力。

### v0.1.2 - 问答历史与调查轮次增强

当前版本重点从“能玩一局”升级为“调查过程可追踪、可复盘、可分轮推进”。

已完成：

- NPC 问答记录链路：`question_history` / `answer_history`
- `/history`：查看完整问答历史
- 调查轮次模型：`InvestigationRound`
- 当前调查轮自动绑定提问记录
- `/review`：查看当前调查轮摘要
- `/close-round`：关闭当前调查轮并开启下一轮
- `/rounds`：查看所有调查轮状态

详细设计与验收记录见：

```text
/docs/releases/v0.1.2-acceptance-note.md
```

---

## 3. 快速启动

列出可用剧本：

```bash
python dev/run_cli.py --list-scripts
```

启动指定剧本：

```bash
python dev/run_cli.py --script snow_inn_murder
```

---

## 4. 常用 CLI 命令

```text
/help         查看命令帮助
/status       查看当前游戏状态
/background   查看案件背景
/characters   查看人物列表
/clues        查看当前线索
/search       搜索线索
/ask          询问 NPC
/history      查看问答历史
/review       查看当前调查轮摘要
/close-round  关闭当前调查轮并开启下一轮
/rounds       查看所有调查轮
/submit       提交最终推理
/quit         退出游戏
```

---

## 5. 核心模块概览

```text
stery/domain
  剧本模型、游戏状态、调查轮次、枚举定义

stery/application
  游戏运行时、NPC 交互服务、线索搜索、规则判定、会话记录

stery/agents
  NPC Agent 与 LLM 调用编排

stery/interfaces
  CLI 交互入口

scripts
  剧本 JSON 数据

tests
  单元测试与功能回归测试
```

---

## 6. 测试

运行全量测试：

```bash
pytest
```

常用专项测试：

```bash
pytest tests/unit/test_npc_interaction_service.py
pytest tests/unit/test_cli_history.py
pytest tests/unit/test_game_runtime_investigation_round.py
pytest tests/unit/test_cli_review.py
pytest tests/unit/test_cli_close_round.py
pytest tests/unit/test_cli_rounds.py
```

---

## 7. 当前边界

当前阶段仍然保持 CLI 单人实验项目定位，暂不做：

- Web UI
- 多玩家房间
- 数据库持久化
- 商业化后台
- AI 自动锁凶
- 剧本自动生成

这些能力会在后续版本中按阶段引入。

---

## 8. 项目原则

- 先保证可运行，再逐步增强智能化
- 先保证状态可追踪，再做复杂推理
- 领域状态由 Runtime 管理，CLI 只负责展示和输入
- README 只做项目总览，详细设计沉淀到 `docs/`
