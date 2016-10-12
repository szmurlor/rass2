from logging import StreamHandler, Formatter, DEBUG, INFO, WARNING, ERROR
from logging.handlers import RotatingFileHandler
from rass_app import app

formatter = Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
streamhandler = StreamHandler()
streamhandler.setFormatter(formatter)
filehandler = RotatingFileHandler('log/production.log')
filehandler.setFormatter(formatter)
#app.logger.addHandler(streamhandler)
#app.logger.addHandler(filehandler)
app.logger.setLevel(INFO)

debug = app.logger.debug
info = app.logger.info
warn = app.logger.warning
error = app.logger.error
exception = app.logger.exception
