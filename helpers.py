import sys
import re
from pathlib import Path
from typing import Any, Literal
from loguru import logger

# initialize
logger.remove()

# for console
logger.add(
    sys.stdout,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>",
    colorize=True,
)

# for log file
logger.add(
    Path("pdf-linker-result.log"),
    format="{time} {level} {message}",
    rotation="5 MB",
    level="DEBUG",
)


def smart_log(
    genre: Literal["debug", "error", "info", "warning"],
    message: str = "",
    target_str: Any = "",
    target_path: Any = "",
    skip: bool = False,
) -> None:
    mapping = {"error": "ERROR", "warning": "WARNING", "info": "INFO", "debug": "DEBUG"}

    msg = message
    if target_str:
        msg += f"\n    対象テキスト: {target_str}"
    if target_path:
        msg += f"\n    対象パス: '{target_path}'"
    if skip:
        msg += f"\n    処理をスキップします"

    level = mapping.get(genre, "INFO")
    logger.log(level, msg)


def stepped_outpath(path: str, step: int, ext: str, suffix: str = "") -> Path:
    p = Path(path)
    stem = p.stem
    if not ext.startswith("."):
        raise ValueError("invalid extension.")
    new_stem = (
        f"{stem[:-1]}{step}"
        if re.search("_step[0-9]$", stem)
        else stem + f"_step{step}"
    ) + suffix
    return p.with_name(new_stem + ext)
