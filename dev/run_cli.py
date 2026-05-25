from dotenv import load_dotenv

from stery.agents.npc_agent import NPCAgent
from stery.application import clue_search_service
from stery.application.game_runtime import GameRuntime
from stery.application.npc_interaction_service import NPCInteractionService
from stery.application.rule_judge import RuleJudge
from stery.application.script_loader import load_script
from stery.interfaces.cli import MysteryCliApp
from stery.llm.base import LLMClient
from stery.application.clue_search_service import ClueSearchService

load_dotenv()


def main() -> None:
    script = load_script("../scripts/mansion_murder.json")
    clue_search_service = ClueSearchService(script)
    runtime = GameRuntime(script)

    llm_client = LLMClient()
    npc_agent = NPCAgent(
        script=script,
        llm_client=llm_client,
    )

    npc_interaction_service = NPCInteractionService(
        runtime=runtime,
        npc_agent=npc_agent,
    )

    rule_judge = RuleJudge(script)

    app = MysteryCliApp(
        runtime=runtime,
        npc_interaction_service=npc_interaction_service,
        rule_judge=rule_judge,
        clue_search_service=clue_search_service
    )

    app.run()


if __name__ == "__main__":
    main()
