# ChatGPT 剧本生成使用手册

## 1. 手册目的

本文档用于说明如何使用 ChatGPT 根据《Mystery Agent Lab V0.2.0 剧本生成规则 v1.0》生成可运行、可调查、可评分的剧本。

目标不是让 ChatGPT 生成一篇小说，而是生成一份符合项目 V0.2.0 协议的 GameScript 数据。

生成后的剧本应满足：

1. 可以被项目 GameScript 模型加载。
2. 玩家可以通过调查对象发现线索。
3. NPC 不直接泄露真凶和完整作案手法。
4. 最终推理可以通过 RuleJudge 确定性评分。
5. 剧本中的 ID、线索、调查对象、真相字段引用一致。
6. 不引入 Tool、Agent Runtime、地图系统、复杂触发规则或 LLMJudge。

---

## 2. 使用前准备

使用 ChatGPT 生成剧本前，建议准备以下文档：

```text
docs/script-generation/v0.2.0-script-generation-rules-v1.0.md
docs/v0.2.0-investigation-mvp-plan.md
```

其中最重要的是：

```text
v0.2.0-script-generation-rules-v1.0.md
```

这份文档定义了：

1. 剧本创作规则。
2. V0.2.0 GameScript 运行协议。
3. 生成后校验规则。
4. Prompt 模板。
5. 版本边界。

---

## 3. 推荐使用流程

不要一上来就让 ChatGPT 直接生成完整 JSON。

推荐使用三步法：

```text
第一步：生成剧本设计草案
第二步：生成 V0.2.0 GameScript JSON
第三步：执行自检并修复 JSON
```

原因：

1. 先看设计，能提前发现故事逻辑问题。
2. 再生成 JSON，能降低字段混乱风险。
3. 最后自检，能修复 ID 引用、线索闭环、评分字段等问题。
4. 避免生成“剧情很好看，但代码跑不起来”的剧本。

---

## 4. V0.2.0 推荐剧本规模

V0.2.0 当前目标是验证调查机制 MVP，不建议一开始生成超大型剧本。

推荐规模：

```text
NPC 数量：4～6 个
线索数量：10～16 条
调查对象：6～10 个
关键证据：4～6 条
红鲱鱼：1～2 个
游玩时长：30～60 分钟
难度：简单到中等偏难
```

不推荐默认生成：

```text
10 人以上复杂剧本
20 条以上线索
多凶手剧本
复杂地图剧本
多阶段触发剧本
强依赖 HIDDEN 线索的剧本
```

10 人以上复杂剧本可以作为后续压力测试，不作为 V0.2.0 默认样例。

---

## 5. 第一步：让 ChatGPT 生成剧本设计草案

### 5.1 使用场景

当你有一个题材想法时，先让 ChatGPT 生成设计草案。

例如：

```text
我要一个赛博朋克风格、密室杀人、6 个 NPC、中等偏难、复杂关系但不超过 V0.2.0 默认规模的剧本。
```

### 5.2 Prompt 模板

将下面内容复制给 ChatGPT：

```text
你现在是 Mystery Agent Lab 的剧本生成助手。

我已经上传了一份《V0.2.0 剧本生成规则 v1.0》。请先阅读并遵守这份规则。

现在不要直接生成完整 JSON，先根据我的需求生成一份“剧本设计草案”。

我的剧本需求如下：

【题材风格】
赛博朋克

【案件类型】
密室杀人

【人物规模】
6 个 NPC 左右，不要超过 V0.2.0 默认推荐规模

【关系复杂度】
中等偏复杂，有隐藏关系和误导动机

【推理难度】
中等偏难

【游玩时长】
约 45～60 分钟

【特殊要求】
1. 玩家必须能通过调查地点、尸体、物品发现关键线索。
2. /search 只作为已知信息检索，不作为主要线索解锁方式。
3. NPC 不能直接泄露真凶和完整作案手法。
4. 必须有唯一真凶。
5. 必须能通过确定性规则评分。
6. 不要引入 Tool、Agent Runtime、地图系统、复杂触发规则或 LLMJudge。

请先输出以下内容：

1. 剧本标题
2. 案件背景摘要
3. 死者设定
4. 主要 NPC 列表
5. 人物关系摘要
6. 表面谜面
7. 真相摘要
8. 作案动机
9. 作案手法
10. 密室机制
11. 关键证据链
12. 红鲱鱼设计
13. 调查对象规划
14. 预计 clues 数量
15. 预计 investigation_targets 数量
16. 自检：这个设计是否符合 V0.2.0 规则
```

### 5.3 你需要检查什么

拿到草案后，重点检查：

```text
[ ] 是否只有一个真凶
[ ] 案件是否能通过线索推出
[ ] 手法是否有物证支撑
[ ] 动机是否有证言或背景支撑
[ ] 密室机制是否可解释
[ ] NPC 是否没有直接泄露真相
[ ] 关键线索是否能通过调查对象发现
[ ] 剧本规模是否没有过大
```

如果草案不合理，先让 ChatGPT 修改草案，不要进入 JSON 阶段。

---

## 6. 第二步：生成 V0.2.0 GameScript JSON

### 6.1 使用场景

当你确认剧本设计草案合理后，再让 ChatGPT 生成完整 GameScript JSON。

### 6.2 Prompt 模板

将下面内容复制给 ChatGPT：

```text
基于上一步确认的剧本设计草案，请生成符合 Mystery Agent Lab V0.2.0 运行协议的完整 GameScript JSON。

要求：

1. 顶层字段保持扁平结构。
2. 只使用以下顶层字段：
   - id
   - title
   - version
   - genre
   - difficulty
   - estimated_minutes
   - background
   - rules
   - characters
   - npc_profiles
   - clues
   - investigation_targets
   - truth
   - timeline
3. 不要新增 metadata 顶层对象。
4. 不要新增 public_intro 顶层对象。
5. relationships 不是 V0.2.0 必填运行字段，不要作为核心字段输出。
6. characters 只放玩家可见信息。
7. npc_profiles 放私有信息、秘密、撒谎规则、禁知信息、性格、不在场声明、可能动机。
8. clues 必须包含 id、title、content、visibility。
9. clue_type、importance、related_target_ids、reasoning_tags、search_keywords 都是可选字段。
10. investigation_targets 必须包含 id、name、type、description、search_keywords、discoverable_clue_ids。
11. investigation_targets 的 type 只能是 ROOM、BODY、ITEM。
12. LOCKED 线索应主要通过 investigation_targets 发现。
13. HIDDEN 线索不能作为 V0.2.0 主线推理必需线索。
14. truth 必须包含：
    - murderer_id
    - motive
    - method
    - key_evidence_ids
    - motive_keywords
    - method_keywords
    - explanation
15. rules.scoring 必须包含：
    - murderer_score
    - key_evidence_score
    - motive_score
    - method_score
16. rules.scoring 总分必须为 100。
17. 输出必须是合法 JSON，不要添加 Markdown 代码块外的解释。
```

### 6.3 生成后不要立即使用

ChatGPT 生成 JSON 后，不要直接放进项目运行。

必须先进入第三步自检。

原因：

```text
LLM 可能生成不存在的 clue_id。
LLM 可能让 murderer_id 指向不存在人物。
LLM 可能让 investigation_targets 引用不存在的线索。
LLM 可能把 HIDDEN 线索作为主线关键证据。
LLM 可能把 NPC 私有信息写进 characters。
LLM 可能生成不合法 JSON。
```

---

## 7. 第三步：让 ChatGPT 校验并修复 JSON

### 7.1 使用场景

拿到完整 JSON 后，让 ChatGPT 根据规则自检并修复。

### 7.2 Prompt 模板

将下面内容复制给 ChatGPT：

```text
请根据《V0.2.0 剧本生成规则 v1.0》校验上面这份 GameScript JSON。

请重点检查：

1. 顶层字段是否符合 V0.2.0 运行协议。
2. 是否错误使用了 metadata 或 public_intro 顶层对象。
3. characters 中是否混入了 NPC 私有信息。
4. npc_profiles 是否正确承载私有信息、秘密、撒谎规则和 forbidden_knowledge。
5. murderer_id 是否存在于 characters。
6. truth.key_evidence_ids 是否全部存在于 clues。
7. truth.motive_keywords 是否存在且可用于评分。
8. truth.method_keywords 是否存在且可用于评分。
9. rules.scoring 是否存在且总分为 100。
10. investigation_targets 中的 discoverable_clue_ids 是否全部存在于 clues。
11. LOCKED 线索是否能通过 investigation_targets 发现。
12. HIDDEN 线索是否没有承担主线推理必需作用。
13. PUBLIC 线索是否没有直接泄露真凶或完整手法。
14. NPC 证言是否没有直接泄露真凶或完整手法。
15. 关键证据是否分散在 BODY、ROOM、ITEM 等调查对象中。
16. 是否存在一个调查对象一次性解锁过多关键线索的问题。
17. 是否存在真相无法从线索推出的问题。
18. 是否存在红鲱鱼无法反证的问题。

请按以下格式输出：

一、校验结论：通过 / 不通过

二、问题列表：
- 问题位置
- 问题描述
- 风险
- 修改建议

三、修复后的完整 JSON

四、最终自检清单
```

### 7.3 自检通过后再保存

自检通过后，将修复后的 JSON 保存到项目剧本目录。

文件名建议：

```text
scripts/{script_id}.json
```

例如：

```text
scripts/neon_tower_locked_room.json
```

---

## 8. 第四步：人工检查重点

即使 ChatGPT 自检通过，也建议人工再检查以下内容。

### 8.1 ID 引用检查

```text
[ ] characters[].id 是否唯一
[ ] npc_profiles[].character_id 是否存在于 characters
[ ] clues[].id 是否唯一
[ ] investigation_targets[].id 是否唯一
[ ] investigation_targets[].discoverable_clue_ids 是否都存在于 clues
[ ] truth.murderer_id 是否存在于 characters
[ ] truth.key_evidence_ids 是否都存在于 clues
```

### 8.2 可玩性检查

```text
[ ] 玩家开局是否知道发生了什么
[ ] 玩家是否知道可以调查什么
[ ] 关键线索是否能通过 /investigate 发现
[ ] NPC 回答是否能提供推理材料
[ ] 红鲱鱼是否能被后续线索反证
[ ] 真相是否可以从已发现线索推出
```

### 8.3 评分检查

```text
[ ] rules.scoring 总分是否为 100
[ ] motive_keywords 是否能命中合理玩家答案
[ ] method_keywords 是否能命中合理玩家答案
[ ] method_keywords 是否能避免错误答案误判
[ ] key_evidence_ids 是否确实是关键证据
```

### 8.4 NPC 不泄底检查

```text
[ ] NPC 是否没有直接说出真凶
[ ] NPC 是否没有直接说出完整作案手法
[ ] NPC 是否没有知道自己不该知道的信息
[ ] NPC 的怀疑是否来自自身信息、偏见或误导，而不是上帝视角
```

---

## 9. 第五步：放入项目运行验证

### 9.1 保存剧本文件

将 JSON 保存到项目脚本目录。

示例：

```text
scripts/neon_tower_locked_room.json
```

具体目录以当前项目实际 ScriptRepository 配置为准。

### 9.2 运行 CLI

示例命令：

```bash
python run_cli.py --script neon_tower_locked_room
```

或者按当前项目实际命令执行。

### 9.3 验证流程

至少完整跑一遍：

```text
1. 启动剧本
2. 查看背景和公开线索
3. 使用 /investigate 调查地点
4. 使用 /investigate 调查尸体
5. 使用 /investigate 调查物品
6. 使用 /ask 询问 NPC
7. 使用 /search 搜索已知信息
8. 使用 /case 查看案件笔记本
9. 使用 /review 查看行为记录
10. 使用 /submit 提交推理
11. 查看 score_breakdown
12. 导出 JSON / Markdown
```

### 9.4 验证结果记录

建议记录：

```text
[ ] 剧本是否成功加载
[ ] CLI 是否正常显示背景
[ ] /investigate 是否能发现线索
[ ] /ask 是否能正常问 NPC
[ ] /search 是否只搜索已知信息
[ ] /case 是否能展示笔记本
[ ] /submit 是否能完成评分
[ ] score_breakdown 是否合理
[ ] JSON / Markdown 是否能导出
```

---

## 10. 常见错误与处理方式

### 10.1 生成了 metadata / public_intro 顶层对象

问题：

```text
V0.2.0 当前运行协议不需要 metadata / public_intro 顶层对象。
```

处理：

```text
让 ChatGPT 改成扁平结构。
metadata 中的信息拆到 id、title、version、genre、difficulty、estimated_minutes。
public_intro 改成 background。
```

---

### 10.2 characters 里混入私密信息

错误示例：

```json
{
  "id": "npc_doctor",
  "name": "周医生",
  "public_profile": "私人医生",
  "secret": "他就是凶手"
}
```

处理：

```text
characters 只放玩家可见信息。
secret、private_background、lie_rules、forbidden_knowledge 移到 npc_profiles。
```

---

### 10.3 murderer_id 不存在

问题：

```text
truth.murderer_id 指向了不存在的人物 ID。
```

处理：

```text
统一 characters[].id 和 truth.murderer_id。
```

---

### 10.4 key_evidence_ids 引用不存在

问题：

```text
truth.key_evidence_ids 中的 clue_id 在 clues 中不存在。
```

处理：

```text
补充对应 clue，或者从 key_evidence_ids 中移除错误 ID。
```

---

### 10.5 LOCKED 线索无法发现

问题：

```text
某些 LOCKED 线索没有绑定到任何 investigation_targets。
```

处理：

```text
将关键 LOCKED 线索加入某个 investigation_target.discoverable_clue_ids。
```

---

### 10.6 HIDDEN 线索承担主线推理

问题：

```text
truth.key_evidence_ids 中包含 HIDDEN 线索。
```

处理：

```text
V0.2.0 不应依赖 HIDDEN 线索完成主线推理。
将关键证据改为 PUBLIC 或 LOCKED，并通过 investigation_targets 发现。
```

---

### 10.7 investigation_target 一次性解锁太多线索

问题：

```text
玩家调查一个对象就获得全部关键线索。
```

处理：

```text
将关键线索分散到 BODY、ROOM、ITEM 多类对象中。
普通对象建议解锁 1～3 条线索。
核心对象最多 4 条线索。
```

---

### 10.8 method_keywords 太窄

问题：

```text
真实手法是“下药”，但 method_keywords 只有“镇静剂”，玩家写“在酒里下药”可能无法得分。
```

处理：

```text
补充常见表达。
例如：
"method_keywords": ["镇静剂", "红酒", "投药", "下药", "酒"]
```

注意：

```text
V0.2.0 暂时使用简单关键词数组，不实现 keyword_groups。
```

---

## 11. 推荐的一次完整操作示例

### 11.1 用户需求

```text
我要一个赛博朋克风格、6 个 NPC、密室杀人、中等偏难、复杂关系但不超过 V0.2.0 默认规模的剧本。要求玩家能通过调查尸体、房间、物品发现关键线索，最终能用 rules.scoring 和 truth keywords 做确定性评分。
```

### 11.2 第一次发给 ChatGPT

先发“生成草案 Prompt”。

### 11.3 草案确认后

再发“生成 GameScript JSON Prompt”。

### 11.4 JSON 生成后

再发“校验并修复 Prompt”。

### 11.5 保存修复后的 JSON

保存为：

```text
scripts/neon_tower_locked_room.json
```

### 11.6 本地运行验证

执行：

```bash
python run_cli.py --script neon_tower_locked_room
```

---

## 12. 不推荐的使用方式

不要这样直接问：

```text
给我一个赛博朋克剧本。
```

问题：

```text
没有限制字段协议。
没有指定 V0.2.0。
没有要求 investigation_targets。
没有要求 rules.scoring。
没有要求 truth keywords。
没有要求 JSON 合法。
没有要求自检。
```

更好的问法：

```text
请基于《V0.2.0 剧本生成规则 v1.0》，先生成一个剧本设计草案，不要直接生成 JSON。
题材是赛博朋克，案件类型是密室杀人，NPC 数量 6 个左右，要求通过 investigation_targets 发现关键线索，并支持确定性评分。
```

---

## 13. 使用原则总结

使用 ChatGPT 生成剧本时，记住以下原则：

```text
先草案，后 JSON，再自检。
先保证可运行，再追求复杂。
先控制规模，再做压力测试。
先保证线索闭环，再写文学表达。
先保证确定性评分，再考虑 LLMJudge。
```

V0.2.0 阶段最重要的不是生成大剧本，而是验证：

```text
玩家能通过调查对象发现线索，并基于轻量案件笔记完成一次可解释评分的推理。
```
