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
