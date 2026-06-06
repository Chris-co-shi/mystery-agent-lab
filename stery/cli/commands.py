"""
CLI command helpers.

这个模块负责：
- 命令标准化
- /help 展示

不依赖 runtime。
不修改 GameState。
"""


def normalize_command(command: str) -> str:
    """
    标准化玩家输入命令。

    支持：
    - /help
    - help
    - 中文别名
    """

    value = (command or "").strip()

    if not value:
        return ""

    if not value.startswith("/"):
        value = "/" + value

    aliases = {
        "/帮助": "/help",
        "/h": "/help",

        "/状态": "/status",
        "/背景": "/background",
        "/人物": "/characters",
        "/角色": "/characters",

        "/线索": "/clues",
        "/搜索": "/search",
        "/检索": "/search",

        "/调查": "/investigate",
        "/询问": "/ask",
        "/问话": "/ask",

        "/历史": "/history",
        "/复盘": "/review",
        "/记录": "/review",

        "/笔记": "/case",
        "/案件": "/case",
        "/notebook": "/case",

        "/提交": "/submit",
        "/推理": "/submit",

        "/退出": "/quit",
        "/q": "/quit",
    }

    return aliases.get(value, value)


def show_help() -> None:
    """
    展示 CLI 命令帮助。

    命令分组原则：
    - 案件信息
    - 玩家行动
    - 已知信息
    - 流程控制
    """

    print("\n【可用命令】")

    print("\n【案件信息】")
    print("/status       查看当前游戏状态")
    print("/background   查看案件背景")
    print("/characters   查看人物列表")

    print("\n【玩家行动】")
    print("/investigate  调查地点、尸体或物品")
    print("/ask          询问 NPC")

    print("\n【已知信息】")
    print("/clues        查看当前线索")
    print("/search       检索已知信息")
    print("/case         查看案件笔记本")
    print("/review       查看调查记录")

    print("\n【流程】")
    print("/submit       提交最终推理")
    print("/help         查看帮助")
    print("/quit         退出游戏")


__all__ = [
    "normalize_command",
    "show_help",
]