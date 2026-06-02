from openai.types.chat import ChatCompletionMessageParam

from stery.npc.npc_context_builder import NPCContextBuilder
from stery.npc.npc_prompt_renderer import NPCPromptRenderer
from stery.domain.models import GameScript
from stery.domain.state import GameState
from stery.llm.base import LLMClient


class NPCAgent:
    """
    NPC Agent。

    职责：
    - 接收玩家问题
    - 构造目标 NPC 的上下文
    - 渲染 prompt
    - 调用 LLM
    - 返回 NPC 回答文本

    当前不负责：
    - 修改 GameState
    - 判断回答是否越权
    - 记录 Answer
    - 多 Agent 协作
    """

    def __init__(
        self,
        script: GameScript,
        llm_client: LLMClient,
        context_builder: NPCContextBuilder | None = None,
        prompt_renderer: NPCPromptRenderer | None = None,
    ):
        self.script = script
        self.llm_client = llm_client
        self.context_builder = context_builder or NPCContextBuilder(script)
        self.prompt_renderer = prompt_renderer or NPCPromptRenderer()

    def answer(
        self,
        state: GameState,
        target_character_id: str,
        player_question: str,
    ) -> str:
        context = self.context_builder.build(
            state=state,
            target_character_id=target_character_id,
            player_question=player_question,
        )

        prompt = self.prompt_renderer.render(context)

        messages: list[ChatCompletionMessageParam] = [
            {
                "role": "system",
                "content": "你是一个剧本杀 NPC 扮演引擎。你必须严格遵守角色信息边界。",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        return self.llm_client.think(messages)