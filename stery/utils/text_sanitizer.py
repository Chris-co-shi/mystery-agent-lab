def remove_surrogates(text: str) -> str:
    """
    移除非法 Unicode surrogate 字符。

    某些复制粘贴内容、模型返回内容、JSON 文本中可能混入
    U+D800 ~ U+DFFF 范围的孤立 surrogate 字符，
    这些字符不能被 UTF-8 正常编码。
    """
    return "".join(
        ch for ch in text
        if not 0xD800 <= ord(ch) <= 0xDFFF
    )


def sanitize_text(value: object) -> object:
    """
    递归清洗字符串、list、dict 中的 surrogate 字符。
    """
    if isinstance(value, str):
        return remove_surrogates(value)

    if isinstance(value, list):
        return [sanitize_text(item) for item in value]

    if isinstance(value, dict):
        return {
            sanitize_text(key): sanitize_text(item)
            for key, item in value.items()
        }

    return value