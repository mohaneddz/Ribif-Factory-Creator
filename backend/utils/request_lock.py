# backend/utils/request_lock.py
"""
Request Locking Mechanism for Workflow/Project ID

Ensures that when the backend is processing a request for a specific workflow/project ID,
it won't accept other requests for the same ID until the current one is done.
This fixes potential refresh issues and prevents race conditions.
"""

import threading
import time
from functools import wraps
from typing import Optional, Callable, Any
from flask import request, jsonify
from utils.logger import get_logger

logger = get_logger("request_lock")

# Global lock registry: {project_id: threading.Lock}
_project_locks: dict[str, threading.Lock] = {}
_registry_lock = threading.Lock()

# Track active requests per project
_active_requests: dict[str, dict] = {}


def _get_or_create_lock(project_id: str) -> threading.Lock:
    """Get or create a lock for a specific project ID."""
    with _registry_lock:
        if project_id not in _project_locks:
            _project_locks[project_id] = threading.Lock()
        return _project_locks[project_id]


def _get_project_id_from_request() -> Optional[str]:
    """Extract project_id from request headers, form, or JSON."""
    # Try headers first
    project_id = request.headers.get("x-project-id") or request.headers.get("X-Project-Id")
    
    # Try form data
    if not project_id and request.form:
        project_id = request.form.get("project_id")
    
    # Try JSON body
    if not project_id and request.is_json:
        try:
            payload = request.get_json(silent=True) or {}
            project_id = (
                payload.get("project_id") 
                or payload.get("ribif_metadata", {}).get("project_id")
                or payload.get("module1_data", {}).get("project_id")
            )
        except Exception:
            pass
    
    return project_id


def require_project_lock(
    timeout: float = 0.5,
    return_waiting_response: bool = True
) -> Callable:
    """
    Decorator to ensure only one request per project ID is processed at a time.
    
    Args:
        timeout: How long to wait for the lock before returning "busy" response (seconds)
        return_waiting_response: If True, return 429 when locked. If False, block until available.
    
    Usage:
        @bp.route("/api/module1/process", methods=["POST"])
        @require_project_lock(timeout=0.5)
        def process_module_1():
            # Your code here
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            project_id = _get_project_id_from_request()
            
            # If no project_id, proceed without locking
            if not project_id:
                logger.debug(f"{func.__name__}: No project_id found, proceeding without lock")
                return func(*args, **kwargs)
            
            # Get the lock for this project
            lock = _get_or_create_lock(project_id)
            
            # Try to acquire the lock
            if return_waiting_response:
                # Non-blocking mode - cannot specify timeout
                acquired = lock.acquire(blocking=False)
            else:
                # Blocking mode with timeout
                acquired = lock.acquire(blocking=True, timeout=timeout)
            
            if not acquired:
                # Another request is processing this project
                logger.warning(
                    f"{func.__name__}: Project {project_id} is already being processed. "
                    f"Returning busy response."
                )
                
                # Get info about the active request
                active_info = _active_requests.get(project_id, {})
                
                return jsonify({
                    "error": "Project is currently being processed",
                    "status": "busy",
                    "project_id": project_id,
                    "message": "Another request for this project is currently in progress. Please wait and try again.",
                    "active_since": active_info.get("start_time"),
                    "active_endpoint": active_info.get("endpoint"),
                }), 429  # 429 Too Many Requests
            
            # Lock acquired - track the active request
            start_time = time.time()
            endpoint = request.endpoint or func.__name__
            
            with _registry_lock:
                _active_requests[project_id] = {
                    "start_time": start_time,
                    "endpoint": endpoint,
                    "method": request.method,
                }
            
            logger.info(
                f"{func.__name__}: Lock acquired for project {project_id}. Processing request..."
            )
            
            try:
                # Execute the actual function
                result = func(*args, **kwargs)
                
                duration = time.time() - start_time
                logger.info(
                    f"{func.__name__}: Completed for project {project_id} in {duration:.2f}s"
                )
                
                return result
            
            finally:
                # Always release the lock
                with _registry_lock:
                    if project_id in _active_requests:
                        del _active_requests[project_id]
                
                lock.release()
                
                logger.debug(f"{func.__name__}: Lock released for project {project_id}")
        
        return wrapper
    return decorator


def get_active_projects() -> list[dict]:
    """Get list of currently active projects being processed."""
    with _registry_lock:
        return [
            {
                "project_id": pid,
                "endpoint": info["endpoint"],
                "method": info["method"],
                "duration_seconds": time.time() - info["start_time"],
            }
            for pid, info in _active_requests.items()
        ]


def is_project_locked(project_id: str) -> bool:
    """Check if a project is currently locked/being processed."""
    if project_id not in _project_locks:
        return False
    
    lock = _project_locks[project_id]
    # Try to acquire without blocking
    acquired = lock.acquire(blocking=False)
    
    if acquired:
        # We got it, so it wasn't locked
        lock.release()
        return False
    
    # Couldn't acquire, so it's locked
    return True


def cleanup_stale_locks(max_age_seconds: float = 3600):
    """
    Cleanup locks for projects that haven't been active recently.
    Call this periodically to prevent memory leaks.
    """
    with _registry_lock:
        current_time = time.time()
        stale_projects = []
        
        for project_id, info in list(_active_requests.items()):
            age = current_time - info["start_time"]
            if age > max_age_seconds:
                stale_projects.append(project_id)
                del _active_requests[project_id]
        
        if stale_projects:
            logger.warning(
                f"Cleaned up {len(stale_projects)} stale project locks: {stale_projects}"
            )
