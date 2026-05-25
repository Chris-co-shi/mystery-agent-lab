# Mystery Agent Lab

`mystery-agent-lab` 是一个 AI 在线剧本杀实验项目。

当前目标不是直接做完整商业产品，而是通过一个可运行的剧本杀场景，逐步学习和验证 AI Agent 的核心能力：

- 剧本数据建模
- 游戏状态管理
- 线索搜证与解锁
- NPC 角色上下文隔离
- LLM 驱动 NPC 回答
- 玩家问答记录
- 最终推理评分
- CLI 最小可玩闭环

---

## 当前版本能力

当前版本已经支持单人 CLI 剧本杀最小闭环：

1. 加载固定剧本 `mansion_murder.json`
2. 启动一局游戏
3. 查看案件背景
4. 查看人物列表
5. 查看当前可见线索
6. 搜索线索并解锁新线索
7. 询问 NPC
8. 调用 LLM 生成 NPC 回答
9. 记录玩家提问与 NPC 回答
10. 提交最终推理
11. 使用 RuleJudge 评分
12. 查看真相复盘

---

## 项目结构

```text
mystery-agent-lab/
  scripts/
    mansion_murder.json

  stery/
    agents/
      npc_agent.py

    application/
      clue_manager.py
      clue_search_service.py
      game_runtime.py
      npc_context_builder.py
      npc_interaction_service.py
      npc_prompt_renderer.py
      rule_judge.py
      script_loader.py
      script_validator.py

    domain/
      enums.py
      models.py
      state.py

    interfaces/
      cli.py

    llm/
      base.py
      errors.py

  tests/
    unit/
    e2e/

  dev/
    run_cli.py
    run_npc_agent_once.py