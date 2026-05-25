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

    llm_client = LLMClient()
    agent = NPCAgent(script=script, llm_client=llm_client)

    player_question = "案发当晚 22 点左右，你在哪里？"

    runtime.record_question(
        target_character_id="npc_butler",
        question=player_question,
    )

    answer = agent.answer(
        state=state,
        target_character_id="npc_butler",
        player_question=player_question,
    )

    runtime.record_npc_answer(
        target_character_id="npc_butler",
        answer=answer,
    )

    print("NPC 回答：")
    print(answer)

    print("\n当前问答历史：")
    print(state.question_history)
    print(state.answer_history)


if __name__ == "__main__":
    main()