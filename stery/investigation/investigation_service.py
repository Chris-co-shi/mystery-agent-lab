# stery/investigation/investigation_service.py

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from stery.domain.models import Clue, GameScript, InvestigationTarget
from stery.domain.state import GameState


class InvestigationTargetNotFoundError(ValueError):
    """
    调查对象不存在异常。

    为什么定义专用异常？
    - 比直接 ValueError 更容易在 CLI / API 层捕获。
    - 后续 /investigate 命令可以把它转换成玩家友好的错误信息。
    """


@dataclass(frozen=True)
class InvestigationResult:
    """
    一次调查动作的结果。

    这个对象是 InvestigationService 的输出，不是剧本静态协议。

    它描述的是：
    - 玩家调查了哪个对象
    - 这个对象是什么类型
    - 这次发现了哪些新线索
    - 哪些线索之前已经发现或本来公开可见
    - 哪些隐藏线索因为规则被跳过
    - 给玩家展示的简短消息

    注意：
    这里保存 Clue 对象，而不是只保存 clue_id。
    原因：
    - CLI 后续需要直接展示 clue.title / clue.content。
    - CaseRecorder 后续也可以直接从 Clue 生成记录摘要。
    """

    target_id: str
    target_name: str
    target_type: str
    target_description: str

    newly_discovered_clues: list[Clue] = field(default_factory=list)
    already_discovered_clues: list[Clue] = field(default_factory=list)

    # HIDDEN 线索不会通过普通调查解锁。
    # 这里只保存 ID，避免无意中把隐藏线索内容暴露给展示层。
    skipped_hidden_clue_ids: list[str] = field(default_factory=list)

    message: str = ""

    @property
    def has_new_clues(self) -> bool:
        """
        当前调查是否发现了新线索。
        """

        return len(self.newly_discovered_clues) > 0

    def to_dict(self) -> dict[str, Any]:
        """
        转为 dict，便于后续测试、导出、CLI 展示。

        注意：
        这里不会导出 HIDDEN 线索内容，只导出 skipped_hidden_clue_ids。
        """

        return {
            "target_id": self.target_id,
            "target_name": self.target_name,
            "target_type": self.target_type,
            "target_description": self.target_description,
            "newly_discovered_clue_ids": [
                clue.id for clue in self.newly_discovered_clues
            ],
            "already_discovered_clue_ids": [
                clue.id for clue in self.already_discovered_clues
            ],
            "skipped_hidden_clue_ids": list(self.skipped_hidden_clue_ids),
            "message": self.message,
        }


def _is_already_known(state: GameState, clue: Clue) -> bool:
    """
    判断线索是否已经对玩家可见。

    规则：
    - PUBLIC 线索从开局就可见，所以视为 already known。
    - 已经在 state.unlocked_clue_ids 中的线索也视为 already known。
    """

    return _is_public_clue(clue) or clue.id in state.unlocked_clue_ids


def _build_message(
        *,
    target: InvestigationTarget,
    newly_discovered_clues: list[Clue],
    already_discovered_clues: list[Clue],
    skipped_hidden_clue_ids: list[str],
) -> str:
    """
    构建给玩家展示的简短调查结果。

    注意：
    - 不展示 HIDDEN 线索 ID 或标题。
    - 只提示“部分信息暂未显现”，避免泄露隐藏线索存在。
    """

    if newly_discovered_clues:
        clue_titles = "、".join(clue.title for clue in newly_discovered_clues)
        return f"调查「{target.name}」：发现 {len(newly_discovered_clues)} 条新线索：{clue_titles}。"

    if already_discovered_clues:
        clue_titles = "、".join(clue.title for clue in already_discovered_clues)
        return f"调查「{target.name}」：没有发现新线索，相关线索此前已知：{clue_titles}。"

    if skipped_hidden_clue_ids:
        return f"调查「{target.name}」：暂时没有发现可以确认的新线索。"

    return f"调查「{target.name}」：没有发现新的有效线索。"


class InvestigationService:
    """
    调查服务。

    它是 V0.2.0 调查机制的服务层核心。

    职责：
    - 根据 investigation_target_id 找调查对象
    - 根据 target.discoverable_clue_ids 找线索
    - 判断哪些线索是新发现
    - 更新 GameState.unlocked_clue_ids
    - 返回 InvestigationResult

    不负责：
    - CLI 输入输出
    - 玩家编号选择
    - 写 case_records
    - 生成 Markdown / JSON 导出
    - Agent Tool 调用
    """

    def __init__(self, script: GameScript):
        self.script = script

        # 预构造索引，避免每次调查都线性扫描。
        self._targets_by_id: dict[str, InvestigationTarget] = {
            target.id: target for target in script.investigation_targets
        }
        self._clues_by_id: dict[str, Clue] = {
            clue.id: clue for clue in script.clues
        }

    def list_targets(self) -> list[InvestigationTarget]:
        """
        返回当前剧本中所有可调查对象。

        后续 CLI 可以用它展示调查对象列表。
        当前只做服务能力，不处理展示格式。
        """

        return list(self.script.investigation_targets)

    def get_target(self, target_id: str) -> InvestigationTarget:
        """
        根据 ID 获取调查对象。

        如果不存在，抛出 InvestigationTargetNotFoundError。
        """

        target = self._targets_by_id.get(target_id)

        if target is None:
            raise InvestigationTargetNotFoundError(
                f"Unknown investigation_target_id: {target_id}"
            )

        return target

    def investigate(self, state: GameState, target_id: str) -> InvestigationResult:
        """
        执行一次调查。

        参数：
            state:
                当前游戏运行状态。服务会更新 state.unlocked_clue_ids。

            target_id:
                调查对象 ID。

        返回：
            InvestigationResult

        行为规则：
        - 不存在的 target_id 会报错。
        - HIDDEN 线索不会通过普通调查解锁。
        - PUBLIC 线索视为已经可见，不作为新发现。
        - LOCKED 且未解锁线索会加入 state.unlocked_clue_ids。
        - 重复调查不会重复解锁同一线索。
        """

        target = self.get_target(target_id)

        newly_discovered_clues: list[Clue] = []
        already_discovered_clues: list[Clue] = []
        skipped_hidden_clue_ids: list[str] = []

        for clue_id in target.discoverable_clue_ids:
            clue = self._get_clue_or_raise(clue_id)

            if _is_hidden_clue(clue):
                # HIDDEN 线索不能通过普通调查暴露。
                skipped_hidden_clue_ids.append(clue.id)
                continue

            if _is_already_known(state, clue):
                already_discovered_clues.append(clue)
                continue

            # 只有非 HIDDEN、非已知的线索才算新发现。
            newly_discovered_clues.append(clue)
            state.unlocked_clue_ids.add(clue.id)

        # 如果这次确实更新了状态，刷新 updated_at。
        if newly_discovered_clues:
            state.touch()

        message = _build_message(
            target=target,
            newly_discovered_clues=newly_discovered_clues,
            already_discovered_clues=already_discovered_clues,
            skipped_hidden_clue_ids=skipped_hidden_clue_ids,
        )

        return InvestigationResult(
            target_id=target.id,
            target_name=target.name,
            target_type=_enum_value(target.type),
            target_description=target.description,
            newly_discovered_clues=newly_discovered_clues,
            already_discovered_clues=already_discovered_clues,
            skipped_hidden_clue_ids=skipped_hidden_clue_ids,
            message=message,
        )

    def _get_clue_or_raise(self, clue_id: str) -> Clue:
        """
        根据 clue_id 获取线索。

        理论上，GameScript 模型层已经校验过
        investigation_targets.discoverable_clue_ids 必须存在于 clues。

        这里仍然保留防御式检查：
        - 防止测试构造了不完整对象
        - 防止未来某些路径绕过模型校验
        """

        clue = self._clues_by_id.get(clue_id)

        if clue is None:
            raise ValueError(f"Unknown clue_id referenced by investigation target: {clue_id}")

        return clue


def _enum_value(value: Any) -> str:
    """
    获取枚举值。

    InvestigationTarget.type 是 Enum。
    这里统一转换成字符串，方便 result.to_dict() 和 CLI 展示。
    """

    return str(getattr(value, "value", value))


def _visibility_value(clue: Clue) -> str:
    """
    读取 clue.visibility 的字符串值。

    兼容：
    - str Enum
    - 普通 Enum
    - 直接字符串

    这样可以避免对 ClueVisibility 枚举实现细节过度依赖。
    """

    return str(getattr(clue.visibility, "value", clue.visibility)).upper()


def _is_public_clue(clue: Clue) -> bool:
    """
    判断是否是 PUBLIC 线索。
    """

    return _visibility_value(clue) == "PUBLIC"


def _is_hidden_clue(clue: Clue) -> bool:
    """
    判断是否是 HIDDEN 线索。

    如果当前枚举没有 HIDDEN，这个函数也不会因为访问
    ClueVisibility.HIDDEN 而报错。
    """

    return _visibility_value(clue) == "HIDDEN"