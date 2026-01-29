"""
Simple console logging helpers for clean, consistent CLI output.
"""

from __future__ import annotations

from typing import Any


def section(title: str) -> None:
    print(f"\n== {title} ==")


def info(msg: str) -> None:
    print(f"[INFO] {msg}")


def success(msg: str) -> None:
    print(f"[OK] {msg}")


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def error(msg: str) -> None:
    print(f"[ERROR] {msg}")


def kv(label: str, value: Any) -> None:
    print(f"  - {label}: {value}")
