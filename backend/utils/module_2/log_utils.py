"""
Simple console logging helpers for clean, consistent CLI output.
"""

from __future__ import annotations

from typing import Any

from utils.logger import get_logger

logger = get_logger(__name__)


def section(title: str) -> None:
    logger.info("SECTION %s", title)


def info(msg: str) -> None:
    logger.info("%s", msg)


def success(msg: str) -> None:
    logger.info("DONE %s", msg)


def warn(msg: str) -> None:
    logger.warning("%s", msg)


def error(msg: str) -> None:
    logger.error("%s", msg)


def kv(label: str, value: Any) -> None:
    logger.info("%s: %s", label, value)
