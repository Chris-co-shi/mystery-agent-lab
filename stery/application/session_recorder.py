import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from stery.config.paths import SESSIONS_DIR
from stery.domain.models import GameScript
from stery.domain.state import GameState
from stery.utils import sanitize_text


class SessionRecordResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    session_id: str
    json_path: Path
    markdown_path: Path


def _build_case_records_markdown(payload: dict[str, Any]) -> list[str]:
    lines: list[str] = [
        "## Case Records",
        "",
    ]

    case_records = payload.get("case_records") or []

    if not case_records:
        lines.append("- 无")
        lines.append("")
        return lines

    for index, record in enumerate(case_records, start=1):
        title = record.get("title", "")
        summary = record.get("summary", "")
        action_type = record.get("action_type", "")
        metadata = record.get("metadata") or {}

        lines.append(f"### {index}. {title}")
        lines.append("")
        lines.append(f"- Type: {action_type}")

        if summary:
            lines.append("- Summary:")
            for line in str(summary).splitlines():
                lines.append(f"  {line}")

        if metadata:
            lines.append("- Metadata:")
            lines.append("```json")
            lines.append(json.dumps(metadata, ensure_ascii=False, indent=2))
            lines.append("```")

        lines.append("")

    return lines


def _build_unlocked_clues_markdown(payload: dict[str, Any]) -> list[str]:
    lines: list[str] = [
        "## Unlocked Clues",
        "",
    ]

    unlocked_clue_ids = payload.get("unlocked_clue_ids") or []

    if not unlocked_clue_ids:
        lines.append("- 无")
    else:
        for clue_id in unlocked_clue_ids:
            lines.append(f"- {clue_id}")

    lines.append("")
    return lines


def _build_final_vote_markdown(payload: dict[str, Any]) -> list[str]:
    return [
        "## Final Vote",
        "",
        "```json",
        json.dumps(payload.get("final_vote"), ensure_ascii=False, indent=2),
        "```",
        "",
    ]

def _build_judge_result_markdown(payload: dict[str, Any]) -> list[str]:
    return [
        "## Judge Result",
        "",
        "```json",
        json.dumps(payload.get("judge_result"), ensure_ascii=False, indent=2),
        "```",
        "",
    ]

def _build_npc_interactions_markdown(payload: dict[str, Any]) -> list[str]:
    lines: list[str] = [
        "## NPC Interactions",
        "",
    ]

    interactions = payload.get("npc_interactions") or []

    if not interactions:
        lines.append("- 无")
        lines.append("")
        return lines

    for index, item in enumerate(interactions, start=1):
        target_character_id = item.get("target_character_id", "")
        question = item.get("question", "")
        npc_answer = item.get("npc_answer") or "<暂无回答记录>"

        lines.append(f"### Interaction {index}")
        lines.append("")
        lines.append(f"- NPC: {target_character_id}")
        lines.append(f"- Q: {question}")
        lines.append(f"- A: {npc_answer}")
        lines.append("")

    return lines

def _build_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Game Session Report",
        "",
        "## Script",
        "",
        f"- ID: {payload['script_id']}",
        f"- Title: {payload['script_title']}",
        "",
        "## Time",
        "",
        f"- Started At: {payload['started_at']}",
        f"- Ended At: {payload['ended_at']}",
        "",
        "## Progress",
        "",
        f"- Current Phase: {payload['current_phase']}",
        f"- Is Finished: {payload['is_finished']}",
        "",
    ]

    lines.extend(_build_case_records_markdown(payload))
    lines.extend(_build_unlocked_clues_markdown(payload))
    lines.extend(_build_npc_interactions_markdown(payload))
    lines.extend(_build_final_vote_markdown(payload))
    lines.extend(_build_judge_result_markdown(payload))

    return "\n".join(lines)


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    safe_payload = sanitize_text(payload)
    markdown = _build_markdown(safe_payload)
    markdown = sanitize_text(markdown)

    path.write_text(markdown, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    safe_payload = sanitize_text(payload)
    path.write_text(
        json.dumps(safe_payload, ensure_ascii=False, indent=2),
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
            "is_finished": state.is_finished,
            "unlocked_clue_ids": sorted(state.unlocked_clue_ids),
            "case_records": self._to_json_value(state.case_records),
            "question_history": self._to_json_value(state.question_history),
            "answer_history": self._to_json_value(state.answer_history),
            "npc_interactions": self._build_npc_interactions(state),
            "final_vote": self._to_json_value(state.final_vote),
            "judge_result": self._to_json_value(judge_result),
        }

    def _build_npc_interactions(self, state: GameState) -> list[dict[str, Any]]:
        answers_by_question_id = {
            answer.question_id: answer
            for answer in state.answer_history
        }
        interactions: list[dict[str, Any]] = []
        for question in state.question_history:
            answer = answers_by_question_id.get(question.question_id)
            interactions.append(
                {
                    "question_id": question.question_id,
                    "target_character_id": question.target_character_id,
                    "question": question.content,
                    "asked_at": self._to_json_value(question.created_at),
                    "answer_id": answer.answer_id if answer else None,
                    "npc_answer": answer.content if answer else None,
                    "answered_at": self._to_json_value(answer.created_at) if answer else None,
                }
            )

        return interactions

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
