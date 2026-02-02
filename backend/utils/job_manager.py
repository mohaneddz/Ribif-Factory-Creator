"""
Async Job Manager for Long-Running Pipeline Tasks
==================================================

Provides background job execution with status polling for Module 1 and other long-running operations.
Prevents socket hang-ups by immediately returning a job_id and running pipeline in background.
"""

import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class Job:
    """Represents an async job."""
    job_id: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0  # 0-100
    progress_message: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_details: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": self.progress,
            "progress_message": self.progress_message,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self._duration_seconds(),
        }
    
    def _duration_seconds(self) -> Optional[float]:
        if not self.started_at:
            return None
        end = self.completed_at or datetime.utcnow()
        return round((end - self.started_at).total_seconds(), 2)


class JobManager:
    """
    Thread-safe job manager for background task execution.
    
    Usage:
        job_id = job_manager.submit(my_function, arg1, arg2, timeout=300)
        status = job_manager.get_status(job_id)
        result = job_manager.get_result(job_id)
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._jobs: Dict[str, Job] = {}
        self._results: Dict[str, Any] = {}
        self._job_lock = threading.Lock()
        self._cleanup_interval = 3600  # 1 hour
        self._job_ttl = 7200  # 2 hours - jobs expire after this
        self._initialized = True
        
        # Start cleanup thread
        cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        cleanup_thread.start()
    
    def submit(
        self,
        func: Callable,
        *args,
        timeout: int = 600,  # 10 minute default timeout
        job_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Submit a function to run in background.
        
        Args:
            func: Function to execute
            *args: Arguments for the function
            timeout: Maximum execution time in seconds
            job_id: Optional custom job ID
            **kwargs: Keyword arguments for the function
            
        Returns:
            job_id: Unique identifier to poll status/result
        """
        job_id = job_id or str(uuid.uuid4())
        
        with self._job_lock:
            self._jobs[job_id] = Job(job_id=job_id)
        
        # Run in background thread
        thread = threading.Thread(
            target=self._run_job,
            args=(job_id, func, args, kwargs, timeout),
            daemon=True
        )
        thread.start()
        
        logger.info(f"Job {job_id} submitted (timeout={timeout}s)")
        return job_id
    
    def _run_job(
        self,
        job_id: str,
        func: Callable,
        args: tuple,
        kwargs: dict,
        timeout: int
    ):
        """Execute job with timeout enforcement."""
        job = self._jobs.get(job_id)
        if not job:
            return
        
        # Update status to running
        with self._job_lock:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            job.progress_message = "Starting..."
        
        result_container = {"result": None, "error": None}
        
        def target_wrapper():
            try:
                # Pass progress callback to function if it accepts it
                if 'progress_callback' in func.__code__.co_varnames[:func.__code__.co_argcount]:
                    kwargs['progress_callback'] = lambda p, m: self.update_progress(job_id, p, m)
                result_container["result"] = func(*args, **kwargs)
            except Exception as e:
                result_container["error"] = str(e)
                result_container["traceback"] = traceback.format_exc()
        
        # Run with timeout
        worker = threading.Thread(target=target_wrapper)
        worker.start()
        worker.join(timeout=timeout)
        
        with self._job_lock:
            job.completed_at = datetime.utcnow()
            
            if worker.is_alive():
                # Timeout - thread still running
                job.status = JobStatus.TIMEOUT
                job.error = f"Job exceeded timeout of {timeout} seconds"
                logger.error(f"Job {job_id} timed out after {timeout}s")
            elif result_container["error"]:
                job.status = JobStatus.FAILED
                job.error = result_container["error"]
                job.error_details = result_container.get("traceback")
                logger.error(f"Job {job_id} failed: {result_container['error']}")
            else:
                job.status = JobStatus.COMPLETED
                job.result = result_container["result"]
                job.progress = 100
                job.progress_message = "Completed"
                self._results[job_id] = result_container["result"]
                logger.info(f"Job {job_id} completed successfully")
    
    def update_progress(self, job_id: str, progress: int, message: str = ""):
        """Update job progress (called from within job function)."""
        with self._job_lock:
            job = self._jobs.get(job_id)
            if job and job.status == JobStatus.RUNNING:
                job.progress = min(99, max(0, progress))  # Cap at 99 until complete
                job.progress_message = message
    
    def get_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status (for polling)."""
        with self._job_lock:
            job = self._jobs.get(job_id)
            if not job:
                return None
            return job.to_dict()
    
    def get_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job result (only available when status=completed)."""
        with self._job_lock:
            job = self._jobs.get(job_id)
            if not job:
                return {"error": "Job not found", "job_id": job_id}
            
            if job.status == JobStatus.COMPLETED:
                return {
                    "status": "completed",
                    "job_id": job_id,
                    "data": job.result,
                    "duration_seconds": job._duration_seconds()
                }
            elif job.status == JobStatus.FAILED:
                return {
                    "status": "failed",
                    "job_id": job_id,
                    "error": job.error,
                    "error_details": job.error_details
                }
            elif job.status == JobStatus.TIMEOUT:
                return {
                    "status": "timeout",
                    "job_id": job_id,
                    "error": job.error
                }
            else:
                return {
                    "status": job.status.value,
                    "job_id": job_id,
                    "message": "Job not yet complete. Poll /status endpoint."
                }
    
    def cancel(self, job_id: str) -> bool:
        """Mark job as failed (cannot truly cancel thread in Python)."""
        with self._job_lock:
            job = self._jobs.get(job_id)
            if job and job.status in (JobStatus.PENDING, JobStatus.RUNNING):
                job.status = JobStatus.FAILED
                job.error = "Job cancelled by user"
                job.completed_at = datetime.utcnow()
                return True
        return False
    
    def _cleanup_loop(self):
        """Periodically clean up old jobs."""
        while True:
            time.sleep(self._cleanup_interval)
            self._cleanup_expired()
    
    def _cleanup_expired(self):
        """Remove jobs older than TTL."""
        now = datetime.utcnow()
        expired = []
        
        with self._job_lock:
            for job_id, job in self._jobs.items():
                age = (now - job.created_at).total_seconds()
                if age > self._job_ttl:
                    expired.append(job_id)
            
            for job_id in expired:
                del self._jobs[job_id]
                self._results.pop(job_id, None)
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired jobs")


# Singleton instance
job_manager = JobManager()
