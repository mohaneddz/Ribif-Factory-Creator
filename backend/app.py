# =========================================================
# ONNX RUNTIME CONFIGURATION - MUST BE BEFORE ANY IMPORTS
# =========================================================
# Configure ONNX Runtime for serverless environments to prevent crashes
# from CPU feature detection failures in containers (e.g., Leapcell)
# These MUST be set before any module imports onnxruntime
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("ONNXRUNTIME_DISABLE_ALL_OPTIMIZATION", "1")
os.environ.setdefault("ORT_DISABLE_ALL", "1")

from flask import Flask, request
from flask_cors import CORS
import logging
import warnings
import traceback
import os

# =========================================================
# GLOBAL LOGGING/WARNING SUPPRESSION
# =========================================================
# Suppress the persistent "Storage endpoint URL should have a trailing slash" warning
warnings.filterwarnings("ignore", message="Storage endpoint URL should have a trailing slash")

# Suppress noisy loggers from Supabase and HTTP libraries affecting stdout
for name in ["supabase", "storage3", "gotrue", "postgrest", "httpx", "httpcore"]:
    logging.getLogger(name).setLevel(logging.ERROR)

from routes.common import bp_common
from routes.module1 import bp_module1
from routes.module2 import bp_module2
from routes.module3 import bp_module3
from routes.module4 import bp_module4
from routes.module_5 import bp_module5
from routes.module6 import bp_module6
from routes.module7 import bp_module7
from routes.module9 import bp_module9
from routes.email_service import bp_email_service
from routes.validation import bp_validation
from routes.health import health_bp

app = Flask(__name__)

# =========================================================
# CORS CONFIGURATION - ALLOW ALL ORIGINS (DIE CORS DIE)
# =========================================================
# Get allowed origins from environment or allow all
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
if CORS_ORIGINS != "*":
    CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS.split(",")]

CORS(
    app,
    resources={r"/*": {"origins": CORS_ORIGINS}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-User-Id", "X-Project-Id", "Accept", "Origin"],
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    expose_headers=["Content-Type", "X-Total-Count", "Content-Disposition"],
    max_age=86400,  # Cache preflight requests for 24 hours
)


@app.before_request
def handle_preflight():
    """Handle OPTIONS preflight requests explicitly."""
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        return response


@app.after_request
def add_cors_headers(response):
    """Add CORS headers to every response as a fallback."""
    origin = request.headers.get("Origin", "*")
    
    # If CORS_ORIGINS is "*", allow any origin
    if CORS_ORIGINS == "*":
        response.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
    elif origin and origin in CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
    elif isinstance(CORS_ORIGINS, list) and CORS_ORIGINS:
        # For credentialed requests, we must echo the exact origin or use specific allowed origin
        # Check if request might be from localhost variants
        if origin and any(allowed in origin or origin in allowed for allowed in CORS_ORIGINS):
            response.headers["Access-Control-Allow-Origin"] = origin
        else:
            # Default to first allowed origin for non-credentialed requests
            response.headers["Access-Control-Allow-Origin"] = CORS_ORIGINS[0]
    else:
        response.headers["Access-Control-Allow-Origin"] = "*"
    
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, X-User-Id, X-Project-Id, Accept, Origin"
    response.headers["Access-Control-Expose-Headers"] = "Content-Type, X-Total-Count, Content-Disposition"
    response.headers["Access-Control-Max-Age"] = "86400"
    
    return response

# Increase timeouts for long-running enrichment operations
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload
app.config['JSON_AS_ASCII'] = False  # Allow non-ASCII characters in JSON
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False  # Faster JSON responses

app.register_blueprint(bp_common)
app.register_blueprint(bp_module1)
app.register_blueprint(bp_module2)
app.register_blueprint(bp_module3)
app.register_blueprint(bp_module4)
app.register_blueprint(bp_module5)
app.register_blueprint(bp_module6)
app.register_blueprint(bp_module7)
app.register_blueprint(bp_module9)
app.register_blueprint(bp_email_service)
app.register_blueprint(bp_validation)
app.register_blueprint(health_bp)

# =========================================================
# GLOBAL ERROR HANDLERS - ALWAYS RETURN JSON WITH CORS
# =========================================================

def _add_cors_to_response(response):
    """Helper to add CORS headers to error responses."""
    origin = request.headers.get("Origin", "*")
    if CORS_ORIGINS == "*":
        response.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
    elif isinstance(CORS_ORIGINS, list) and origin in CORS_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
    else:
        response.headers["Access-Control-Allow-Origin"] = CORS_ORIGINS[0] if isinstance(CORS_ORIGINS, list) else "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With, X-User-Id, X-Project-Id, Accept, Origin"
    return response


@app.errorhandler(400)
def bad_request_error(error):
    from flask import jsonify, request
    response = jsonify({
        "error": "Bad Request",
        "message": str(error.description) if hasattr(error, 'description') else str(error),
        "path": request.path,
        "method": request.method,
        "hint": "Check Content-Type header and request body format"
    })
    return _add_cors_to_response(response), 400


@app.errorhandler(404)
def not_found_error(error):
    from flask import jsonify, request
    response = jsonify({
        "error": "Not Found",
        "message": f"The requested URL {request.path} was not found on this server.",
        "path": request.path
    })
    return _add_cors_to_response(response), 404


@app.errorhandler(405)
def method_not_allowed_error(error):
    from flask import jsonify, request
    response = jsonify({
        "error": "Method Not Allowed",
        "message": f"The method {request.method} is not allowed for {request.path}",
        "path": request.path,
        "method": request.method
    })
    return _add_cors_to_response(response), 405


@app.errorhandler(413)
def request_entity_too_large(error):
    from flask import jsonify
    response = jsonify({
        "error": "Request too large",
        "message": "The request body exceeds the maximum allowed size (100MB)"
    })
    return _add_cors_to_response(response), 413


@app.errorhandler(500)
def internal_server_error(error):
    from flask import jsonify, request
    response = jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred. Please check server logs.",
        "path": request.path,
        "details": str(error) if app.debug else None
    })
    return _add_cors_to_response(response), 500


@app.errorhandler(Exception)
def handle_uncaught_exception(error):
    """Catch-all for any unhandled exceptions - ALWAYS return JSON with CORS."""
    from flask import jsonify, request
    
    # Log the full traceback
    tb = traceback.format_exc()
    logging.getLogger("flask").error(f"Uncaught exception on {request.path}: {error}\n{tb}")
    
    response = jsonify({
        "error": "Internal Server Error",
        "message": str(error) if app.debug else "An unexpected error occurred",
        "path": request.path,
        "type": type(error).__name__
    })
    return _add_cors_to_response(response), 500


if __name__ == "__main__":
    app.run(
        debug=True, 
        port=5000, 
        use_reloader=False,
        threaded=True,  # Enable threading for concurrent requests
    )
