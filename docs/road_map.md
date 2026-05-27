# Mystery Agent Lab — 完整版本化开发计划（受控路线）

版本：Roadmap Baseline
状态：正式开发基线
维护方式：版本迭代式维护

---

# 一、项目定位

Mystery Agent Lab 当前定位：

```text
AI 推理游戏引擎
```

不是：

```text
多人在线平台
Agent 炫技项目
AI 聊天项目
```

核心目标：

```text
做出：

可信
稳定
可推理
可复盘
可扩展

的 AI 推理游戏引擎。
```

---

# 二、路线控制原则

后续所有版本迭代：

必须遵守：

```text
先稳定游戏核心
再稳定协议
再进入服务化
最后平台化
```

禁止：

```text
提前平台化
提前多人化
提前复杂 Agent 编排
提前 AI 自动生成
```

---

# 三、版本演化路线

整体路线：

```text
V0.1.x
CLI 单局推理闭环

↓

V0.2.x
调查机制 + NPC可信化

↓

V0.3.x
Session/Event Runtime

↓

V0.4.x
HTTP API 服务化

↓

V0.5.x
Web 单人版

↓

V0.6.x
剧本 CMS / 内容平台

↓

V0.7.x
AI 辅助生成剧本

↓

V0.8.x
多人在线
```

禁止跳阶段。

---

# 四、V0.1.x：CLI 单局推理闭环

阶段目标：

```text
完成完整单局推理体验。
```

即：

```text
问 NPC
→ 调查线索
→ 查看历史
→ 提交推理
→ 获得复盘
→ 导出结果
```

---

# V0.1.0

## 目标

建立最小可玩闭环。

---

## 功能范围

### 游戏核心

* GameScript
* GameState
* NPC 问答
* accuse 判案
* clue 系统

### CLI

* ask
* clues
* submit
* help

### 基础结构

* domain
* application
* interfaces

---

## 阶段结果

达到：

```text
最小 AI 推理游戏 Demo
```

---

# V0.1.1

## 目标

开始内容资产化与安全控制。

---

## 功能范围

### Script 体系

* ScriptRepository
* ScriptSource 抽象
* script_validator 雏形

### NPC 安全

* NPC Guardrail
* 禁止直接泄底
* 主观怀疑回答

### SessionRecorder

* JSON 导出
* Markdown 导出
* 基础会话记录

---

## 阶段结果

达到：

```text
可管理剧本 + 可导出推理结果
```

---

# V0.1.2

## 目标

完成会话复盘闭环。

---

## 功能范围

### CLI 增强

* /status
* /history
* /review
* /rounds
* /close-round

### History

支持：

* 问答历史
* 回合历史
* NPC 问答记录

### JudgeResult

结构化：

* score
* matched clues
* final result

### SessionRecorder

增强：

* judge_result 导出
* Markdown 复盘
* JSON 复盘

---

## 阶段结果

达到：

```text
真正可复盘的单局推理体验
```

---

# V0.1.3

## 当前正式开发版本

阶段目标：

```text
调查轮稳定化
```

当前重点：

```text
让玩家真正“调查案件”
而不是单纯聊天。
```

---

## 允许开发内容

### TASK-001：调查轮稳定化

统一：

* round lifecycle
* round state
* round summary

避免：

```text
轮次状态混乱
```

---

### TASK-002：review 系统增强

支持：

* 当前轮总结
* 已发现线索
* 当前嫌疑人
* 当前推理方向

---

### TASK-003：线索发现增强

支持：

* discovered clue
* hidden clue
* key clue

但：

```text
暂不引入复杂地图系统
```

---

### TASK-004：调查结果结构化

统一：

```python
InvestigationResult
```

避免：

```text
大量字符串拼接逻辑
```

---

### TASK-005：测试稳定化

增加：

* round tests
* review tests
* clue tests
* recorder tests

当前阶段：

```text
稳定性优先于新功能
```

---

## 当前明确禁止

```text
不做 Web
不做 FastAPI
不做 GameSession Runtime
不做多人
不做 AI 自动生成
```

---

# V0.1.4

## 目标

协议稳定化。

---

## 功能范围

### GameScript 冻结

明确：

* characters
* clues
* truth
* timeline
* npc_profiles
* rules

阶段结束后：

```text
GameScript 视为稳定协议
```

---

### script_validator 升级

支持：

* timeline 校验
* killer 校验
* clue owner 校验
* npc knowledge 校验

目标：

```text
升级为“剧本编译器”
```

---

### ScriptRepository 稳定化

统一：

* load_script
* list_scripts
* validate_script

---

## 阶段结果

达到：

```text
稳定的剧本协议层
```

---

# 五、V0.2.x：调查机制与 NPC 可信化

阶段目标：

```text
从聊天游戏
升级为调查推理游戏
```

---

# V0.2.0

## investigate 系统

支持：

* investigate room
* investigate body
* investigate item

---

## Location 模型

支持：

* 地点
* 场景
* 可调查对象

---

## Hidden Clue

支持：

* 条件触发
* 隐藏线索
* 特殊发现

---

# V0.2.1

## NPC Knowledge Boundary

NPC 区分：

* facts
* rumors
* assumptions
* lies
* secrets

避免：

```text
NPC = 全知 AI
```

---

## NPC Profile

支持：

* personality
* emotion
* speaking_style
* bias
* secrets

---

# 六、V0.3.x：Session 与 Event Runtime

阶段目标：

```text
真正游戏运行时
```

---

# V0.3.0

## GameSession

支持：

* session_id
* current_state
* discovered_clues
* player_notes
* status

---

## GameEvent

统一：

* AskNpcEvent
* DiscoverClueEvent
* AccuseEvent
* JudgeEvent

---

# 七、V0.4.x：HTTP API 服务化

阶段目标：

```text
从 CLI 进入服务化
```

---

## FastAPI

支持：

* Session API
* Ask NPC API
* Clue API
* Submit API

当前阶段：

```text
只支持单人
```

---

# 八、V0.5.x：Web 单人版

阶段目标：

```text
真正用户可玩
```

---

## Web UI

支持：

* Script Select
* NPC Chat
* Clue Panel
* Review Panel
* Final Result

---

# 九、V0.6.x：剧本 CMS

阶段目标：

```text
内容平台化
```

---

## CMS

支持：

* Script CRUD
* Character Config
* Clue Config
* Truth Config
* NPC Knowledge Config

---

# 十、V0.7.x：AI 辅助生成剧本

阶段目标：

```text
AI + 人工协作生成剧本
```

---

## AI Generate

分阶段：

```text
题材
→ 人物关系
→ 真相
→ 时间线
→ 线索
→ NPC知识
→ 一致性检查
```

禁止：

```text
一步生成完整剧本
```

---

# 十一、V0.8.x：多人在线

当前阶段：

```text
长期规划
```

当前禁止提前进入。

---

## Room System

未来支持：

* room
* role select
* vote
* websocket
* multiplayer sync

---

# 十二、README 管理策略（正式建议）

建议：

```text
每完成一个版本迭代
就在 README 增加：

- 当前版本
- 已完成内容
- 当前架构图
- 下一版本计划
```

这是非常推荐的做法。

---

# 推荐 README 结构

建议 README 固定包含：

```text
1. 项目定位
2. 当前版本
3. 当前能力
4. 架构图
5. 已完成版本历史
6. 当前开发计划
7. 后续路线图
```

---

# 推荐版本记录方式

例如：

```markdown
## Version History

### V0.1.0
- 最小 CLI 推理闭环

### V0.1.1
- ScriptRepository
- NPC Guardrail
- SessionRecorder

### V0.1.2
- history
- review
- round system
- recorder enhancement
```

这样会非常清晰。

---

# 十三、README 是否应该同步更新

结论：

```text
强烈建议。
```

原因：

README 不只是介绍页。

对于当前项目：

README 实际上承担：

```text
项目阶段状态
+
当前目标
+
版本演化历史
+
开发边界
```

如果 README 不同步：

后面会出现：

```text
代码状态
计划状态
项目定位

三者脱节。
```

这是很多 AI 项目后期失控的重要原因。

---

# 十四、当前最终控制结论

当前最重要的不是：

```text
功能数量
```

而是：

```text
稳定游戏核心
稳定推理体验
稳定剧本协议
稳定 NPC 可信性
```

因此：

当前项目必须继续：

```text
小版本
可控迭代
严格限制范围
```

而不是快速平台化。
