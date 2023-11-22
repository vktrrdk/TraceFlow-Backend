from redis import Redis
import os
from rq import Worker, Queue, Connection
import logging

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
r_con = Redis(host=REDIS_HOST, port=6379)

if __name__ == '__main__':
    with Connection(r_con):
        logger = logging.getLogger('rq.worker')
        
        # Attach the logger to the console handler
        console_handler = logging.StreamHandler()
        logger.addHandler(console_handler)


        worker = Worker(map(Queue, ['request_queue']), exception_handlers=[logger])
        worker.work()