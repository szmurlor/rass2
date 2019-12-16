import redis
from rq import Queue, Connection
from rq.job import Job
import database
import os
import json
from datetime import datetime as dt

def _task_calculate_histogram(datauid, fluence_maps=None):
    import rass_app
    from rass_app import app
    datafile = database.StoredFile.query.filter_by(uid=datauid).one()    
    app.logger.info("Uruchomilem zadanie, które powinno obliczyć histogram dla pliku %s o nazwie %s" % (datauid, datafile.name))
    stamp = datafile.stored_at.strftime('%Y%m%d_%H%M%S')
    dirname = f'{app.config["PROCESSING_FOLDER"]}/{stamp}_{datafile.uid}';
    app.logger.info(dirname)

    if not os.path.isdir(dirname):
        os.mkdir(dirname)
    
    state = {
        'finished': False
    }
    if os.path.isfile(f"{dirname}/state.json"):
        with open(f"{dirname}/state.json") as f:
            state.update(json.load(f))

    if state['finished']:
        print("Zadanie skończone.")
        return {
            "status": "finished",
            "folder": dirname
        }

    state['started_at'] = dt.now().strftime('%Y%m%d %H:%M:%S');
    with open(f"{dirname}/state.json", "w") as f:
        json.dump(state,f)

    import time 
    time.sleep(4)
    print("Zakonczylem...")

    return {
        "status": "started"
    }


def calculate_histogram(datauid, fluence_maps=None):
    from rass_app import app
    print("Ala: %s" % app.config["PROCESSING_FOLDER"])
    with Connection(redis.from_url(app.config['REDIS_URL'])):
        q = Queue(app.config['REDIS_WORKER'])
        task = q.enqueue(_task_calculate_histogram, datauid, fluence_maps)
        response = {
            'status': 'success',
            'data': {
                'task_id': task.get_id()
            }
        }
        return response

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