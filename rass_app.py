# -*- coding: utf-8
from flask import Flask

app = Flask('rass', template_folder='modules')
app.secret_key = '\x81~\x88\r\xc95\xe3\xf9\xeb\xa8\x08h\xc2-\x063\x92\x93\x8ev\x9d\xcf\x14|'

import logging

FORMAT = '%(asctime)-15s- %(message)s'
#logging.basicConfig(format=FORMAT, filename='log/production.log', level=logging.DEBUG)
logging.basicConfig(format=FORMAT, level=logging.DEBUG)

LONG_NOTES = u"""#### 1. Krótki opis przypadku COI

1. ...

#### 2. Uwagi PAN

1. ...

#### 3. Komentarz COI

1. ...
"""