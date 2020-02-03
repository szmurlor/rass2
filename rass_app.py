# -*- coding: utf-8
from flask import Flask, g, request
from flask_babel import Babel
import os
import json
import logging

app = Flask('rass', template_folder='modules')

############################################################
# Wczytywanie konfiguracji
############################################################

app_config = {}
if (os.path.isfile('rass_config.json')):
    with open('rass_config.json') as fin:
        app_config.update(json.load(fin))
else:
    if (os.path.isfile('rass_config_dev.json')):
        with open('rass_config_dev.json') as fin:
            app_config.update(json.load(fin))            

    
def get_option(option, default):    
    if option in app.config:
        return app.config[option]

    if option in os.environ:
        return os.environ[option]

    if option in app_config:
        return app_config[option]

    return default


UPLOAD_FOLDER = get_option("RASS_DATAFOLDER", "/opt/rass2/data/")
PROCESSING_FOLDER = get_option("RASS_PROCESSINGFOLDER", "/opt/rass2/processing/")
LONG_NOTES = u"""...
"""
REDIS_URL = get_option("REDIS_URL", "redis://localhost:6379/0")
REDIS_WORKER_NAME = get_option("REDIS_WORKER_NAME", "rass2-worker")
SQLALCHEMY_DATABASE_URI = get_option("SQLALCHEMY_DATABASE_URI", 'sqlite:///data/rass.db')

print("Starting with App processing folder: %s" % PROCESSING_FOLDER)
print("Starting with Files upload folder: %s" % UPLOAD_FOLDER)

app.secret_key = '\x81~\x88\r\xc95\xe3\xf9\xeb\xa8\x08h\xc2-\x063\x92\x93\x8ev\x9d\xcf\x14|'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSING_FOLDER'] = PROCESSING_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['REDIS_URL'] = REDIS_URL
app.config['REDIS_WORKER'] = REDIS_WORKER_NAME


############################################################
# Zainstalowanie wsparcia dla trybu wielojęzykowego
############################################################

babel = Babel(app)


############################################################
# Konfiguracja bilbioteki do logowania komunikatów
############################################################

FORMAT = '%(asctime)-15s- %(message)s'
#logging.basicConfig(format=FORMAT, filename='log/production.log', level=logging.DEBUG)
logging.basicConfig(format=FORMAT, level=logging.DEBUG)



def set_upload_folder(folder):
    """ Tutaj możemy przesłonić ustawiony katalogów do zapisywania danych. """
    print("Setting data folder to: %s" % folder)
    app.config['UPLOAD_FOLDER'] = folder


def set_processing_folder(folder):
    print("Setting processing folder to: %s" % folder)
    app.config['PROCESSING_FOLDER'] = folder
