from bootstrap import bootstrap_project
from stery.clue import ClueSearchService

bootstrap_project()
from dotenv import load_dotenv
import argparse
from stery.agents import NPCAgent
from stery.application.game_runtime import GameRuntime
from stery.npc.npc_interaction_service import NPCInteractionService
from stery.judge.rule_judge import RuleJudge
from stery.interfaces.cli import MysteryCliApp
from stery.llm.base import LLMClient
from stery.config.paths import ENV_FILE
from stery.script_repository import LocalFileScriptRepository, ScriptRepository

load_dotenv(ENV_FILE)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--script",
        required=False,
        help="剧本 ID，例如 mansion_murder，对应 scripts/mansion_murder.json",
    )

    parser.add_argument(
        "--list-scripts",
        action="store_true",
        help="列出当前可用剧本",
    )

    args = parser.parse_args()

    repository = LocalFileScriptRepository()
    if args.list_scripts:
        print_available_scripts(repository)
        return

    if not args.script:
        parser.print_help()
        print()
        print_available_scripts(repository)
        return

    script = repository.get_script(args.script)
    clue_search_service = ClueSearchService(script)
    runtime = GameRuntime(script)

    llm_client = LLMClient()
    npc_agent = NPCAgent(
        script=script,
        llm_client=llm_client,
    )

    npc_interaction_service = NPCInteractionService(
        state_provider=lambda: runtime.state,
        responder=npc_agent,
        record_npc_answer=runtime.record_npc_answer,
        record_question=runtime.record_question
    )

    rule_judge = RuleJudge(script)

    app = MysteryCliApp(
        runtime=runtime,
        npc_interaction_service=npc_interaction_service,
        rule_judge=rule_judge,
        clue_search_service=clue_search_service
    )

    app.run()


def print_available_scripts(repository: ScriptRepository) -> None:
    scripts = repository.list_scripts()

    if not scripts:
        print("当前没有可用剧本。")
        return

    print("可用剧本：")
    for script_id in scripts:
        print(f"- {script_id}")


if __name__ == "__main__":
    main()
