from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

from stery.domain.enums import CaseActionType


def generate_case_record_id() -> str:
    """生成案件调查记录 ID。"""
    return f"case_record_{uuid4().hex}"


def utc_now() -> datetime:
    """生成 UTC 时间。"""
    return datetime.now(timezone.utc)


class CaseRecordBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaseRecord(CaseRecordBaseModel):
    """
    玩家案件记录。

    CaseRecord 是玩家行为和调查发现的统一记录。
    它不是剧本静态数据，而是一局游戏运行过程中的记忆。
    """
    record_id: str = Field(default_factory=lambda: uuid4().hex)
    action_type: CaseActionType
    title: str
    summary: str
    # 结构化扩展字段。
    # 用于保存调查对象、线索 ID、NPC ID 等机器可读信息。
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
