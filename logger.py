import os
import logging
from logging import StreamHandler, Formatter, DEBUG, INFO, WARNING, ERROR
from logging.handlers import RotatingFileHandler
from rass_app import app

wlog = logging.getLogger('werkzeug')
wlog.setLevel(logging.INFO)

if "RASS_DEV_LOGGER" in os.environ:
    wlog.setLevel(logging.ERROR)
    print(f"Using RASS_DEV_LOGGER handler: {os.environ['RASS_DEV_LOGGER']}")
    formatter = Formatter(os.environ["RASS_DEV_LOGGER"])
else:    
    formatter = Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
streamhandler = StreamHandler()
streamhandler.setFormatter(formatter)
#filehandler = RotatingFileHandler('log/production.log')
#filehandler.setFormatter(formatter)


#from flask.logging import default_handler
#app.logger.removeHandler(default_handler)
app.logger.addHandler(streamhandler)
app.logger.setLevel(DEBUG)

debug = app.logger.debug
info = app.logger.info
warn = app.logger.warning
error = app.logger.error
exception = app.logger.exception
