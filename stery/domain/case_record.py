from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict

from stery.domain.enums import CaseActionType


def generate_case_record_id() -> str:
    """生成案件调查记录 ID。"""
    return f"case_record_{uuid4().hex}"


def utc_now() -> datetime:
    """生成 UTC 时间。"""
    return datetime.now(timezone.utc)

class CaseRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: uuid4().hex)
    # 案件操作类型
    action_type: CaseActionType
    # 标题
    title: str
    # 概括
    summary: str
    # 创建时间
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict = Field(default_factory=dict)

