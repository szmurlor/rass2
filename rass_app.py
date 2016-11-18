# -*- coding: utf-8
from flask import Flask

UPLOAD_FOLDER = "/opt/rass2/data/"

LONG_NOTES = u"""...
"""

app = Flask('rass', template_folder='modules')
app.secret_key = '\x81~\x88\r\xc95\xe3\xf9\xeb\xa8\x08h\xc2-\x063\x92\x93\x8ev\x9d\xcf\x14|'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/rass.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

import logging

FORMAT = '%(asctime)-15s- %(message)s'
#logging.basicConfig(format=FORMAT, filename='log/production.log', level=logging.DEBUG)
logging.basicConfig(format=FORMAT, level=logging.DEBUG)

