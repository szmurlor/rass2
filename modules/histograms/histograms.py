# -*- encoding: utf-8
import os
import storage
import json

from flask import g, abort, render_template, flash, redirect, session, jsonify, redirect
import database
import logger
from rass_app import app, protected
import workers.worker as redis_worker
from utils import merge_http_request_arguments



@app.route('/histogram/<ftokens>')
@protected
def histogram(ftokens):
    """Opis działania:
        1. pobieram wszystkie pliki z bazy danych podane po tokenach rozdzielane przecinkami
        2. szukam pliku beamlets
        3. szukam plików fluence maps (sortuję na końcu, aby odnajdywać dobrze folder z ewentualnym cache)
        4. buduję lokalizację folderu cache
    """
    forceRecalculate = False

    args = merge_http_request_arguments()
    if "forceRecalculate" in args:
        forceRecalculate = args["forceRecalculate"].lower() == "true"
    
    # dopisać sprawdzanie czy podano poprawny argument ftokens

    mlist = filter(lambda v: len(v) > 0, ftokens.split(","))
    stored_files = [storage.find_file_by_token(token) for token in mlist]

    # dopisać sprawdzanie czy udało się znaleźć wszystkie pliki

    res = None # to będzie odpowiedź dla użytkownika
    data = None
    message = None

    beamlets = None
    fluences = []
    # find beamlets
    for f in stored_files:
        if f.type == 'beamlets':
            print("Znalazłem beamlety")
            beamlets = f
        if f.type == 'pareto':
            print("Znalazłem plik z mapami fluencji")
            fluences.append(f)
    fluences = sorted(fluences, key=lambda f: f.token)

    if beamlets != None:
        # Generuję nazwę folderu cache na podstawie plików i ich czasów załączenia do systemu
        processing_folder = generate_dirname(beamlets, fluences)                        

        print(f"Checking processing folder: {processing_folder}")
        if not os.path.isdir(processing_folder) or forceRecalculate:
            if os.path.isdir(processing_folder):
                logger.debug(f"Removing processing folder: {processing_folder}")
                import shutil
                shutil.rmtree(processing_folder)

        
            logger.debug(f"Creating new processing folder: {processing_folder}")
            os.mkdir(processing_folder)

            pars_fname = processing_folder + "/params-input.json"
            logger.debug(f"Creating parameters file: {pars_fname}")
            with open(pars_fname, "w") as fout:
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

            #######################################################################
            logger.debug("Scheduling a job with calculations...")
            task_id = redis_worker.start_calculate_histogram_job(processing_folder)
            #######################################################################

        else:            
            logger.info(f"Found processing folder - will return cached data: {processing_folder}")

            #######################################################################
            logger.debug("Scheduling a job which will return cached data...")
            task_id = redis_worker.start_cached_histogram_job(processing_folder)
            #######################################################################

        data = {"task_id":  task_id}
        res = "success"
    else:
        message = f"Unable to locate file with dose deposition data (Dane do optymalizacji PW) for file tokens: {ftokens}"
        res = "failure"

    res = { "result": res }
    if message:
        res["message"] = message
    if data:
        res["data"] = data

    # return jsonify(res)
    return redirect(f"/dash_histograms?task_id={data['task_id']}")

    
def generate_dirname(beamlets, fluences):
    stamp = beamlets.stored_at.strftime('%Y%m%d_%H%M%S')
    dirname = f'/{stamp}_{beamlets.uid}';
    for fl in fluences:
        stamp = fl.stored_at.strftime('%Y%m%d_%H%M%S')
        dirname += f'_{stamp}_{fl.uid}';
    return f'{app.config["PROCESSING_FOLDER"]}{dirname}'



