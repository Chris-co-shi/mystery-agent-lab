from dotenv import load_dotenv

from stery.agents.npc_agent import NPCAgent
from stery.application.game_runtime import GameRuntime
from stery.application.script_loader import load_script
from stery.llm.base import LLMClient

load_dotenv()


def main():
    script = load_script("../scripts/mansion_murder.json")

    runtime = GameRuntime(script)
    state = runtime.start()

    llm_client = LLMClient(temperature=0.2)
    agent = NPCAgent(script=script, llm_client=llm_client)

    answer = agent.answer(
        state=state,
        target_character_id="npc_butler",
        player_question="案发当晚 22 点左右，你在哪里？",
    )

    print("NPC 回答：")
    print(answer)


if __name__ == "__main__":
    main()