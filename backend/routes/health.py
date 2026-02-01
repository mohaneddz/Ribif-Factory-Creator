"""
System Health Check Route
==========================

Provides comprehensive health status of all services, quotas, and system resources.
"""

from flask import Blueprint, jsonify
from typing import Dict, Any
import time
import os

from utils.quota_manager import get_service_health, get_all_quota_status
from utils.logger import get_logger
from config import WEB_SEARCH_ENABLED

logger = get_logger(__name__)

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """
    Comprehensive system health check.
    
    Returns:
        {
            "status": "healthy" | "degraded" | "critical",
            "timestamp": float,
            "services": {...},
            "quotas": {...},
            "configuration": {...},
            "system": {...}
        }
    """
    try:
        # Service health (quotas)
        service_health = get_service_health()
        
        # Configuration status
        config_status = {
            "web_search_enabled": WEB_SEARCH_ENABLED,
            "environment": os.getenv("ENVIRONMENT", "development"),
            "vertex_configured": bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")),
            "serper_configured": bool(os.getenv("SERPER_API_KEY")),
            "supabase_configured": bool(os.getenv("SUPABASE_URL")),
        }
        
        # System resources
        try:
            import psutil
            system_status = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
            }
        except ImportError:
            system_status = {"available": False, "note": "psutil not installed"}
        
        # Overall status determination
        if service_health["exhausted_services"] == 0:
            overall_status = "healthy"
        elif service_health["exhausted_services"] < service_health["total_services"] / 2:
            overall_status = "degraded"
        else:
            overall_status = "critical"
        
        return jsonify({
            "status": overall_status,
            "timestamp": time.time(),
            "services": service_health,
            "quotas": get_all_quota_status(),
            "configuration": config_status,
            "system": system_status
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "error",
            "timestamp": time.time(),
            "error": str(e)
        }), 500


@health_bp.route('/health/ready', methods=['GET'])
def readiness_check():
    """
    Kubernetes-style readiness check.
    Returns 200 if system can accept requests, 503 otherwise.
    """
    try:
        service_health = get_service_health()
        
        # Not ready if all services exhausted
        if service_health["exhausted_services"] == service_health["total_services"] and service_health["total_services"] > 0:
            return jsonify({
                "ready": False,
                "reason": "All API quotas exhausted"
            }), 503
        
        return jsonify({"ready": True}), 200
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({"ready": False, "reason": str(e)}), 503


@health_bp.route('/health/live', methods=['GET'])
def liveness_check():
    """
    Kubernetes-style liveness check.
    Returns 200 if application is running.
    """
    return jsonify({"live": True, "timestamp": time.time()}), 200


@health_bp.route('/health/metrics', methods=['GET'])
def metrics():
    """
    Prometheus-style metrics endpoint.
    Returns key metrics in simple text format.
    """
    try:
        service_health = get_service_health()
        quotas = get_all_quota_status()
        
        lines = []
        lines.append(f"# HELP system_health Overall system health (1=healthy, 0=degraded)")
        lines.append(f"# TYPE system_health gauge")
        lines.append(f"system_health {1 if service_health['overall_health'] == 'healthy' else 0}")
        
        lines.append(f"# HELP service_quota_exhausted Services with exhausted quotas")
        lines.append(f"# TYPE service_quota_exhausted gauge")
        lines.append(f"service_quota_exhausted {service_health['exhausted_services']}")
        
        for service_name, quota_info in quotas.items():
            safe_name = service_name.replace("_", "").replace("-", "")
            
            lines.append(f"# HELP quota_calls_made_{safe_name} Calls made to {service_name}")
            lines.append(f"# TYPE quota_calls_made_{safe_name} counter")
            lines.append(f"quota_calls_made_{{{safe_name}}} {quota_info['calls_made']}")
            
            lines.append(f"# HELP quota_errors_{safe_name} Errors from {service_name}")
            lines.append(f"# TYPE quota_errors_{safe_name} counter")
            lines.append(f"quota_errors_{{{safe_name}}} {quota_info['errors']}")
        
        return "\n".join(lines), 200, {"Content-Type": "text/plain"}
        
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        return f"# Error: {str(e)}", 500


@health_bp.route('/health/reset', methods=['POST'])
def reset_quotas():
    """
    ADMIN ONLY: Reset all quota trackers.
    Use with caution - only for testing/recovery.
    """
    # TODO: Add authentication/authorization
    from utils.quota_manager import reset_quota_tracker
    
    try:
        reset_quota_tracker()
        logger.info("All quota trackers reset")
        return jsonify({
            "success": True,
            "message": "All quota trackers reset"
        }), 200
    except Exception as e:
        logger.error(f"Failed to reset quotas: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
