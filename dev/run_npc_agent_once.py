from bootstrap import bootstrap_project

bootstrap_project()
from dotenv import load_dotenv

from stery.agents.npc_agent import NPCAgent
from stery.application.game_runtime import GameRuntime
from stery.application.npc_interaction_service import NPCInteractionService
from stery.application.script_loader import load_script
from stery.llm.base import LLMClient

from stery.config.paths import ENV_FILE, MANSION_MURDER_SCRIPT

load_dotenv(ENV_FILE)


def main():
    script = load_script(MANSION_MURDER_SCRIPT)

    runtime = GameRuntime(script)
    runtime.start()

    llm_client = LLMClient(temperature=0.1)
    npc_agent = NPCAgent(script=script, llm_client=llm_client)

    service = NPCInteractionService(
        runtime=runtime,
        npc_agent=npc_agent,
    )

    result = service.ask_npc(
        target_character_id="npc_butler",
        question="案发当晚 22 点左右，你在哪里？",
    )

    print("NPC 回答：")
    print(result.npc_answer)

    print("\n本轮交互：")
    print(result)

    print("\n当前状态：")
    print(runtime.state)


if __name__ == "__main__":
    main()