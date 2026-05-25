# AI 在线剧本杀领域模型设计

## 1. 文档目的

本文档定义 `mystery-agent-lab` 项目的核心领域模型，用于支撑第一版「单人文本版 AI 在线剧本杀」最小闭环。

第一版目标不是做完整商业化剧本杀平台，而是验证一个可运行、可测试、可演进的 Agent 游戏系统：

```text
START
  -> BACKGROUND_INTRO
  -> FREE_QUESTION
  -> SEARCH_CLUE
  -> FINAL_VOTE
  -> REVEAL_TRUTH
  -> END
```

本文档重点解决以下问题：

* 一局 AI 剧本杀由哪些核心对象组成
* 哪些数据属于剧本静态定义
* 哪些数据属于游戏运行时状态
* 玩家、NPC、Host、Judge 分别可以看到哪些信息
* NPC 如何避免知道完整真相
* 线索如何解锁和展示
* 玩家行为如何记录
* 最终推理如何判断
* 后续 Python 代码如何映射这些模型

---

## 2. 第一版设计原则

### 2.1 先业务闭环，后 Agent 框架

第一版先完成游戏领域模型和流程闭环，不直接引入 LangGraph、LlamaIndex、向量数据库、多 Agent 框架。

原因是：

* 领域边界不清楚时，上 Agent 框架只会放大混乱
* 剧本杀最核心的问题是信息权限和状态推进，不是模型调用本身
* 后续接入 Agent 框架时，领域模型可以保持稳定

### 2.2 LLM 不直接控制核心状态

LLM 可以生成文案、回答、复盘，但不能直接修改核心状态。

例如：

* LLM 可以生成 NPC 回答
* LLM 不能直接决定线索是否解锁
* LLM 可以生成主持人文案
* LLM 不能直接跳转游戏阶段
* LLM 可以解释玩家推理
* LLM 不能直接覆盖最终真相

核心状态必须由确定性代码控制。

### 2.3 信息隔离优先

AI 剧本杀最大的风险是信息泄露。

因此第一版必须严格区分：

* 玩家可见信息
* NPC 可见信息
* Host 可见信息
* Rule Judge 可见信息
* 系统内部真相信息

尤其要避免把完整剧本、完整真相、完整时间线直接塞给 NPC Agent。

### 2.4 先内存模型，后数据库模型

第一版只使用：

* JSON 剧本文件
* Python dataclass / Pydantic model
* Enum
* list / dict
* 内存状态

暂时不引入：

* 数据库
* ORM
* Redis
* 消息队列
* 分布式状态

后续进入多人在线、房间恢复、历史记录时，再设计持久化模型。

---

## 3. 核心对象总览

| 对象             | 类型     | 职责                |
| -------------- | ------ | ----------------- |
| GameScript     | 静态定义   | 表示一个完整剧本          |
| GameRoom       | 运行实例   | 表示一局游戏房间          |
| GameState      | 运行状态   | 表示当前游戏进度和状态       |
| GamePhase      | 枚举     | 表示当前游戏阶段          |
| Player         | 运行实体   | 表示人类玩家            |
| Character      | 静态定义   | 表示剧本中的公开角色        |
| NPCProfile     | 私有定义   | 表示 NPC 的私有背景和知识边界 |
| Clue           | 静态定义   | 表示剧本中的线索          |
| ClueVisibility | 枚举     | 表示线索可见性           |
| EventLog       | 运行记录   | 表示游戏过程事件          |
| Question       | 运行记录   | 表示玩家向 NPC 的提问     |
| Answer         | 运行记录   | 表示 NPC 的回答        |
| JudgeResult    | 运行判断   | 表示裁判判断结果          |
| Vote           | 运行记录   | 表示玩家最终推理          |
| Truth          | 静态敏感定义 | 表示案件真相            |
| TimelineEvent  | 静态定义   | 表示案件时间线事件         |
| GameRule       | 静态规则   | 表示游戏规则和限制         |

---

## 4. 对象分层

从工程视角看，第一版领域对象可以分成三层。

### 4.1 剧本静态层

剧本静态层来自 `scripts/mansion_murder.json`。

包括：

* GameScript
* Character
* NPCProfile
* Clue
* Truth
* TimelineEvent
* GameRule

这些数据在一局游戏运行过程中通常不变。

### 4.2 游戏运行层

游戏运行层表示某一局游戏的当前状态。

包括：

* GameRoom
* GameState
* Player
* Question
* Answer
* Vote
* EventLog

这些数据会随着玩家操作不断变化。

### 4.3 Agent 上下文层

Agent 上下文层不是独立持久化对象，而是根据权限从静态层和运行层中动态组装出来。

例如：

* HostContext
* NPCContext
* JudgeContext
* PlayerView

这些对象用于控制不同 Agent 能看到什么。

---

## 5. GameScript：剧本定义

### 5.1 职责

`GameScript` 表示一个完整剧本的静态定义。

它是游戏初始化的数据来源，不表示某一局游戏的运行状态。

### 5.2 字段设计

```text
script_id: str
version: str
title: str
summary: str
background: str
characters: list[Character]
npc_profiles: list[NPCProfile]
clues: list[Clue]
truth: Truth
timeline: list[TimelineEvent]
rules: list[GameRule]
```

### 5.3 字段说明

| 字段           | 说明            |
| ------------ | ------------- |
| script_id    | 剧本唯一标识        |
| version      | 剧本版本          |
| title        | 剧本标题          |
| summary      | 剧本摘要，供系统或列表展示 |
| background   | 案件背景，玩家可见     |
| characters   | 剧本公开角色列表      |
| npc_profiles | NPC 私有信息列表    |
| clues        | 全部线索定义        |
| truth        | 案件真相          |
| timeline     | 案件时间线         |
| rules        | 游戏规则          |

### 5.4 可见性原则

`GameScript` 可以包含完整真相，但不能直接暴露给所有 Agent。

| 使用方          | 可读取内容                                   |
| ------------ | --------------------------------------- |
| Player       | background、characters 公开信息、已解锁 clues    |
| NPC Agent    | 对应 Character 公开信息、自己的 NPCProfile、必要对话摘要 |
| Host Agent   | 完整 GameScript、完整 GameState              |
| Rule Judge   | 完整 GameScript、完整 GameState、候选回答         |
| Clue Manager | clues、GameState.unlocked_clue_ids、当前阶段  |

---

## 6. GameRoom：游戏房间

### 6.1 职责

`GameRoom` 表示一局具体运行中的游戏。

第一版只有一个玩家，但仍然保留房间概念，方便后续扩展多人在线、房间恢复、历史记录。

### 6.2 字段设计

```text
room_id: str
script_id: str
player: Player
state: GameState
created_at: datetime
updated_at: datetime
```

### 6.3 设计说明

`GameRoom` 是运行时聚合根。

它关联：

* 当前使用的剧本
* 当前玩家
* 当前游戏状态

第一版可以在内存中创建一个默认房间。

### 6.4 示例

```json
{
  "room_id": "room_001",
  "script_id": "mansion_murder_001",
  "player": {
    "player_id": "player_001",
    "display_name": "玩家"
  },
  "state": {
    "current_phase": "START",
    "current_round": 0,
    "unlocked_clue_ids": []
  }
}
```

---

## 7. GameState：游戏状态

### 7.1 职责

`GameState` 表示一局游戏当前运行到哪里，以及已经发生了什么。

这是第一版最核心的运行时对象。

### 7.2 字段设计

```text
room_id: str
current_phase: GamePhase
current_round: int
unlocked_clue_ids: list[str]
asked_questions: list[Question]
answers: list[Answer]
event_logs: list[EventLog]
final_vote: Vote | None
is_finished: bool
```

### 7.3 字段说明

| 字段                | 说明       |
| ----------------- | -------- |
| room_id           | 所属房间 ID  |
| current_phase     | 当前游戏阶段   |
| current_round     | 当前回合数    |
| unlocked_clue_ids | 已解锁线索 ID |
| asked_questions   | 玩家提问记录   |
| answers           | NPC 回答记录 |
| event_logs        | 游戏事件日志   |
| final_vote        | 玩家最终推理   |
| is_finished       | 游戏是否结束   |

### 7.4 状态边界

`GameState` 只保存运行态信息，不保存剧本静态定义。

| 信息       | 所属对象             |
| -------- | ---------------- |
| 剧本背景     | GameScript       |
| 角色公开设定   | Character        |
| NPC 私有秘密 | NPCProfile       |
| 当前阶段     | GameState        |
| 已解锁线索    | GameState        |
| 所有线索定义   | GameScript       |
| 真凶是谁     | Truth            |
| 玩家最终投票   | Vote / GameState |

### 7.5 状态变更原则

所有状态变更都应由确定性函数完成。

例如：

```text
start_game(room)
change_phase(room, next_phase)
unlock_clue(room, clue_id)
record_question(room, question)
record_answer(room, answer)
submit_vote(room, vote)
finish_game(room)
```

LLM 不能直接修改 `GameState`。

---

## 8. GamePhase：游戏阶段

### 8.1 职责

`GamePhase` 表示当前游戏阶段。

### 8.2 枚举值

```text
START
BACKGROUND_INTRO
FREE_QUESTION
SEARCH_CLUE
FINAL_VOTE
REVEAL_TRUTH
END
```

### 8.3 阶段说明

| 阶段               | 说明       | 玩家行为         |
| ---------------- | -------- | ------------ |
| START            | 初始化游戏    | 无            |
| BACKGROUND_INTRO | 展示案件背景   | 查看背景、查看人物    |
| FREE_QUESTION    | 自由询问 NPC | 选择 NPC 并提问   |
| SEARCH_CLUE      | 查看或搜索线索  | 查看当前可见线索     |
| FINAL_VOTE       | 提交最终推理   | 选择凶手、填写动机和手法 |
| REVEAL_TRUTH     | 公布真相     | 查看复盘         |
| END              | 游戏结束     | 无            |

### 8.4 允许的阶段流转

第一版使用固定阶段流转：

```text
START -> BACKGROUND_INTRO
BACKGROUND_INTRO -> FREE_QUESTION
FREE_QUESTION -> SEARCH_CLUE
SEARCH_CLUE -> FREE_QUESTION
FREE_QUESTION -> FINAL_VOTE
FINAL_VOTE -> REVEAL_TRUTH
REVEAL_TRUTH -> END
```

说明：

* `FREE_QUESTION` 和 `SEARCH_CLUE` 可以来回切换
* 玩家在收集足够信息后，可以进入 `FINAL_VOTE`
* `FINAL_VOTE` 之后不能回到前面的阶段

### 8.5 设计原则

阶段流转必须由系统代码控制。

LLM 可以建议进入下一阶段，但最终是否流转由 `GameRuntime` 或 `RuleJudge` 决定。

---

## 9. Player：玩家

### 9.1 职责

`Player` 表示参与游戏的人类玩家。

### 9.2 字段设计

```text
player_id: str
display_name: str
```

### 9.3 第一版简化

第一版不做登录系统，所以 `Player` 可以使用临时 ID。

示例：

```json
{
  "player_id": "player_001",
  "display_name": "玩家"
}
```

### 9.4 后续扩展

后续多人在线版本可以扩展：

```text
avatar_url
role
connection_status
joined_at
is_host_player
```

---

## 10. Character：公开角色

### 10.1 职责

`Character` 表示剧本中的公开人物。

它只包含玩家可以知道的公开信息，不包含秘密、动机、谎言边界。

### 10.2 字段设计

```text
character_id: str
name: str
role: str
public_profile: str
is_npc: bool
```

### 10.3 字段说明

| 字段             | 说明              |
| -------------- | --------------- |
| character_id   | 角色唯一 ID         |
| name           | 角色名称            |
| role           | 角色身份，例如管家、医生、女儿 |
| public_profile | 公开人物介绍          |
| is_npc         | 是否由 AI 扮演       |

### 10.4 示例

```json
{
  "character_id": "npc_butler",
  "name": "林管家",
  "role": "管家",
  "public_profile": "在顾家服务二十年的老管家，熟悉庄园内的一切。",
  "is_npc": true
}
```

### 10.5 设计原则

`Character` 只存公开信息。

这些内容可以展示给玩家，也可以作为 NPC Agent 的基础身份信息。

---

## 11. NPCProfile：NPC 私有信息

### 11.1 职责

`NPCProfile` 表示某个 NPC 的私有角色设定。

它决定 NPC 在回答玩家问题时：

* 知道什么
* 想隐瞒什么
* 可以撒什么谎
* 不能知道什么
* 应该用什么风格说话

### 11.2 字段设计

```text
character_id: str
private_background: str
known_facts: list[str]
secrets: list[str]
lie_rules: list[str]
forbidden_knowledge: list[str]
personality: str
```

### 11.3 字段说明

| 字段                  | 含义              |
| ------------------- | --------------- |
| character_id        | 对应 Character ID |
| private_background  | NPC 私有背景        |
| known_facts         | NPC 确实知道的事实     |
| secrets             | NPC 想隐瞒的秘密      |
| lie_rules           | NPC 可以如何撒谎或回避   |
| forbidden_knowledge | NPC 明确不能知道的信息   |
| personality         | NPC 的语言风格和性格    |

### 11.4 示例

```json
{
  "character_id": "npc_butler",
  "private_background": "林管家发现死者生前正在修改遗嘱，但他并不知道真正的凶手。",
  "known_facts": [
    "案发当晚 21:50，他听到书房方向传来玻璃碎裂声。",
    "他看到医生在 21:40 左右离开过书房。"
  ],
  "secrets": [
    "他偷偷拿走过书房抽屉里的旧钥匙。"
  ],
  "lie_rules": [
    "如果玩家直接询问钥匙，可以先含糊其辞。",
    "如果玩家拿出钥匙相关线索，可以承认自己拿过钥匙。"
  ],
  "forbidden_knowledge": [
    "不能知道真正凶手是谁。",
    "不能知道毒药的完整来源。"
  ],
  "personality": "谨慎、克制、说话礼貌，但在被追问时会紧张。"
}
```

### 11.5 关键原则

NPC Agent 的上下文只能注入对应 NPC 的信息。

禁止注入：

* 完整 Truth
* 其他 NPC 的私有信息
* 系统隐藏线索
* 完整真相时间线

否则 NPC 很容易提前泄露谜底。

---

## 12. Clue：线索

### 12.1 职责

`Clue` 表示游戏中的一条线索。

线索是玩家推理的基础，也是剧本杀游戏最重要的交互资源之一。

### 12.2 字段设计

```text
clue_id: str
title: str
content: str
visibility: ClueVisibility
unlock_phase: GamePhase | None
related_character_ids: list[str]
is_key_clue: bool
```

### 12.3 字段说明

| 字段                    | 说明      |
| --------------------- | ------- |
| clue_id               | 线索唯一 ID |
| title                 | 线索标题    |
| content               | 线索内容    |
| visibility            | 初始可见性   |
| unlock_phase          | 默认解锁阶段  |
| related_character_ids | 关联角色    |
| is_key_clue           | 是否关键线索  |

### 12.4 ClueVisibility

```text
PUBLIC
LOCKED
HIDDEN
```

| 类型     | 说明              |
| ------ | --------------- |
| PUBLIC | 开局或背景阶段可见       |
| LOCKED | 达到阶段或条件后可解锁     |
| HIDDEN | 系统内部线索，玩家不可直接查看 |

### 12.5 示例

```json
{
  "clue_id": "clue_broken_glass",
  "title": "书房地毯上的玻璃碎片",
  "content": "书房地毯上有一片碎玻璃，边缘沾有少量深红色液体。",
  "visibility": "PUBLIC",
  "unlock_phase": "SEARCH_CLUE",
  "related_character_ids": ["npc_butler", "npc_doctor"],
  "is_key_clue": true
}
```

### 12.6 线索可见性判断

玩家是否可以查看某条线索，由以下因素共同决定：

* `Clue.visibility`
* `Clue.unlock_phase`
* `GameState.current_phase`
* `GameState.unlocked_clue_ids`

不要让 LLM 自己判断线索能不能展示。

### 12.7 第一版简化规则

第一版可以采用简单规则：

* `PUBLIC` 线索在 `BACKGROUND_INTRO` 后可见
* `LOCKED` 线索需要进入 `SEARCH_CLUE` 后由系统解锁
* `HIDDEN` 线索只供 Host 和 Judge 使用，玩家不可查看

---

## 13. EventLog：事件日志

### 13.1 职责

`EventLog` 记录游戏过程中发生的关键事件。

它用于：

* 游戏复盘
* Debug Agent 行为
* 判断玩家是否已经问过某类问题
* 后续构建记忆系统
* 后续做 Trace / Evaluation

### 13.2 字段设计

```text
event_id: str
room_id: str
event_type: str
actor_type: str
actor_id: str
content: str
created_at: datetime
```

### 13.3 event_type 示例

```text
GAME_STARTED
PHASE_CHANGED
QUESTION_ASKED
NPC_ANSWERED
CLUE_UNLOCKED
CLUE_VIEWED
FINAL_VOTE_SUBMITTED
TRUTH_REVEALED
GAME_ENDED
```

### 13.4 actor_type 示例

```text
SYSTEM
PLAYER
HOST_AGENT
NPC_AGENT
JUDGE_AGENT
CLUE_MANAGER
```

### 13.5 示例

```json
{
  "event_id": "event_001",
  "room_id": "room_001",
  "event_type": "QUESTION_ASKED",
  "actor_type": "PLAYER",
  "actor_id": "player_001",
  "content": "玩家向林管家询问案发当晚 22 点在哪里。",
  "created_at": "2026-05-25T12:00:00+09:00"
}
```

### 13.6 设计原则

第一版即使不做数据库，也必须保留内存事件日志。

因为 Agent 项目如果没有事件日志，后续很难解释：

* NPC 为什么这样回答
* 玩家之前问过什么
* 哪条线索何时解锁
* 游戏阶段为何变化
* 最终复盘依据是什么

---

## 14. Question：玩家提问

### 14.1 职责

`Question` 表示玩家向某个 NPC 提出的一个问题。

### 14.2 字段设计

```text
question_id: str
room_id: str
player_id: str
target_character_id: str
content: str
created_at: datetime
```

### 14.3 示例

```json
{
  "question_id": "question_001",
  "room_id": "room_001",
  "player_id": "player_001",
  "target_character_id": "npc_butler",
  "content": "案发当晚 22 点左右，你在哪里？",
  "created_at": "2026-05-25T12:05:00+09:00"
}
```

### 14.4 设计原则

玩家提问必须先落入系统记录，再交给 NPC Agent 生成回答。

推荐流程：

```text
玩家输入问题
  -> 创建 Question
  -> 记录 EventLog: QUESTION_ASKED
  -> 构造 NPCContext
  -> NPC Agent 生成候选回答
  -> Rule Judge 检查
  -> 生成 Answer
  -> 记录 EventLog: NPC_ANSWERED
```

---

## 15. Answer：NPC 回答

### 15.1 职责

`Answer` 表示 NPC 对玩家问题的回答。

### 15.2 字段设计

```text
answer_id: str
question_id: str
target_character_id: str
content: str
judge_result: JudgeResult
created_at: datetime
```

### 15.3 字段说明

| 字段                  | 说明         |
| ------------------- | ---------- |
| answer_id           | 回答 ID      |
| question_id         | 对应提问 ID    |
| target_character_id | 回答的 NPC    |
| content             | 最终展示给玩家的回答 |
| judge_result        | 裁判检查结果     |
| created_at          | 创建时间       |

### 15.4 设计原则

NPC 的原始回答不要直接展示给玩家。

必须先经过 Rule Judge 检查。

推荐流程：

```text
NPC Agent 生成 candidate_answer
  -> Rule Judge 检查是否越权
  -> ALLOWED: 展示给玩家
  -> NEEDS_REWRITE: 要求 NPC 重写
  -> VIOLATION: 拒绝并记录异常
```

---

## 16. JudgeResult：裁判判断结果

### 16.1 职责

`JudgeResult` 表示 Rule Judge 对某个行为或回答的判断。

### 16.2 字段设计

```text
allowed: bool
status: str
reason: str
suggested_action: str | None
```

### 16.3 status 示例

```text
ALLOWED
NEEDS_REWRITE
VIOLATION
PHASE_NOT_ALLOWED
CLUE_NOT_VISIBLE
```

### 16.4 示例

```json
{
  "allowed": false,
  "status": "NEEDS_REWRITE",
  "reason": "NPC 回答中提到了自己不应该知道的真凶身份。",
  "suggested_action": "rewrite_answer"
}
```

### 16.5 设计原则

JudgeResult 应尽量结构化，避免只有自然语言解释。

后续可以使用 Pydantic 模型约束 LLM 输出。

---

## 17. Vote：最终投票 / 推理

### 17.1 职责

`Vote` 表示玩家提交的最终推理答案。

### 17.2 字段设计

```text
suspect_character_id: str
motive: str
method: str
key_evidence: list[str]
submitted_at: datetime
```

### 17.3 字段说明

| 字段                   | 说明           |
| -------------------- | ------------ |
| suspect_character_id | 玩家认为的凶手      |
| motive               | 玩家认为的作案动机    |
| method               | 玩家认为的作案手法    |
| key_evidence         | 玩家引用的关键线索 ID |
| submitted_at         | 提交时间         |

### 17.4 示例

```json
{
  "suspect_character_id": "npc_doctor",
  "motive": "医生长期被死者勒索。",
  "method": "利用镇静剂让死者失去反抗能力，再制造意外假象。",
  "key_evidence": ["clue_medicine_bottle", "clue_torn_letter"],
  "submitted_at": "2026-05-25T13:00:00+09:00"
}
```

### 17.5 判断方式

第一版可以采用规则判断：

* 凶手是否匹配 `Truth.murderer_character_id`
* 关键证据是否命中 `Truth.key_clue_ids`
* 动机和手法暂时由 Host 或 Judge 用自然语言点评

后续可以加入更细的评分模型。

---

## 18. Truth：案件真相

### 18.1 职责

`Truth` 表示剧本真正答案。

这是最高敏感信息。

### 18.2 字段设计

```text
murderer_character_id: str
motive: str
method: str
key_clue_ids: list[str]
summary: str
```

### 18.3 示例

```json
{
  "murderer_character_id": "npc_doctor",
  "motive": "医生多年前的医疗事故被死者掌握，并长期遭到勒索。",
  "method": "医生利用镇静剂削弱死者反抗能力，再伪造书房争执后的意外死亡。",
  "key_clue_ids": ["clue_medicine_bottle", "clue_torn_letter"],
  "summary": "真正的凶手是医生。他利用自己熟悉药物的优势完成作案，并试图通过制造混乱把嫌疑引向管家。"
}
```

### 18.4 可见性原则

| 使用方          | 是否可访问 Truth            |
| ------------ | ---------------------- |
| Player       | 游戏结束前不可访问              |
| NPC Agent    | 默认不可访问                 |
| 真凶 NPC       | 只能知道自己参与的事实，不应获得完整系统真相 |
| Host Agent   | 可以访问                   |
| Rule Judge   | 可以访问                   |
| Clue Manager | 通常不需要完整 Truth          |

---

## 19. TimelineEvent：时间线事件

### 19.1 职责

`TimelineEvent` 表示案发相关时间线。

### 19.2 字段设计

```text
time: str
character_id: str | None
event: str
is_public: bool
```

### 19.3 示例

```json
{
  "time": "21:40",
  "character_id": "npc_doctor",
  "event": "医生进入书房，与死者发生争执。",
  "is_public": false
}
```

### 19.4 公开时间线与真相时间线

时间线分为两种：

| 类型    | 说明                     |
| ----- | ---------------------- |
| 公开时间线 | 玩家可以看到，通常不完整           |
| 真相时间线 | Host 和 Judge 可见，包含完整事实 |

### 19.5 设计原则

不要把完整时间线直接给 NPC。

NPC 只能知道自己看到、听到、参与过的部分事实。

---

## 20. GameRule：游戏规则

### 20.1 职责

`GameRule` 表示当前剧本或游戏模式下的规则。

第一版可以很简单，但需要保留规则概念。

### 20.2 字段设计

```text
rule_id: str
description: str
rule_type: str
```

### 20.3 rule_type 示例

```text
PHASE_RULE
CLUE_RULE
NPC_KNOWLEDGE_RULE
VOTE_RULE
```

### 20.4 示例

```json
{
  "rule_id": "rule_npc_no_truth_leak",
  "rule_type": "NPC_KNOWLEDGE_RULE",
  "description": "NPC 不能主动透露完整真相，也不能知道不属于自己视角的信息。"
}
```

---

## 21. 信息可见性规则

### 21.1 玩家可见信息

玩家可以看到：

```text
案件背景
公开角色信息
已解锁线索
NPC 对外回答
自己的提问历史
最终复盘
```

玩家不能看到：

```text
NPC 私有秘密
完整真相
隐藏线索
系统裁判规则细节
NPC forbidden_knowledge
完整真相时间线
```

### 21.2 NPC 可见信息

单个 NPC 可以看到：

```text
自己的公开角色信息
自己的 private_background
自己的 known_facts
自己的 secrets
自己的 lie_rules
自己的 personality
玩家当前问题
必要的对话历史摘要
```

单个 NPC 不能看到：

```text
完整 Truth
其他 NPC 的私有信息
未公开隐藏线索
系统完整时间线
其他 NPC 的内心动机
系统规则实现细节
```

### 21.3 Host 可见信息

Host 可以看到：

```text
完整 GameScript
完整 GameState
当前阶段
所有线索
最终真相
事件日志
玩家行为记录
```

Host 负责引导游戏，但也不能随意篡改状态。

### 21.4 Rule Judge 可见信息

Rule Judge 可以看到：

```text
完整 GameScript
完整 GameState
NPC 可见边界
玩家当前问题
NPC 候选回答
规则定义
```

Rule Judge 不负责生成剧情文案，只负责判断合法性。

### 21.5 Clue Manager 可见信息

Clue Manager 可以看到：

```text
全部 Clue 定义
当前 GamePhase
GameState.unlocked_clue_ids
玩家请求查看的 clue_id
```

Clue Manager 不需要知道完整推理真相，只需要判断线索是否可见。

---

## 22. Agent 上下文模型

### 22.1 HostContext

Host Agent 使用的上下文。

```text
script_title
background
characters
current_phase
game_state_summary
available_actions
truth
recent_events
```

### 22.2 NPCContext

NPC Agent 使用的上下文。

```text
character
npc_profile
current_question
conversation_summary
known_facts
secrets
lie_rules
forbidden_knowledge
```

禁止包含：

```text
truth
other_npc_profiles
hidden_clues
full_timeline
```

### 22.3 JudgeContext

Rule Judge 使用的上下文。

```text
current_phase
question
candidate_answer
npc_profile
truth
rules
forbidden_knowledge
```

### 22.4 PlayerView

展示给玩家的视图。

```text
background
public_characters
current_phase
visible_clues
recent_answers
available_actions
```

### 22.5 设计原则

Agent 上下文必须由代码组装，不能直接把完整 `GameScript` 扔给所有 Agent。

这一步是防止信息泄露的关键。

---

## 23. 第一版对象关系

```text
GameScript
  ├── Character[]
  ├── NPCProfile[]
  ├── Clue[]
  ├── Truth
  ├── TimelineEvent[]
  └── GameRule[]

GameRoom
  ├── Player
  └── GameState

GameState
  ├── current_phase
  ├── unlocked_clue_ids
  ├── Question[]
  ├── Answer[]
  ├── EventLog[]
  └── Vote

Question
  └── Answer

Vote
  └── compared with Truth
```

---

## 24. 关键业务流程

### 24.1 开始游戏

```text
load GameScript
  -> create Player
  -> create GameRoom
  -> create initial GameState
  -> write EventLog: GAME_STARTED
  -> change phase to BACKGROUND_INTRO
```

### 24.2 玩家询问 NPC

```text
player input question
  -> validate current_phase is FREE_QUESTION
  -> create Question
  -> write EventLog: QUESTION_ASKED
  -> build NPCContext
  -> NPC Agent generates candidate answer
  -> build JudgeContext
  -> Rule Judge checks candidate answer
  -> if allowed: create Answer
  -> if not allowed: rewrite or reject
  -> write EventLog: NPC_ANSWERED
  -> return Answer to player
```

### 24.3 玩家查看线索

```text
player requests clue
  -> validate current_phase allows clue view
  -> Clue Manager checks visibility
  -> if visible: return clue content
  -> if not visible: return denied message
  -> write EventLog: CLUE_VIEWED or CLUE_DENIED
```

### 24.4 解锁线索

```text
runtime checks phase or condition
  -> find unlockable clues
  -> update GameState.unlocked_clue_ids
  -> write EventLog: CLUE_UNLOCKED
```

### 24.5 提交最终推理

```text
player submits Vote
  -> validate current_phase is FINAL_VOTE
  -> save Vote into GameState
  -> compare with Truth
  -> write EventLog: FINAL_VOTE_SUBMITTED
  -> change phase to REVEAL_TRUTH
```

### 24.6 公布真相

```text
Host Agent reads Truth and EventLog
  -> generate truth reveal
  -> generate player reasoning review
  -> write EventLog: TRUTH_REVEALED
  -> change phase to END
```

---

## 25. 后续 Python 代码映射

建议第一版代码结构：

```text
mystery-agent-lab/
  game/
    __init__.py
    models.py
    script_loader.py
    state.py
    runtime.py
    clue_manager.py
    judge.py
  scripts/
    mansion_murder.json
  tests/
    test_models.py
    test_script_loader.py
    test_clue_manager.py
    test_runtime.py
```

### 25.1 models.py

存放领域模型：

```text
GameScript
GameRoom
GameState
GamePhase
Player
Character
NPCProfile
Clue
ClueVisibility
EventLog
Question
Answer
JudgeResult
Vote
Truth
TimelineEvent
GameRule
```

### 25.2 script_loader.py

负责：

```text
读取 JSON 剧本
校验必要字段
转换为 GameScript
```

### 25.3 state.py

负责：

```text
创建初始 GameState
阶段流转
记录问题
记录回答
记录事件
保存最终投票
```

### 25.4 runtime.py

负责：

```text
游戏主流程
接收玩家动作
调用对应服务
返回玩家可见结果
```

### 25.5 clue_manager.py

负责：

```text
判断线索是否可见
获取当前可见线索
解锁线索
```

### 25.6 judge.py

第一版可以先做规则判断，不接 LLM。

负责：

```text
判断当前阶段是否允许某动作
判断 NPC 回答是否包含 forbidden_knowledge
判断玩家最终答案是否命中真相
```

---

## 26. 第一版测试重点

### 26.1 模型测试

验证：

```text
GamePhase 枚举正确
ClueVisibility 枚举正确
GameState 初始化正确
```

### 26.2 剧本加载测试

验证：

```text
可以从 JSON 加载 GameScript
characters 不为空
clues 不为空
truth 不为空
npc_profiles 与 characters 能关联
```

### 26.3 线索管理测试

验证：

```text
PUBLIC 线索可见
LOCKED 线索未解锁前不可见
unlocked_clue_ids 中的线索可见
HIDDEN 线索对玩家不可见
```

### 26.4 状态流转测试

验证：

```text
START 可以进入 BACKGROUND_INTRO
BACKGROUND_INTRO 可以进入 FREE_QUESTION
FREE_QUESTION 可以进入 SEARCH_CLUE
FINAL_VOTE 后不能回到 FREE_QUESTION
END 后不能继续操作
```

### 26.5 NPC 信息边界测试

验证：

```text
NPCContext 不包含 truth
NPCContext 不包含其他 NPC profile
NPCContext 不包含 hidden clues
NPCContext 包含自己的 known_facts
NPCContext 包含自己的 forbidden_knowledge
```

---

## 27. 第一版不处理的问题

当前领域模型暂不处理：

```text
多人玩家身份
玩家阵营
玩家私聊
实时 WebSocket 房间
用户登录
房间持久化
断线恢复
剧本商城
付费机制
AI 自动生成剧本
复杂地图探索
物品系统
技能系统
语音输入输出
图片线索生成
长期用户画像
```

这些都属于后续阶段。

---

## 28. 后续扩展方向

### 28.1 多人在线

扩展对象：

```text
PlayerRole
RoomMember
PlayerAction
ChatMessage
ConnectionState
```

### 28.2 多 Agent 编排

扩展对象：

```text
AgentRole
AgentContext
AgentRun
AgentTrace
AgentDecision
```

### 28.3 RAG 剧本检索

扩展对象：

```text
ScriptChunk
KnowledgeScope
RetrievalQuery
RetrievedContext
```

### 28.4 剧本生成

扩展对象：

```text
GeneratedScriptDraft
CharacterArc
MotiveGraph
ClueGraph
LogicCheckReport
```

### 28.5 可观测性和评估

扩展对象：

```text
TraceSpan
EvaluationCase
LeakageCheckResult
AnswerQualityScore
```

---

## 29. 当前阶段完成标准

完成本文档后，需要能回答以下问题：

* [ ] 一局游戏有哪些核心对象
* [ ] 哪些对象是剧本静态定义
* [ ] 哪些对象是运行时状态
* [ ] GameState 保存什么
* [ ] GameScript 和 GameState 的边界是什么
* [ ] 玩家能看到哪些信息
* [ ] NPC 能看到哪些信息
* [ ] Host 和 Judge 为什么可以看到完整真相
* [ ] 线索如何控制可见性
* [ ] NPC 回答为什么需要 Judge 检查
* [ ] EventLog 为什么必须保留
* [ ] 后续 Python 代码应该如何映射这些模型

---

## 30. 本阶段结论

第一版 AI 在线剧本杀的核心不是「让 AI 随便聊天」，而是构建一个受控的互动推理系统。

因此领域模型的关键不是字段数量，而是三个边界：

1. **静态剧本与运行状态的边界**
2. **玩家、NPC、Host、Judge 的信息可见性边界**
3. **LLM 生成内容与系统确定性状态变更的边界**

只要这三个边界清楚，后续无论接入 LangGraph、LlamaIndex、Pydantic AI，还是自研轻量 Agent Runtime，系统都不会失控。
