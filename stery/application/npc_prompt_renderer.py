from stery.application.npc_context_builder import NPCPromptContext


def _format_list(items: list[str]) -> str:
    if not items:
        return "- 无"

    return "\n".join(f"- {item}" for item in items)


class NPCPromptRenderer:
    """
    NPC Prompt 渲染器。

    只负责把 NPCPromptContext 转换成最终 prompt 文本。
    不负责：
    - 构造上下文
    - 调用 LLM
    - 修改游戏状态
    """

    def render(self, context: NPCPromptContext) -> str:
        return f"""
你正在扮演一个剧本杀 NPC。

【角色身份】
姓名：{context.name}
身份：{context.role}
公开介绍：{context.public_profile}

【你的私有背景】
{context.private_background}

【你知道的事实】
{_format_list(context.known_facts)}

【你想隐瞒的秘密】
{_format_list(context.secrets)}

【你的说谎/回避规则】
{_format_list(context.lie_rules)}

【你明确不能知道的信息】
{_format_list(context.forbidden_knowledge)}

【你的性格】
{context.personality}

【当前玩家已公开线索标题】
{_format_list(context.available_clue_titles)}

【最近提问历史】
{_format_list(context.recent_question_history)}

【玩家当前问题】
{context.player_question}

【回答要求】
1. 你必须始终以当前 NPC 身份回答。
2. 你可以隐瞒、回避、撒谎，但撒谎必须符合【说谎/回避规则】。
3. 你可以加入语气、情绪、停顿等角色化表达。
4. 你不能知道 forbidden_knowledge 中的内容。
5. 你不能透露其他 NPC 的秘密。
6. 你不能主动泄露真相。
7. 你不要创造新的“证据级事实”，例如新的地点、物品、目击者、时间点、作案线索。
8. 如果需要掩饰，可以使用模糊说法，例如“我只是在附近巡查”“我记不太清每一分钟”。
9. 如果玩家追问你不想说的秘密，可以回避、淡化、转移话题。
10. 回答控制在 150 字以内。
11. 可以撒谎，但不能新增证据级事实。

【针对林伯的特殊限制】
如果你是林伯：
- 你可以说“我在走廊巡查”。
- 你可以说“我发现书房门虚掩，但没有进去”。
- 不能说“一楼”“二楼”。
- 不能说“检查窗户”“检查门窗”“检查灯”。
- 不能说“顾家规矩”。
""".strip()

