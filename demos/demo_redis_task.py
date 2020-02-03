import logger as log
import rass_app
from rass_app import app

import redis
from rq import Queue, Connection, Worker
from rq.job import Job

from demos.demo_task import do_something

EXAMPLE_WORKER_QUEUE="demo_worker"


def check_redis_started():
    rs = redis.from_url(app.config['REDIS_URL'])
    try:
        res = rs.client_list()
        log.info(f"Succesfully connected to redis server: {app.config['REDIS_URL']}")
    except Exception as e:
        log.info("There is no redis: ", e)



def add_task():
    message_to_echo = "Witaj Świecie"
    red = redis.from_url(app.config['REDIS_URL'])
    with Connection(red):
        q = Queue(EXAMPLE_WORKER_QUEUE)
        task = q.enqueue(do_something, message_to_echo)
        return task    

    
def wait_for_task(task_id):
    import time
    red = redis.from_url(app.config['REDIS_URL'])
    with Connection(red):
        j = Job.fetch(task_id)
        while j.get_status() in ['queued','started']:
            log.info(f'waiting for job {task_id}')
            time.sleep(0.1)
            j = Job.fetch(task_id)
        log.info(f'Job status is: {j.get_status()}')

        if j.get_status() == 'finished':
            return j.result
        
        return None

#app.config['REDIS_URL'] = "redis://localhost:6379/0"
# = "rass2-worker"

def run_worker():
    redis_url = app.config['REDIS_URL']
    redis_connection = redis.from_url(redis_url)
    with Connection(redis_connection):
        worker = Worker(EXAMPLE_WORKER_QUEUE)
        worker.work()


def start_worker():
    from multiprocessing import Process
    p = Process(target=run_worker, args=())
    p.start()
    return p


if __name__ == "__main__":
    check_redis_started()
    worker_process = start_worker()
    t = add_task()
    r = wait_for_task(t.id)
    print(f"Result from job is: {r}")
    worker_process.terminate()