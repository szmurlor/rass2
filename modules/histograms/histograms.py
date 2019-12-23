# -*- encoding: utf-8
import os

from flask import g, abort, render_template, flash, redirect, session, jsonify
import database
from rass_app import app
import storage
import json
import modules.histograms.worker as hworker

import redis
from rq import Queue, Connection
import urllib.parse


@app.route('/histogram/<ftokens>')
def histogram(ftokens):
    """Opis działania:
        1. pobieram wszystkie pliki z bazy danych podane po tokenach rozdielane przecinkami
        2. szukam pliku beamlets
        3. szukam plików fluence maps 9sortuję nakońcu specjalnie, aby odnajdywac dobrze folder)
        4. buduję lokalizację folderu cache
    """

    if not g.user_id:
        abort(401)
    mlist = filter(lambda v: len(v) > 0, ftokens.split(","))
    stored_files = [storage.find_file_by_token(token) for token in mlist]
    res = None
    data = None
    message = None

    beamlets = None
    fluences = []
    # find beamlets
    for f in stored_files:
        print(f.type)
        if f.type == 'beamlets':
            beamlets = f
        if f.type == 'pareto':
            fluences.append(f)
    fluences = sorted(fluences, key=lambda f: f.token)

    if beamlets != None:
        data = {}
        res = "success"
        processing_foder = generate_dirname(beamlets, fluences)
        if not os.path.isdir(processing_foder):
            data["cached"] = False
            os.mkdir(processing_foder)

            with open(processing_foder + "/params-input.json", "w") as fout:
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

        task_id = hworker.calculate_histogram(processing_foder)
        data["task_id"] = task_id
    else:
        res = "failure"
        message = f"Unable to locate file with dose deposition data for file tokens: {ftokens}"


    res = { "result": res }
    if message:
        res["message"] = message
    if data:
        res["data"] = data

    return jsonify(res)

    
def generate_dirname(beamlets, fluences):
    stamp = beamlets.stored_at.strftime('%Y%m%d_%H%M%S')
    dirname = f'/{stamp}_{beamlets.uid}';
    for fl in fluences:
        stamp = fl.stored_at.strftime('%Y%m%d_%H%M%S')
        dirname += f'_{stamp}_{fl.uid}';
    return f'{app.config["PROCESSING_FOLDER"]}{dirname}'



