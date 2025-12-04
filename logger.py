from typing import Literal


def logfy(
    genre: Literal["skip", "error", "processing", "warning"],
    message: str,
    target_str: str = "",
    target_path: str = "",
) -> str:
    s = f"[{genre}] {message}"
    if not s.endswith("。"):
        s += "。"
    if target_str:
        s += f"対象テキスト: {target_str}"
    if target_path:
        s += f"対象パス: {target_path}"
    return s
