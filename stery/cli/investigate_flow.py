"""
CLI investigate flow.

这个模块负责 /investigate 调查流程。

设计边界：
- 展示可调查对象。
- 解析玩家输入。
- 调用 InvestigationService。
- 展示调查结果。
- 调用 CaseRecorder 记录调查行为。
- 不修改 InvestigationService 业务逻辑。
"""

from typing import Any


class InvestigateFlow:
    """
    /investigate 调查流程。
    """

    def __init__(
            self,
            *,
            runtime,
            investigation_service,
            case_recorder,
    ):
        self.runtime = runtime
        self.investigation_service = investigation_service
        self.case_recorder = case_recorder

    def run(self) -> None:
        """
        执行一次调查。
        """

        state = self.runtime.state

        if state is None:
            print("游戏尚未开始。")
            return

        print("\n【调查】")

        targets = self._list_targets()

        if not targets:
            print("当前没有可调查对象。")
            return

        self._show_investigation_targets(targets)

        target_id = self._prompt_target_id(targets)

        if target_id is None:
            print("已取消调查。")
            return

        try:
            result = self._investigate_target(
                state=state,
                target_id=target_id,
            )
        except Exception as exc:
            print(f"调查失败：{exc}")
            return

        self._show_investigation_result(result)

        self.case_recorder.record_investigation(
            state=state,
            result=result,
        )

    def _list_targets(self) -> list[Any]:
        """
        获取可调查对象列表。

        如果你的 InvestigationService 方法名不是 list_targets，
        只需要改这里。
        """

        if hasattr(self.investigation_service, "list_targets"):
            return list(self.investigation_service.list_targets())

        if hasattr(self.investigation_service, "list_investigation_targets"):
            return list(self.investigation_service.list_investigation_targets())

        # fallback：直接读 script.investigation_targets
        return list(getattr(self.runtime.script, "investigation_targets", []) or [])

    def _investigate_target(self, *, state, target_id: str):
        """
        调用 InvestigationService 执行调查。

        如果你的 InvestigationService 方法签名不同，只需要改这里。
        """

        try:
            return self.investigation_service.investigate(
                state=state,
                target_id=target_id,
            )
        except TypeError:
            return self.investigation_service.investigate(target_id)

    def _show_investigation_targets(self, targets) -> None:
        """
        展示可调查对象。
        """

        print("\n【可调查对象】")

        for index, target in enumerate(targets, start=1):
            target_type = self._get_attr(target, "type", "")
            target_type = getattr(target_type, "value", target_type)

            print(f"{index}. {self._get_attr(target, 'name', '')}（{target_type}）")

            description = self._get_attr(target, "description", "")
            if description:
                print(f"   描述：{description}")

            target_id = self._get_attr(target, "id", "")
            if target_id:
                print(f"   ID：{target_id}")

    def _prompt_target_id(self, targets) -> str | None:
        """
        解析玩家选择的调查对象。

        支持：
        - 编号
        - target_id
        - target.name
        - search_keywords
        - 名称模糊匹配
        """

        while True:
            raw = input("\n请输入要调查的对象编号、名称或 ID：").strip()

            if raw.lower() in {"q", "quit", "exit"} or raw in {"取消", "退出", "返回"}:
                return None

            if not raw:
                print("调查对象不能为空。")
                continue

            target_id = self._resolve_target_id(
                raw=raw,
                targets=targets,
            )

            if target_id is not None:
                return target_id

            print("请重新输入调查对象编号、名称或 ID。")

    def _resolve_target_id(self, *, raw: str, targets) -> str | None:
        """
        将玩家输入解析为 investigation_target.id。
        """

        value = raw.strip()

        if value.isdigit():
            index = int(value)

            if 1 <= index <= len(targets):
                return self._get_attr(targets[index - 1], "id", "")

            print(f"无效编号：{value}。请输入 1 到 {len(targets)} 之间的数字。")
            return None

        for target in targets:
            target_id = self._get_attr(target, "id", "")
            target_name = self._get_attr(target, "name", "")

            if value == target_id or value == target_name:
                return target_id

        keyword_matches = []

        for target in targets:
            search_keywords = self._get_attr(target, "search_keywords", []) or []
            target_name = self._get_attr(target, "name", "")

            if value in target_name or value in search_keywords:
                keyword_matches.append(target)

        if len(keyword_matches) == 1:
            return self._get_attr(keyword_matches[0], "id", "")

        if len(keyword_matches) > 1:
            print("匹配到多个调查对象，请输入编号或完整名称：")

            for target in keyword_matches:
                index = targets.index(target) + 1
                print(f"{index}. {self._get_attr(target, 'name', '')}（{self._get_attr(target, 'id', '')}）")

            return None

        print(f"未找到匹配的调查对象：{value}")
        return None

    def _show_investigation_result(self, result) -> None:
        """
        展示调查结果。

        注意：
        - 不展示 HIDDEN 线索内容。
        - skipped_hidden_clue_ids 不面向玩家展示具体内容。
        """

        print("\n【调查结果】")

        target_name = self._get_attr(result, "target_name", "")
        target_type = self._get_attr(result, "target_type", "")

        print(f"调查对象：{target_name}（{target_type}）")

        newly_discovered = list(
            self._get_attr(result, "newly_discovered_clues", []) or []
        )
        already_discovered = list(
            self._get_attr(result, "already_discovered_clues", []) or []
        )

        if newly_discovered:
            print(f"发现 {len(newly_discovered)} 条新线索：")
            for clue in newly_discovered:
                print(f"- {self._get_attr(clue, 'title', '')}")
                print(f"  ID：{self._get_attr(clue, 'id', '')}")
                print(f"  内容：{self._get_attr(clue, 'content', '')}")

        elif already_discovered:
            print("没有发现新线索，相关线索此前已知。")
            print("\n【已知线索】")
            for clue in already_discovered:
                print(f"- {self._get_attr(clue, 'title', '')}")

        else:
            print("暂时没有发现新的有效线索。")

    def _get_attr(self, obj, name: str, default=None):
        """
        兼容 dataclass / pydantic / 普通对象 / dict。
        """

        if isinstance(obj, dict):
            return obj.get(name, default)

        return getattr(obj, name, default)


__all__ = ["InvestigateFlow"]