"""Validate connection settings before any paid/network request; never log values."""


class ConfigurationError(ValueError):
    """Only curated, value-free messages are safe to show in the UI."""


def normalize_api_key(raw, location):
    if not isinstance(raw, str):
        raise ConfigurationError(f"{location}必须是文本。请直接粘贴服务控制台提供的密钥。")

    def trim_boundary(value):
        while True:
            cleaned = value.strip().strip("\ufeff\u200b\u2060").strip()
            if cleaned == value:
                return cleaned
            value = cleaned

    value = trim_boundary(raw)
    pairs = {'"': '"', "'": "'", "“": "”", "‘": "’", "`": "`"}
    while len(value) >= 2 and value[0] in pairs and value[-1] == pairs[value[0]]:
        value = trim_boundary(value[1:-1])
    if not value:
        raise ConfigurationError(f"{location}未填写。请粘贴有效密钥后再生成简报。")
    if not value.isascii():
        raise ConfigurationError(f"{location}含非英文或隐藏字符。请从服务控制台重新复制密钥本身，不附带中文说明；不要将密钥发到聊天里。")
    if any(ord(char) < 33 or ord(char) == 127 for char in value):
        raise ConfigurationError(f"{location}含内部空白或控制字符。请重新复制完整密钥，不附带 Bearer、空格或换行。")
    if any(char in value for char in "\"'`"):
        raise ConfigurationError(f"{location}含引号或代码符号。请只填写密钥本身。")
    return value
