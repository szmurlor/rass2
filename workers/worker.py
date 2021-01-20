import redis
from rq import Queue, Connection
from rq.job import Job
import os
import json
import logger
import time
from datetime import datetime as dt
from workers.tasklog import TaskLog


def _task_cached_histogram(processing_folder):
    logger.debug("Running _task_cached_histogram")

    data = {"cached": True }

    return {
        "data": data,
        "status": "finished"
    }


def dev_only_delay(secs):
    if "DEV_DELAY" in os.environ:
        time.sleep(secs) # just for fun....


def _task_calculate_histogram(processing_folder):
    import shutil
    import zipfile

    message = None
    if (os.path.isdir(processing_folder)):
        task_log = TaskLog(processing_folder + "/_task.log")

        pars_fname = processing_folder + "/params-input.json"

        if (os.path.isfile(pars_fname)):
            proc_dir = processing_folder + "/processing"
            if (not os.path.isdir(proc_dir)):
                task_log.log("Creating procesing folder...")
                os.makedirs(proc_dir)
            
            ######################################################
            task_log.log("Reading task parameters...")
            with open(pars_fname, "r") as fin:
                pars = (json.load(fin))
                logger.debug(f"Read pars from {pars_fname} file: {pars}")
            dev_only_delay(1)
            task_log.log("Done.", 1)

            ######################################################
            task_log.log("Copying beamlets file...")
            bpath = pars['beamlets_path']
            bname = pars['beamlets_name']
            res = shutil.copy(bpath, processing_folder + "/" + bname)
            logger.debug(f"Copied file to: {res}")
            dev_only_delay(1)
            task_log.log("Done.", 5)

            ######################################################
            task_log.log("Unzipping beamlets file. This may take a while...")
            dev_only_delay(1)
            with zipfile.ZipFile(res) as z:
                logger.info(f"Rozpakowuję do folderu: {proc_dir}")
                z.extractall(proc_dir)
            task_log.log("Done.", 30)

            ######################################################
            task_log.log("Finding m_* file...")
            m_file = None
            only_dirs = True
            first_dir = None
            for fn in os.listdir(proc_dir):
                if not os.path.isdir(proc_dir + "/" + fn):
                    only_dirs = False
                else:
                    if first_dir is None: 
                        first_dir = "/" + fn
            if not only_dirs:
                first_dir = ""            


            for fn in os.listdir(proc_dir + first_dir):
                print(f"plik: {fn}")
                if fn.startswith("m_"):
                    m_file = proc_dir + first_dir + "/" + fn
                    break
            
            if m_file is not None:
                task_log.log(f"Found m_file in the archive: {m_file}")

                ######################################################
                task_log.log("Calculating histograms...")
                dev_only_delay(1)

                from workers.histogram import DosesMain
                main = DosesMain(m_file, task_log)
                main.save_png_preview_fluence = True
                hist = main.histogram()

                hist_fname = f"{processing_folder}/histogram.json"
                with open(hist_fname, "w") as f:       
                    print(hist)
                    json.dump(hist, f)
                
                task_log.log("Done.", 50)
            else:
                task_log.log("Error! Unable to find file with its name starting with 'm_'...", 100)


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
        task = q.enqueue(_task_calculate_histogram, processing_folder, job_timeout='30m')
        return task.get_id()


def start_cached_histogram_job(processing_folder):
    from rass_app import app
    with Connection(redis.from_url(app.config['REDIS_URL'])):
        q = Queue(app.config['REDIS_WORKER'])
        task = q.enqueue(_task_cached_histogram, processing_folder, job_timeout='30m')
        return task.get_id()


def get_job(task_id):
    """ Szukam w kolejce zadań zadania o zadanym  id i zwracam status w słowniku. """
    from rass_app import app
    with Connection(redis.from_url(app.config['REDIS_URL'])) as con:
        try:
            job = Job.fetch(task_id, connection=con)
            if job is not None:
                taskLogs = None
                print(f"Folder processing: {job.args[0]}")
                if os.path.isdir(job.args[0]):
                    taskLog = job.args[0] + "/_task.log"
                    if os.path.isfile(taskLog):
                        with open(taskLog,"r") as f:
                            taskLogs = json.load(f)
                response = {
                    'status': job.get_status(),
                    'job': job.result,
                    'args': job.args
                }
                if taskLogs is not None:
                    response["taskLogs"] = taskLogs
            else:
                response = {
                    'status': f"Brak zadania o identyfikatorze {task_id}",
                }
        except Exception as e:
            response = {
                    'status': f"Błąd podczas komunikacji z kolejką zadań: {e}",
            }
        return response