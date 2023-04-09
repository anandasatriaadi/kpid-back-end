import os

import redis
from rq import Connection, Queue, Worker

listen = ['default']

redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = os.getenv('REDIS_PORT', '6379')
redis_password = os.getenv('REDIS_PASSWORD', '')

conn = redis.from_url(f'redis://:{redis_password}@{redis_host}:{redis_port}')

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()
