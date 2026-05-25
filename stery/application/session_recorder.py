import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from stery.config.paths import SESSIONS_DIR
from stery.domain.models import GameScript
from stery.domain.state import GameState


class SessionRecordResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    session_id: str
    json_path: Path
    markdown_path: Path


def _build_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = ["# Game Session Report", "", "## Script", "", f"- ID: {payload['script_id']}",
                        f"- Title: {payload['script_title']}", "", "## Time", "",
                        f"- Started At: {payload['started_at']}", f"- Ended At: {payload['ended_at']}", "",
                        "## Progress", "", f"- Current Phase: {payload['current_phase']}",
                        f"- Current Round: {payload['current_round']}", f"- Is Finished: {payload['is_finished']}",
                        "", "## Unlocked Clues", ""]

    unlocked_clue_ids = payload.get("unlocked_clue_ids") or []

    if not unlocked_clue_ids:
        lines.append("- 无")
    else:
        for clue_id in unlocked_clue_ids:
            lines.append(f"- {clue_id}")

    lines.append("")

    lines.append("## NPC Interactions")
    lines.append("")

    answer_history = payload.get("answer_history") or []

    if not answer_history:
        lines.append("- 无")
    else:
        for index, item in enumerate(answer_history, start=1):
            target_character_id = item.get("target_character_id", "")
            question = item.get("question", "")
            npc_answer = item.get("npc_answer", "")

            lines.append(f"### Interaction {index}")
            lines.append("")
            lines.append(f"- NPC: {target_character_id}")
            lines.append(f"- Q: {question}")
            lines.append(f"- A: {npc_answer}")
            lines.append("")

    lines.append("## Final Vote")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(payload.get("final_vote"), ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")

    lines.append("## Judge Result")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(payload.get("judge_result"), ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    markdown = _build_markdown(payload)
    path.write_text(markdown, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _build_session_id(script_id: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{script_id}-{timestamp}"


class SessionRecorder:
    """
    游戏会话记录器。

    职责：
    - 将一局游戏的最终状态导出为 JSON
    - 将一局游戏的最终状态导出为 Markdown
    - 用于人工复盘、测试分析、后续 Web/API 复用

    不负责：
    - 数据库存档
    - 断点恢复
    - 用户账号
    - 多局历史查询
    """

    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or SESSIONS_DIR

    def save(
        self,
        script: GameScript,
        state: GameState,
        judge_result: Any | None = None,
    ) -> SessionRecordResult:
        self.output_dir.mkdir(parents=True, exist_ok=True)

        session_id = _build_session_id(state.script_id)

        payload = self._build_payload(
            session_id=session_id,
            script=script,
            state=state,
            judge_result=judge_result,
        )

        json_path = self.output_dir / f"{session_id}.json"
        markdown_path = self.output_dir / f"{session_id}.md"

        _write_json(json_path, payload)
        _write_markdown(markdown_path, payload)

        return SessionRecordResult(
            session_id=session_id,
            json_path=json_path,
            markdown_path=markdown_path,
        )

    def _build_payload(
        self,
        session_id: str,
        script: GameScript,
        state: GameState,
        judge_result: Any | None,
    ) -> dict[str, Any]:
        return {
            "session_id": session_id,
            "script_id": state.script_id,
            "script_title": getattr(script, "title", ""),
            "started_at": self._to_json_value(state.created_at),
            "ended_at": self._to_json_value(state.updated_at),
            "current_phase": self._to_json_value(state.current_phase),
            "current_round": state.current_round,
            "is_finished": state.is_finished,
            "unlocked_clue_ids": sorted(state.unlocked_clue_ids),
            "question_history": self._to_json_value(state.question_history),
            "answer_history": self._to_json_value(state.answer_history),
            "final_vote": self._to_json_value(state.final_vote),
            "judge_result": self._to_json_value(judge_result),
        }

    def _to_json_value(self, value: Any) -> Any:
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, set):
            return sorted(value)

        if isinstance(value, list):
            return [self._to_json_value(item) for item in value]

        if isinstance(value, tuple):
            return [self._to_json_value(item) for item in value]

        if isinstance(value, dict):
            return {
                str(key): self._to_json_value(item)
                for key, item in value.items()
            }

        if isinstance(value, BaseModel):
            return self._to_json_value(value.model_dump(mode="json"))

        if hasattr(value, "value"):
            return value.value

        return value