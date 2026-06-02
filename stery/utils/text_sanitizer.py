from __future__ import annotations

from typing import Any


def remove_surrogates(text: str) -> str:
    """
    移除非法 Unicode surrogate 字符。

    某些复制粘贴内容、模型返回内容、JSON 文本中可能混入
    U+D800 ~ U+DFFF 范围的孤立 surrogate 字符。
    这些字符不能被 UTF-8 正常编码，会导致文件写入失败。
    """

    return "".join(
        ch
        for ch in text
        if not 0xD800 <= ord(ch) <= 0xDFFF
    )


def sanitize_text(value: Any) -> Any:
    """
    递归清洗字符串、list、tuple、set、dict 中的 surrogate 字符。

    注意：
    - 不改变业务结构
    - 只清理字符串内容
    - 用于导出 JSON / Markdown 前的安全处理
    """

    if isinstance(value, str):
        return remove_surrogates(value)

    if isinstance(value, list):
        return [sanitize_text(item) for item in value]

    if isinstance(value, tuple):
        return tuple(sanitize_text(item) for item in value)

    if isinstance(value, set):
        return {sanitize_text(item) for item in value}

    if isinstance(value, dict):
        return {
            sanitize_text(key): sanitize_text(item)
            for key, item in value.items()
        }

    return value