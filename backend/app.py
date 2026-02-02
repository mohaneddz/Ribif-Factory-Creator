from flask import Flask
from flask_cors import CORS
import logging
import warnings
import traceback

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
CORS(app, resources={r"/*": {"origins": "*"}})

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
# GLOBAL ERROR HANDLERS - ALWAYS RETURN JSON
# =========================================================

@app.errorhandler(400)
def bad_request_error(error):
    from flask import jsonify, request
    return jsonify({
        "error": "Bad Request",
        "message": str(error.description) if hasattr(error, 'description') else str(error),
        "path": request.path,
        "method": request.method,
        "hint": "Check Content-Type header and request body format"
    }), 400


@app.errorhandler(404)
def not_found_error(error):
    from flask import jsonify, request
    return jsonify({
        "error": "Not Found",
        "message": f"The requested URL {request.path} was not found on this server.",
        "path": request.path
    }), 404


@app.errorhandler(405)
def method_not_allowed_error(error):
    from flask import jsonify, request
    return jsonify({
        "error": "Method Not Allowed",
        "message": f"The method {request.method} is not allowed for {request.path}",
        "path": request.path,
        "method": request.method
    }), 405


@app.errorhandler(413)
def request_entity_too_large(error):
    from flask import jsonify
    return jsonify({
        "error": "Request too large",
        "message": "The request body exceeds the maximum allowed size (100MB)"
    }), 413


@app.errorhandler(500)
def internal_server_error(error):
    from flask import jsonify, request
    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred. Please check server logs.",
        "path": request.path,
        "details": str(error) if app.debug else None
    }), 500


@app.errorhandler(Exception)
def handle_uncaught_exception(error):
    """Catch-all for any unhandled exceptions - ALWAYS return JSON."""
    from flask import jsonify, request
    
    # Log the full traceback
    tb = traceback.format_exc()
    logging.getLogger("flask").error(f"Uncaught exception on {request.path}: {error}\n{tb}")
    
    return jsonify({
        "error": "Internal Server Error",
        "message": str(error) if app.debug else "An unexpected error occurred",
        "path": request.path,
        "type": type(error).__name__
    }), 500


if __name__ == "__main__":
    app.run(
        debug=True, 
        port=5000, 
        use_reloader=False,
        threaded=True,  # Enable threading for concurrent requests
    )
