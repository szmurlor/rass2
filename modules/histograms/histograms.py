# -*- encoding: utf-8
import os

from flask import g, abort, render_template, flash, redirect, session, jsonify
import database
from rass_app import app
import storage
import json
import rass_redis.worker as hworker

import redis
from rq import Queue, Connection
import urllib.parse


@app.route('/histogram/<ftokens>')
def histogram(ftokens):
    """Opis działania:
        1. pobieram wszystkie pliki z bazy danych podane po tokenach rozdzielane przecinkami
        2. szukam pliku beamlets
        3. szukam plików fluence maps (sortuję na końcu, aby odnajdywać dobrze folder z ewentualnym cache)
        4. buduję lokalizację folderu cache
    """

    if not g.user_id:
        abort(401)

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
        #** Zlecam uruchomienie zadania, ponieważ nie ma go w cache
        processing_foder = generate_dirname(beamlets, fluences)
        
        data = {}
        res = "success"
        task_id = hworker.calculate_histogram(processing_foder)
        data["task_id"] = task_id

    else:
        res = "failure"
        message = f"Unable to locate file with dose deposition data (Dane do optymalizacji PW) for file tokens: {ftokens}"


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



