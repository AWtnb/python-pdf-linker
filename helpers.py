import sys
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
) -> None:
    mapping = {"error": "ERROR", "warning": "WARNING", "info": "INFO", "debug": "DEBUG"}

    msg = message
    if target_str:
        msg += f"\n    対象テキスト: {target_str}"
    if target_path:
        msg += f"\n    対象パス: '{target_path}'"

    level = mapping.get(genre, "INFO")
    logger.log(level, msg)


if __name__ == "__main__":
    pass
