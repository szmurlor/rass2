import redis
from rq import Queue, Connection
from rq.job import Job
import os
import json
import logger
from datetime import datetime as dt


def _task_cached_histogram(processing_folder):
    logger.debug("Running _task_cached_histogram")

    data = {"cached": True }

    return {
        "data": data,
        "status": "finished"
    }


def _task_calculate_histogram(processing_folder):
    message = None
    if (os.path.isdir(processing_folder)):

        pars_fname = processing_folder + "/params-input.json"

        if (os.path.isfile(pars_fname)):            
            with open(pars_fname, "r") as fin:
                pars = (json.load(fin))
                logger.info(pars)

            status = "finished"

        else:
            logger.error(f"Brak pliku z parametrami: {pars_fname}")
            message = "Nie mogę odnaleźć pliku z parametrami do obliczenia histogramu."
    else:
        logger.error(f"Brak folderu: {processing_folder}")
        message = "Nie mogę odnaleźć folderu do obliczeń."

    data = {"cached": False}
    if message:
        data["message"] = message
    return {
        "data": data,
        "status": status
    }


def start_calculate_histogram_job(processing_folder):
    from rass_app import app
    with Connection(redis.from_url(app.config['REDIS_URL'])):
        q = Queue(app.config['REDIS_WORKER'])
        task = q.enqueue(_task_calculate_histogram, processing_folder)
        return task.get_id()


def start_cached_histogram_job(processing_folder):
    from rass_app import app
    with Connection(redis.from_url(app.config['REDIS_URL'])):
        q = Queue(app.config['REDIS_WORKER'])
        task = q.enqueue(_task_cached_histogram, processing_folder)
        return task.get_id()


def get_job(task_id):
    """ Szukam w kolejce zadań zadania o zadanym  id i zwracam status w słowniku. """
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