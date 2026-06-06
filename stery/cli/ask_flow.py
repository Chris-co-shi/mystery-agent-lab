"""
CLI ask flow.

这个模块负责 /ask 询问模式。

设计边界：
- 负责 NPC 选择、连续追问、NPC 切换。
- 不依赖 Application 的私有方法。
- 不修改 NPCInteractionService、Prompt、Guardrail。
- 不改变问答记录逻辑。
"""

from stery.cli.selectors import _resolve_character_id


class AskFlow:
    """
    /ask 询问流程。

    为什么做成类：
    - 避免 ask_flow.py 反向依赖 Application 的私有方法。
    - /ask 本身已经是一个独立交互流程。
    - 后续如果继续拆 CLI，AskFlow 可以单独测试。
    """

    def __init__(
            self,
            *,
            runtime,
            npc_interaction_service,
            case_recorder,
    ):
        self.runtime = runtime
        self.npc_interaction_service = npc_interaction_service
        self.case_recorder = case_recorder

    def run(self) -> None:
        """
        进入 NPC 询问模式。
        """

        print("\n【询问 NPC】")

        candidates = self._get_askable_npc_candidates()

        if not candidates:
            print("当前没有可询问的 NPC。")
            return

        self._show_askable_npcs(candidates)

        current_character_id = self._select_askable_npc(
            candidates=candidates,
            prompt_text="\n请输入要询问的 NPC 编号、姓名或 ID：",
        )

        if current_character_id is None:
            print("已取消询问。")
            return

        self._run_ask_loop(
            current_character_id=current_character_id,
            candidates=candidates,
        )

    def _get_askable_npc_candidates(self):
        """
        获取 /ask 可询问 NPC 候选。

        规则：
        1. 优先以 script.npc_profiles 为准。
           因为 NPCInteractionService 真正依赖 npc_profile。
        2. 排除死者 / 受害者。
        3. 如果旧剧本没有 npc_profiles，则 fallback 到 is_npc=True 的角色。
        """

        characters = self.runtime.list_characters()

        characters_by_id = {
            character.id: character
            for character in characters
        }

        npc_profiles = getattr(self.runtime.script, "npc_profiles", None) or []

        npc_profile_character_ids: set[str] = set()

        if isinstance(npc_profiles, dict):
            npc_profile_character_ids.update(
                str(profile_id)
                for profile_id in npc_profiles.keys()
            )
            profile_items = list(npc_profiles.values())
        else:
            profile_items = list(npc_profiles)

        for profile in profile_items:
            profile_character_id = getattr(profile, "character_id", None)

            if profile_character_id:
                npc_profile_character_ids.add(str(profile_character_id))
                continue

            profile_id = getattr(profile, "id", None)

            if profile_id and str(profile_id) in characters_by_id:
                npc_profile_character_ids.add(str(profile_id))

        if npc_profile_character_ids:
            return [
                character
                for character in characters
                if character.id in npc_profile_character_ids
                   and not self._is_victim(character)
            ]

        return [
            character
            for character in characters
            if getattr(character, "is_npc", False)
               and not self._is_victim(character)
        ]

    def _is_victim(self, character) -> bool:
        """
        判断角色是否为死者 / 受害者。
        """

        if getattr(character, "is_victim", False):
            return True

        role_text = str(getattr(character, "role", ""))

        return (
            "死者" in role_text
            or "受害者" in role_text
            or "victim" in role_text.lower()
        )

    def _show_askable_npcs(self, candidates) -> None:
        """
        展示当前可询问 NPC 列表。

        注意：
        - 这里不展示死者。
        - 内部 ID 可以保留展示，方便开发阶段核对。
        - 后续如果要完全玩家化，可以隐藏 ID。
        """

        print("\n【可询问 NPC】")

        if not candidates:
            print("当前没有可询问的 NPC。")
            return

        for index, character in enumerate(candidates, start=1):
            print(f"{index}. {character.name}（{character.role}）")

            character_id = getattr(character, "id", "")
            if character_id:
                print(f"   ID：{character_id}")

            public_profile = getattr(character, "public_profile", "")
            if public_profile:
                print(f"   简介：{public_profile}")

    def _get_character_name(self, character_id: str) -> str:
        """
        根据 character_id 获取角色姓名。

        找不到时回退显示 ID。
        """

        for character in self.runtime.list_characters():
            if character.id == character_id:
                return character.name

        return character_id

    def _select_askable_npc(
            self,
            *,
            candidates,
            prompt_text: str,
    ) -> str | None:
        """
        从可询问 NPC 列表中选择一个 NPC。
        """

        while True:
            raw_target = input(prompt_text).strip()

            if raw_target.lower() in {"q", "quit", "exit"} or raw_target in {"返回", "退出", "取消"}:
                return None

            if raw_target in {"/list", "list", "名单"}:
                self._show_askable_npcs(candidates)
                continue

            if raw_target in {"/help", "help", "?", "？"}:
                self._show_ask_mode_help()
                continue

            if not raw_target:
                print("NPC 不能为空。")
                continue

            if raw_target.startswith("@"):
                raw_target = raw_target[1:].strip()

            if not raw_target:
                print("NPC 不能为空。")
                continue

            target_character_id = _resolve_character_id(
                raw=raw_target,
                candidates=candidates,
            )

            if target_character_id is not None:
                return target_character_id

            print("请重新输入 NPC 编号、姓名或 ID。")

    def _run_ask_loop(
            self,
            *,
            current_character_id: str,
            candidates,
    ) -> None:
        """
        NPC 连续问答循环。
        """

        current_name = self._get_character_name(current_character_id)

        print(f"\n【正在询问：{current_name}】")
        self._show_ask_mode_help()

        while True:
            current_name = self._get_character_name(current_character_id)
            raw_input_text = input(f"\n你({current_name})：").strip()

            if not raw_input_text:
                print("问题不能为空。")
                continue

            command_result = self._handle_ask_mode_command(
                raw_input_text=raw_input_text,
                current_character_id=current_character_id,
                candidates=candidates,
            )

            current_character_id = command_result["current_character_id"]

            if not command_result["should_continue"]:
                return

            if command_result["consumed"]:
                continue

            self._ask_current_npc_once(
                target_character_id=current_character_id,
                question=raw_input_text,
            )

    def _handle_ask_mode_command(
            self,
            *,
            raw_input_text: str,
            current_character_id: str,
            candidates,
    ) -> dict:
        """
        处理 /ask 模式内部命令。
        """

        text = raw_input_text.strip()
        lower_text = text.lower()

        if lower_text in {"q", "quit", "exit"} or text in {"返回", "退出", "结束"}:
            print("已退出询问模式。")
            return {
                "current_character_id": current_character_id,
                "should_continue": False,
                "consumed": True,
            }

        if text in {"/help", "help", "?", "？"}:
            self._show_ask_mode_help()
            return {
                "current_character_id": current_character_id,
                "should_continue": True,
                "consumed": True,
            }

        if text in {"/list", "list", "名单"}:
            self._show_askable_npcs(candidates)
            return {
                "current_character_id": current_character_id,
                "should_continue": True,
                "consumed": True,
            }

        if text in {"/switch", "switch", "切换"}:
            self._show_askable_npcs(candidates)

            new_character_id = self._select_askable_npc(
                candidates=candidates,
                prompt_text="\n请输入要切换的 NPC 编号、姓名或 ID：",
            )

            if new_character_id is None:
                print("已取消切换，继续询问当前 NPC。")
                return {
                    "current_character_id": current_character_id,
                    "should_continue": True,
                    "consumed": True,
                }

            print(f"【已切换到：{self._get_character_name(new_character_id)}】")

            return {
                "current_character_id": new_character_id,
                "should_continue": True,
                "consumed": True,
            }

        if text.startswith("@"):
            raw_target = text[1:].strip()

            if not raw_target:
                print("请输入要切换的 NPC，例如：@陆沉。")
                return {
                    "current_character_id": current_character_id,
                    "should_continue": True,
                    "consumed": True,
                }

            new_character_id = _resolve_character_id(
                raw=raw_target,
                candidates=candidates,
            )

            if new_character_id is None:
                return {
                    "current_character_id": current_character_id,
                    "should_continue": True,
                    "consumed": True,
                }

            print(f"【已切换到：{self._get_character_name(new_character_id)}】")

            return {
                "current_character_id": new_character_id,
                "should_continue": True,
                "consumed": True,
            }

        if text.startswith("/"):
            print("询问模式下只支持 /help、/list、/switch。")
            print("如需调查、搜索、查看案件笔记或提交推理，请先输入 q 返回主命令。")

            return {
                "current_character_id": current_character_id,
                "should_continue": True,
                "consumed": True,
            }

        return {
            "current_character_id": current_character_id,
            "should_continue": True,
            "consumed": False,
        }

    def _ask_current_npc_once(
            self,
            *,
            target_character_id: str,
            question: str,
    ) -> None:
        """
        向当前 NPC 提出一个问题，并记录问答。
        """

        state = self.runtime.state

        if state is None:
            print("游戏尚未开始。")
            return

        try:
            result = self.npc_interaction_service.ask_npc(
                target_character_id=target_character_id,
                question=question,
            )

            self.case_recorder.record_ask_npc(
                state=state,
                npc_id=result.target_character_id,
                npc_name=self._get_character_name(result.target_character_id),
                question=result.question,
                answer=result.npc_answer,
            )

        except Exception as exc:
            print(f"询问失败：{exc}")
            return

        print(f"\n【{self._get_character_name(result.target_character_id)}】")
        print(result.npc_answer)

    def _show_ask_mode_help(self) -> None:
        """
        显示 /ask 询问模式帮助。
        """

        print("\n【询问模式】")
        print("直接输入问题：继续询问当前 NPC")
        print("@NPC姓名 / @编号 / @ID：快速切换 NPC")
        print("/switch：选择并切换 NPC")
        print("/list：查看可询问 NPC")
        print("/help：查看询问模式帮助")
        print("q / quit / exit / 返回 / 退出：返回主命令")


__all__ = ["AskFlow"]