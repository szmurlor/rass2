# -*- encoding: utf-8
from flask import g, session, request, flash, send_from_directory, render_template, redirect, url_for
from datetime import datetime
from rass_app import app, set_upload_folder
import logger
import database
from flask_babel import gettext, refresh, Babel

import authentication
import modules.datastore.datastore
import modules.help.help
import modules.histograms.histograms

try:
    for f in database.StoredFile.query.filter_by(token=None):
        pass
except:
    database.get_engine().execute('ALTER TABLE stored_file ADD COLUMN meta VARCHAR(4096)')

try:
    for dstype in database.DatasetType.query.all():
        if dstype.name == "CT / ROI Structures / RT Plan / Pareto results":
            file_types = dstype.get_file_types()            
            for t in file_types["types"]:
                if t["name"] in ['rt', 'beamlets', 'optdesc', 'pareto' , 'fluences', 'other']:
                    import json
                    t["CAN_ARCHIVE"] = True
                    sftypes = json.dumps(file_types, indent=True)
                    dstype.file_types = sftypes
                    database.db.session.add(dstype)
                    database.db.session.commit()

except:
    raise Error(gettext("Nie mogę zaktualizować struktury bazy danych!"))


##################################
# Global variables
##################################
import sys

@app.route('/doc/<path:path>')
def send_js(path):
    return send_from_directory('doc', path)

@app.errorhandler(401)
def unauthorized(error):
    logger.debug("Unauthorized access to %s" % request.url)
    return redirect(url_for('login') + '?redirect_url=' + request.url)


@app.errorhandler(500)
@app.route('/error/<error>')
def internal_error(error):
    error_description = session.pop('error_description', '')
    error_message = session.pop('error_message', 'UNKNOWN')
    error_date = session.pop('error_date', datetime.utcnow())
    return render_template('error.html', error=error, error_description=error_description,
                           error_message=error_message, error_date=error_date)


@app.before_request
def before_request():
    g.user_id = None
    g.user_home = None
    user_id = session.get('user_id')
    if user_id:
        try:
            user = database.User.query.filter_by(id=user_id).one()
            g.user_id = user_id
            g.user_home = user.home
        # logger.debug("Authorized to %s" % g.user_id)
        except Exception as e:
            logger.debug('Could not find the user with id=%s' % user_id)
            logger.debug('Cause: %s' % e)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/lang/<lang>')
def set_language(lang):
    session['lang'] = lang
    refresh() # odświeżam cache językowy, bo mogłem zmienić język?
    return index()


@app.template_filter('datetime')
def _jinja2_filter_datetime(date, fmt=None):
    dformat = '%d.%m.%Y %H:%M:%S'
    return date.strftime(dformat)


@app.template_filter('date')
def _jinja2_filter_date(date, fmt=None):
    dformat = '%d.%m.%Y'
    return date.strftime(dformat)


@app.template_filter('markdown')
def markdown_filter(data):
    from flask import Markup
    from markdown import markdown
    return Markup(markdown(data, extensions=['markdown.extensions.attr_list']))


############################################################
# Zainstalowanie wsparcia dla trybu wielojęzykowego
############################################################
babel = Babel(app)

@babel.localeselector
def get_locale():
    if "lang" in session:
        return session.get('lang')
    return 'pl'

app.jinja_env.globals['get_locale'] = get_locale



###########################################################
# INIT DASH
###########################################################
from rass_dash.dash_histograms import init_dash
init_dash(app)


if __name__ == '__main__':
    import sys, getopt

    try:
        opts, args = getopt.getopt(sys.argv[1:], "d:p:",["datafolder=","processing="])
    except getopt.GetoptError:
        print('rass.py -datafolder <absolute path to file storage location>')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-d", "--datafolder"):
            set_upload_folder(arg)
        if opt in ("-p", "--processing"):
            set_processing_folder(arg)

    app.run(host='0.0.0.0')

    gettext("Dane CT")
    gettext("Dane o strukturach ROI")
    gettext("Plany radioterapii")
    gettext("Inne")
    gettext("Wszyscy")
    gettext("Dane do optymalizacji")
    gettext("Opis optymalizacji")
    gettext("Wyniki pareto")
    gettext("Mapy fluencji po optymalizacji")
    gettext("PW")
    gettext("COI")
    gettext("PAN")
