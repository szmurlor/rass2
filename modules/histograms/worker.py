import redis
from rq import Queue, Connection
from rq.job import Job
import database
import os
import json
from datetime import datetime as dt

def _task_calculate_histogram(processing_folder):
    print("TASK CALCULATE!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    return {
        "status": "finished"
    }


def calculate_histogram(processing_folder):
    from rass_app import app
    with Connection(redis.from_url(app.config['REDIS_URL'])):
        q = Queue(app.config['REDIS_WORKER'])
        task = q.enqueue(_task_calculate_histogram, processing_folder)
        return task.get_id()

def get_job(task_id):
    from rass_app import app
    with Connection(redis.from_url(app.config['REDIS_URL'])) as con:
        job = Job.fetch(task_id, connection=con)
        response = {
            'status': job.get_status(),
            'data': {
                'status': dir(job)
            }
        }
        return response