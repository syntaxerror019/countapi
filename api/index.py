from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
import urllib.parse
import os
import logging
from datetime import datetime
from functools import wraps

# Version 2!!!
app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per minute"],
    storage_uri=os.getenv("COUNTAPI_REDIS_URL") or "memory://",
    enabled=os.getenv("ENABLE_RATE_LIMIT", "false").lower() == "true"
)

class Server:
    def __init__(self, url=None):
        if url:
            parsed = urllib.parse.urlparse(url)
            password = parsed.password
            host = parsed.hostname
            port = parsed.port
            ssl = parsed.scheme == 'rediss'
        else:
            host = 'localhost'
            port = 6379
            password = None
            ssl = False
        
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                password=password,
                ssl=ssl,
                decode_responses=True,
                socket_keepalive=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test connection
            self.client.ping()
            logger.info(f"Successfully connected to Redis at {host}:{port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def get(self, key):
        try:
            return self.client.get(key)
        except redis.RedisError as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            raise
    
    def set(self, key, value):
        try:
            return self.client.set(key, value)
        except redis.RedisError as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
            raise
    
    def increase(self, key, amount=1):
        try:
            return self.client.incrby(key, amount)
        except redis.RedisError as e:
            logger.error(f"Redis INCRBY error for key '{key}': {e}")
            raise
    
    def decrease(self, key, amount=1):
        try:
            return self.client.decrby(key, amount)
        except redis.RedisError as e:
            logger.error(f"Redis DECRBY error for key '{key}': {e}")
            raise
    
    def delete(self, key):
        try:
            return self.client.delete(key)
        except redis.RedisError as e:
            logger.error(f"Redis DELETE error for key '{key}': {e}")
            raise
    
    def exists(self, key):
        """Check if key exists"""
        try:
            return self.client.exists(key)
        except redis.RedisError as e:
            logger.error(f"Redis EXISTS error for key '{key}': {e}")
            raise
    
    def get_total_keys(self):
        """Get total number of keys (expensive operation, use sparingly)"""
        try:
            return self.client.dbsize()
        except redis.RedisError as e:
            logger.error(f"Redis DBSIZE error: {e}")
            return None

# Initialize Redis
try:
    r = Server(url=os.getenv("COUNTAPI_REDIS_URL"))
except Exception as e:
    logger.critical(f"Failed to initialize Redis: {e}")
    r = None

# Store app start time for uptime calculation
APP_START_TIME = datetime.utcnow()

def validate_key(key):
    """Validate key format and length"""
    if not key or len(key) > 200:
        return False
    # Prevent certain characters that might cause issues
    forbidden_chars = ['/', '\\', '\0', ' ', '\n', '\r', '\t']
    return not any(char in key for char in forbidden_chars)

def handle_redis_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if r is None:
            return jsonify({"error": "Service temporarily unavailable"}), 503
        try:
            return f(*args, **kwargs)
        except redis.RedisError as e:
            logger.error(f"Redis error in {f.__name__}: {e}")
            return jsonify({"error": "Database error occurred"}), 500
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {e}")
            return jsonify({"error": "Internal server error"}), 500
    return decorated_function

@app.before_request
def before_request():
    if r and request.endpoint not in ['static', 'favicon']:
        try:
            r.increase('count.api.page.hits')
        except Exception as e:
            logger.warning(f"Failed to increment page hits: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'icon.png',
        mimetype='image/png'
    )

@app.route('/api/v1/get/<key>', methods=['GET'])
@limiter.limit("10 per second")
@handle_redis_errors
def get_handler(key):
    if not validate_key(key):
        return jsonify({"error": "Invalid key format"}), 400
    
    value = r.get(key)
    if value is None:
        return jsonify({"error": "Key not found"}), 404
    
    try:
        return jsonify({
            "message": "Key requested successfully",
            "key": key,
            "value": int(value)
        }), 200
    except ValueError:
        return jsonify({
            "message": "Key requested successfully",
            "key": key,
            "value": value
        }), 200

@app.route('/api/v1/set/<key>', methods=['GET', 'POST'])
@limiter.limit("10 per second")
@handle_redis_errors
def set_handler(key):
    """Set the value of a key"""
    if not validate_key(key):
        return jsonify({"error": "Invalid key format"}), 400
    
    # Support both GET and POST
    if request.method == 'POST':
        data = request.get_json() or {}
        value = data.get('value')
    else:
        value = request.args.get('value')
    
    if value is None:
        return jsonify({"error": "No value provided"}), 400
    
    # Allow negative integers
    try:
        int_value = int(value)
    except ValueError:
        return jsonify({"error": "Value must be an integer"}), 400
    
    old_value = r.get(key)
    r.set(key, int_value)
    
    response = {
        "message": "Key set successfully",
        "key": key,
        "value": int_value
    }
    
    if old_value is not None:
        try:
            response["old_value"] = int(old_value)
        except ValueError:
            response["old_value"] = old_value
    
    return jsonify(response), 200

@app.route('/api/v1/hit/<key>', methods=['GET', 'POST'])
@limiter.limit("10 per second")
@handle_redis_errors
def hit_handler(key):
    """Increment a key by 1 (or specified amount)"""
    if not validate_key(key):
        return jsonify({"error": "Invalid key format"}), 400
    
    # Optional: support custom increment amount
    amount = request.args.get('amount', 1)
    try:
        amount = int(amount)
        if amount < 1 or amount > 100:
            return jsonify({"error": "Amount must be between 1 and 100"}), 400
    except ValueError:
        return jsonify({"error": "Amount must be an integer"}), 400
    
    new_value = r.increase(key, amount)
    return jsonify({
        "message": "Key updated successfully",
        "key": key,
        "value": int(new_value)
    }), 200

@app.route('/api/v1/status', methods=['GET'])
@limiter.limit("10 per second")
@handle_redis_errors
def status_handler():
    """Get API status and statistics"""
    info = r.client.info()
    
    # Calculate uptime
    uptime = datetime.utcnow() - APP_START_TIME
    uptime_seconds = int(uptime.total_seconds())
    uptime_days = uptime_seconds // 86400
    uptime_hours = (uptime_seconds % 86400) // 3600
    
    # Get total keys
    total_keys = r.get_total_keys()
    
    # Get page hits
    page_hits = r.get('count.api.page.hits')
    
    # Return simplified, useful stats
    return jsonify({
        "status": "operational",
        "version": "2.1",
        "uptime_seconds": uptime_seconds,
        "uptime": f"{uptime_days}d {uptime_hours}h",
        "total_requests": int(page_hits) if page_hits else 0,
        "total_keys": total_keys,
        "redis_version": info.get("redis_version"),
        "connected_clients": info.get("connected_clients"),
        "used_memory_human": info.get("used_memory_human"),
        "total_commands_processed": info.get("total_commands_processed"),
    }), 200

@app.route('/api/v1/info/<key>', methods=['GET'])
@limiter.limit("10 per second")
@handle_redis_errors
def info_handler(key):
    """Get information about a key (exists, value, etc.)"""
    if not validate_key(key):
        return jsonify({"error": "Invalid key format"}), 400
    
    exists = r.exists(key)
    
    if not exists:
        return jsonify({
            "key": key,
            "exists": False
        }), 200
    
    value = r.get(key)
    
    return jsonify({
        "key": key,
        "exists": True,
        "value": int(value) if value and value.lstrip('-').isdigit() else value
    }), 200

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit errors"""
    return jsonify({
        "error": "Rate limit exceeded",
        "message": str(e.description)
    }), 429

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    if request.path.startswith('/api/'):
        return jsonify({"error": "Endpoint not found"}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    try:
        if r:
            r.client.ping()
            return jsonify({"status": "healthy"}), 200
        else:
            return jsonify({"status": "unhealthy", "reason": "Redis not initialized"}), 503
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "reason": str(e)}), 503

if __name__ == '__main__':
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)