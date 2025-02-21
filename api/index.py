from flask import Flask, request, jsonify, render_template
import redis


class Server:
    def __init__(self, host='localhost', port=6379, password="", ssl=True):
        self.client = redis.Redis(
            host=host,
            port=port,
            password=password,
            ssl=ssl
        )

    def get(self, key):
        return self.client.get(key)

    def set(self, key, value):
        return self.client.set(key, value)

    def increase(self, key, amount=1):
        return self.client.incrby(key, amount)

    def decrease(self, key, amount=1):
        return self.client.decrby(key, amount)


app = Flask(__name__)

r = Server(
  host='rich-deer-51846.upstash.io',
  port=6379,
  password='AcqGAAIjcDE4YzRjYTJmZmFiYTI0YzYwYmI1YWFjMWFhNGFkMWE5YXAxMA',
  ssl=True
)


@app.before_request
def before_request():
    r.increase('hits')


@app.route('/')
def index():
    return render_template('index.html', hits=r.get('hits').decode('utf-8'), info=r.client.info())  # # noqa: E501


@app.route('/api/v1/get/<key>', methods=['GET'])
def get_handler(key):
    value = r.get(key)
    if value is None:
        return jsonify({"error": "Key not found"}), 404
    return jsonify({"message": "Key requested successfully", "key": key, "value": value.decode('utf-8')}), 200  # noqa: E501


@app.route('/api/v1/set/<key>', methods=['GET'])
def set_handler(key):
    value = request.args.get('value', None)

    if value is None:
        return jsonify({"error": "No value provided"}), 400
    if key is None:
        return jsonify({"error": "No key provided"}), 400
    if not value.isdigit():
        return jsonify({"error": "Value must be an integer"}), 400

    old_value = r.get(key).decode('utf-8') if r.get(key) else None
    r.set(key, value)

    return jsonify({"message": "Key set successfully", "key": key, "value": value, "old_value": old_value}), 200  # noqa: E501


@app.route('/api/v1/hit/<key>', methods=['GET'])
def hit_handler(key):
    r.increase(key)
    value = r.get(key).decode('utf-8')
    return jsonify({"message": "Key updated successfully", "key": key, "value": value}), 200  # noqa: E501


@app.route('/api/v1/status/memory', methods=['GET'])
def status_memory_handler():
    print(r.client.info('memory'))
    return jsonify({"message": "Memory status", "used_memory": r.client.info('memory')}), 200  # noqa: E501


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
