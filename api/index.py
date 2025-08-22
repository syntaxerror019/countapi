from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import redis
import urllib.parse
import os

app = Flask(__name__)
CORS(app)


class Server:
    def __init__(self, url=None):
        """
        url: rediss://:password@host:port
        """
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

        self.client = redis.Redis(
            host=host,
            port=port,
            password=password,
            ssl=ssl,
            decode_responses=True,  # automatically decode bytes to str
            socket_keepalive=True,
        )

    def get(self, key):
        return self.client.get(key)

    def set(self, key, value):
        return self.client.set(key, value)

    def increase(self, key, amount=1):
        return self.client.incrby(key, amount)

    def decrease(self, key, amount=1):
        return self.client.decrby(key, amount)

    def delete(self, key):
        return self.client.delete(key)

r = Server(url=os.getenv("COUNTAPI_REDIS_URL"))  # set REDIS_URL to your rediss://... URL


@app.before_request
def before_request():
    r.increase('count.api.page.hits')

@app.route('/')
def index():
    return render_template('index.html', hits=r.get('count.api.page.hits') or 0, info=r.client.info())

@app.route('/api/v1/get/<key>', methods=['GET'])
def get_handler(key):
    value = r.get(key)
    if value is None:
        return jsonify({"error": "Key not found"}), 404
    return jsonify({"message": "Key requested successfully", "key": key, "value": value}), 200

@app.route('/api/v1/set/<key>', methods=['GET'])
def set_handler(key):
    value = request.args.get('value')
    if value is None:
        return jsonify({"error": "No value provided"}), 400
    if not value.isdigit():
        return jsonify({"error": "Value must be an integer"}), 400

    old_value = r.get(key)
    r.set(key, value)
    return jsonify({"message": "Key set successfully", "key": key, "value": value, "old_value": old_value}), 200

@app.route('/api/v1/hit/<key>', methods=['GET'])
def hit_handler(key):
    new_value = r.increase(key)
    return jsonify({"message": "Key updated successfully", "key": key, "value": new_value}), 200

@app.route('/api/v1/status/memory', methods=['GET'])
def status_memory_handler():
    mem_info = r.client.info('memory')
    return jsonify({"message": "Memory status", "used_memory": mem_info}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
