"""
CLI search flow.

这个模块负责 /search 已知信息检索流程。

设计边界：
- 只检索玩家已知信息。
- 不解锁新线索。
- 不修改搜索业务逻辑。
- 搜索行为仍写入 case_records。
"""

from stery.cli.presenters import show_known_info_search_result


class SearchFlow:
    """
    /search 已知信息检索流程。
    """

    def __init__(
            self,
            *,
            runtime,
            known_info_search_service,
            case_recorder,
    ):
        self.runtime = runtime
        self.known_info_search_service = known_info_search_service
        self.case_recorder = case_recorder

    def run(self) -> None:
        """
        执行一次已知信息检索。
        """

        state = self.runtime.state

        if state is None:
            print("游戏尚未开始。")
            return

        print("\n【检索已知信息】")

        keyword = input("请输入你要检索的关键词：").strip()

        if not keyword:
            print("搜索关键词不能为空。")
            return

        # 先搜索，再记录。
        # 原因：避免“本次搜索行为”污染本次搜索结果。
        result = self.known_info_search_service.search(
            state=state,
            keyword=keyword,
        )

        show_known_info_search_result(result)

        self.case_recorder.record_search(
            state=state,
            target=keyword,
        )


__all__ = ["SearchFlow"]