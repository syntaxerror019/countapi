from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import redis
import os
import logging
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ------------------ Basic App Setup ------------------
app = Flask(__name__)
CORS(app)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ------------------ Rate Limiting ------------------
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100 per minute"],
    storage_uri=os.getenv("COUNTAPI_REDIS_URL") or "memory://",
    enabled=os.getenv("ENABLE_RATE_LIMIT", "false").lower() == "true",
    app=app  # must be last
)


# ------------------ Redis Wrapper ------------------
class Server:
    def __init__(self, url=None):
        try:
            # Use redis.from_url — handles password, port, host automatically
            redis_url = url or "redis://127.0.0.1:6379/0"
            self.client = redis.from_url(redis_url, decode_responses=True)
            self.client.ping()
            logger.info(f"Successfully connected to Redis at {redis_url}")
        except redis.AuthenticationError:
            logger.critical("Redis authentication failed. Check your password.")
            raise
        except redis.ConnectionError as e:
            logger.critical(f"Failed to connect to Redis: {e}")
            raise

    def get(self, key): return self.client.get(key)
    def set(self, key, value): return self.client.set(key, value)
    def increase(self, key, amount=1): return self.client.incrby(key, amount)
    def decrease(self, key, amount=1): return self.client.decrby(key, amount)
    def delete(self, key): return self.client.delete(key)
    def exists(self, key): return self.client.exists(key)
    def get_total_keys(self): return self.client.dbsize()

# ------------------ Initialize Redis ------------------
try:
    r = Server(url=os.getenv("COUNTAPI_REDIS_URL"))
except Exception as e:
    logger.critical(f"Failed to initialize Redis: {e}")
    r = None

APP_START_TIME = datetime.utcnow()

# ------------------ Helpers ------------------
WRITE_PROTECTED_KEYS = {'count.api.page.hits'}

def is_write_protected(key):
    return key in WRITE_PROTECTED_KEYS

def validate_key(key):
    if not key or len(key) > 200: return False
    forbidden = ['/', '\\', '\0', ' ', '\n', '\r', '\t']
    return not any(char in key for char in forbidden)

def handle_redis_errors(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if r is None: return jsonify({"error": "Service temporarily unavailable"}), 503
        try:
            return f(*args, **kwargs)
        except redis.RedisError as e:
            logger.error(f"Redis error in {f.__name__}: {e}")
            return jsonify({"error": "Database error occurred"}), 500
        except Exception as e:
            logger.error(f"Unexpected error in {f.__name__}: {e}")
            return jsonify({"error": "Internal server error"}), 500
    return wrapper

# ------------------ Page Hit Tracker ------------------
@app.before_request
def track_hits():
    if r and request.endpoint not in ['static', 'favicon']:
        try:
            r.increase('count.api.page.hits')
        except Exception as e:
            logger.warning(f"Failed to increment page hits: {e}")

# ------------------ Routes ------------------
@app.route('/')
def index(): return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'icon.png', mimetype='image/png')

@app.route('/api/v1/get/<key>', methods=['GET'])
@limiter.limit("10 per second")
@handle_redis_errors
def get_handler(key):
    if not validate_key(key): return jsonify({"error": "Invalid key"}), 400
    value = r.get(key)
    if value is None: return jsonify({"error": "Key not found"}), 404
    return jsonify({"key": key, "value": int(value) if value.isdigit() else value}), 200

@app.route('/api/v1/set/<key>', methods=['GET', 'POST'])
@limiter.limit("10 per second")
@handle_redis_errors
def set_handler(key):
    if not validate_key(key): return jsonify({"error": "Invalid key"}), 400
    if is_write_protected(key): return jsonify({"error": "This key is write-protected"}), 403
    value = request.get_json(silent=True, force=True) or {}
    value = value.get('value') if request.method == 'POST' else request.args.get('value')
    if value is None: return jsonify({"error": "No value provided"}), 400
    try: int_value = int(value)
    except ValueError: return jsonify({"error": "Value must be integer"}), 400
    old_value = r.get(key)
    r.set(key, int_value)
    resp = {"key": key, "value": int_value}
    if old_value: resp["old_value"] = int(old_value) if old_value.isdigit() else old_value
    return jsonify(resp), 200

@app.route('/api/v1/hit/<key>', methods=['GET', 'POST'])
@limiter.limit("10 per second")
@handle_redis_errors
def hit_handler(key):
    if not validate_key(key): return jsonify({"error": "Invalid key"}), 400
    if is_write_protected(key): return jsonify({"error": "This key is write-protected"}), 403
    try:
        amount = int(request.args.get('amount', 1))
        if not (1 <= amount <= 100): raise ValueError
    except ValueError: return jsonify({"error": "Amount must be 1-100"}), 400
    new_value = r.increase(key, amount)
    return jsonify({"key": key, "value": int(new_value)}), 200

@app.route('/api/v1/status', methods=['GET'])
@limiter.limit("30 per minute")
@handle_redis_errors
def status_handler():
    info = r.client.info()
    uptime = info.get("uptime_in_seconds", 0)
    days = uptime // 86400
    hours = (uptime % 86400) // 3600
    page_hits = r.get('count.api.page.hits') or 0
    return jsonify({
        "status": "operational",
        "version": "2.1",
        "uptime_seconds": uptime,
        "uptime": f"{days}d {hours}h",
        "total_requests": int(page_hits),
        "total_keys": r.get_total_keys(),
        "redis_version": info.get("redis_version"),
        "connected_clients": info.get("connected_clients"),
        "used_memory_human": info.get("used_memory_human"),
        "total_commands_processed": info.get("total_commands_processed")
    }), 200

# ------------------ Error Handlers ------------------
@app.errorhandler(429)
def ratelimit_handler(e): return jsonify({"error": "Rate limit exceeded"}), 429
@app.errorhandler(404)
def not_found(e): return jsonify({"error": "Endpoint not found"}), 404
@app.errorhandler(500)
def internal_error(e): return jsonify({"error": "Internal server error"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    try:
        r.client.ping() if r else None
        return jsonify({"status": "healthy"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "reason": str(e)}), 503

if __name__ == '__main__':
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
