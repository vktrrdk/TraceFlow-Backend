from redis import Redis
import os
from rq import Worker, Queue, Connection
import logging

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
r_con = Redis(host=REDIS_HOST, port=6379)

if __name__ == '__main__':
    queue = Queue("request_queue", connection=r_con)
    queue.empty()