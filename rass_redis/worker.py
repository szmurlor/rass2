import redis
from rq import Queue, Connection
from rq.job import Job
import database
import os
import json
from datetime import datetime as dt

def _task_calculate_histogram(processing_folder):
    print(f"TASK CALCULATE in folder: {processing_folder}")
    data = {}
    if not os.path.isdir(processing_folder):
        data["cached"] = False
        os.mkdir(processing_folder)

        with open(processing_folder + "/params-input.json", "w") as fout:
            pars = {
                "beamlets": beamlets.uid,
                "beamlets_name": beamlets.name,
                "beamlets_path": beamlets.path,
                "fluences": [ {
                    "uid": f.uid,
                    "name": f.name,
                    "path": f.path,
                    } for f in fluences]
            }
            fout.write(json.dumps(pars))

    else:            
        data["cached"] = True

    return {
        "data": data,
        "status": "finished"
    }


def calculate_histogram(processing_folder):
    from rass_app import app
    with Connection(redis.from_url(app.config['REDIS_URL'])):
        q = Queue(app.config['REDIS_WORKER'])
        task = q.enqueue(_task_calculate_histogram, processing_folder)
        return task.get_id()


def get_job(task_id):
    """ Szukam w kolejce zadąń zadania o zadanym  id i zwracam status w słowniku. """
    from rass_app import app
    with Connection(redis.from_url(app.config['REDIS_URL'])) as con:
        try:
            job = Job.fetch(task_id, connection=con)
            if job is not None:
                response = {
                    'status': job.get_status(),
                    'job': job.result
                }
            else:
                response = {
                    'status': f"Brak zadania o identyfikatorze {task_id}",
                }
        except Exception as e:
            response = {
                    'status': f"Błąd podczas komunikacji z kolejką zadań: {e}",
            }
        return response