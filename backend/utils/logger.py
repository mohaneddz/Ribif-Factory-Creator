"""
Shared logging singleton for backend modules.
Creates a per-run log file under backend/logs and logs to console.
Falls back to /tmp or console-only in read-only filesystem environments.
"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterator, Optional

_LOGGER: Optional[logging.Logger] = None
_RUN_ID: Optional[str] = None


def _get_writable_logs_dir() -> Optional[str]:
    """Get a writable logs directory, or None if file logging should be disabled."""
    utils_dir = os.path.dirname(__file__)
    backend_dir = os.path.abspath(os.path.join(utils_dir, ".."))
    default_logs_dir = os.path.join(backend_dir, "logs")
    
    # Try default location first
    try:
        os.makedirs(default_logs_dir, exist_ok=True)
        test_file = os.path.join(default_logs_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return default_logs_dir
    except (OSError, PermissionError):
        pass
    
    # Try /tmp/ribif/logs for serverless environments
    try:
        tmp_logs_dir = os.path.join(tempfile.gettempdir(), "ribif", "logs")
        os.makedirs(tmp_logs_dir, exist_ok=True)
        test_file = os.path.join(tmp_logs_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return tmp_logs_dir
    except (OSError, PermissionError):
        pass
    
    # File logging disabled - use console only
    return None


def _build_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + f"_{os.getpid()}"


def get_logger(name: Optional[str] = None) -> logging.Logger:
    global _LOGGER, _RUN_ID
    if _LOGGER:
        return _LOGGER if name is None else _LOGGER.getChild(name)

    _RUN_ID = _build_run_id()
    logger = logging.getLogger("ribif")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter(
            fmt="%(asctime)s.%(msecs)03d | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Try to set up file handler if we have a writable directory
        logs_dir = _get_writable_logs_dir()
        log_path = None
        if logs_dir:
            try:
                log_path = os.path.join(logs_dir, f"run_{_RUN_ID}.log")
                file_handler = logging.FileHandler(log_path, encoding="utf-8")
                file_handler.setLevel(logging.INFO)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except (OSError, PermissionError) as e:
                log_path = None
                print(f"Warning: Could not create log file: {e}", file=sys.stderr)

        # Always add console handler
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        if log_path:
            logger.info("START run_id=%s log_path=%s", _RUN_ID, log_path)
        else:
            logger.info("START run_id=%s (console-only logging)", _RUN_ID)

    _LOGGER = logger
    return _LOGGER if name is None else _LOGGER.getChild(name)


def run_id() -> str:
    if _RUN_ID is None:
        get_logger()
    return _RUN_ID or "unknown"


@dataclass
class TaskResult:
    name: str
    duration_s: float
    status: str


@contextmanager
def task(name: str, logger: Optional[logging.Logger] = None) -> Iterator[TaskResult]:
    log = logger or get_logger()
    start = time.perf_counter()
    log.info("START %s", name)
    result = TaskResult(name=name, duration_s=0.0, status="started")
    try:
        yield result
    except Exception:
        result.duration_s = time.perf_counter() - start
        result.status = "error"
        log.exception("ERROR %s (%.2fs)", name, result.duration_s)
        raise
    else:
        result.duration_s = time.perf_counter() - start
        result.status = "done"
        log.info("DONE %s (%.2fs)", name, result.duration_s)


def log_skip(name: str, reason: Optional[str] = None, logger: Optional[logging.Logger] = None) -> None:
    log = logger or get_logger()
    if reason:
        log.info("SKIP %s reason=%s", name, reason)
    else:
        log.info("SKIP %s", name)
