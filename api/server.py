import redis
import urllib.parse

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