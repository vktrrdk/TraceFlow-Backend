from redis import Redis
import os
from rq import Worker, Queue, Connection
import logging

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
r_con = Redis(host=REDIS_HOST, port=6379)


DICT_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
            'stream': 'ext://sys.stderr',  # Default is stderr
        },
    },
    'loggers': {
        'root': {  # root logger
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': False
        },
    }
}


if __name__ == '__main__':
    with Connection(r_con):
        logger = logging.getLogger('rq.worker')
        
        # Attach the logger to the console handler
        console_handler = logging.StreamHandler()
        logger.addHandler(console_handler)


        worker = Worker(map(Queue, ['request_queue']), exception_handlers=[logger])
        worker.work()


"""
TODO: need to get the logging running, so one sees the time for the operations - otherwise try to add a framework, which is able to show it
"""