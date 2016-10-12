from logger import DEBUG
from werkzeug.debug import DebuggedApplication
from rass_app import app

app.debug = True
app.wsgi_app = DebuggedApplication(app.wsgi_app, True)
app.logger.setLevel(DEBUG)
