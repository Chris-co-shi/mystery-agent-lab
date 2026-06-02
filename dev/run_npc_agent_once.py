import argparse

from bootstrap import bootstrap_project


bootstrap_project()
from dotenv import load_dotenv

from stery.agents.npc_agent import NPCAgent
from stery.application.game_runtime import GameRuntime
from stery.application.npc_interaction_service import NPCInteractionService
from stery.llm.base import LLMClient

from stery.config.paths import ENV_FILE
from stery.script_repository import LocalFileScriptRepository
load_dotenv(ENV_FILE)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--script",
        required=True,
        help="剧本 ID，例如 mansion_murder，对应 scripts/mansion_murder.json",
    )

    args = parser.parse_args()

    repository = LocalFileScriptRepository()
    script = repository.get_script(args.script)

    runtime = GameRuntime(script)
    runtime.start()

    llm_client = LLMClient(temperature=0.1)
    npc_agent = NPCAgent(script=script, llm_client=llm_client)

    service = NPCInteractionService(
        state_provider=lambda: runtime.state,
        responder=npc_agent,
        record_npc_answer=runtime.record_npc_answer,
        record_question=runtime.record_question
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