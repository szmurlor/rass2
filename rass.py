# -*- encoding: utf-8
from flask import g, session, request, flash
from flask import render_template, redirect, url_for
from datetime import datetime

from flask import send_from_directory

from rass_app import app, set_upload_folder
import logger
import database


try:
    for f in database.StoredFile.query.filter_by(token=None):
        pass
except:
    database.get_engine().execute('ALTER TABLE stored_file ADD COLUMN meta VARCHAR(4096)')



##################################
# Global variables
##################################
scenarios = None

import sys
#reload(sys)
#sys.setdefaultencoding('utf8')

def init_scenarios():
    import modules.scenarios.roi.roi
    import modules.scenarios.pareto.pareto
    global scenarios
    scenarios = {
        'roi': create_scenario('roi', modules.scenarios.roi.roi),
        'pareto': create_scenario('pareto', modules.scenarios.pareto.pareto)
    }


def create_scenario(module_name, scenario_class):
    return {
        'href': module_name,
        'class': scenario_class,
        'name': getattr(scenario_class, '__scenario__', 'Scenariusz %s' % module_name)
    }


init_scenarios()


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
    g.scenarios = None
    user_id = session.get('user_id')
    if user_id:
        try:
            user = database.User.query.filter_by(id=user_id).one()
            g.user_id = user_id
            g.user_home = user.home
            g.scenarios = scenarios
        # logger.debug("Authorized to %s" % g.user_id)
        except Exception as e:
            logger.debug('Could not find the user with id=%s' % user_id)
            logger.debug('Cause: %s' % e)


@app.route('/')
def index():
    return render_template('index.html', scenarios=scenarios)


# noinspection PyUnresolvedReferences
import authentication
# noinspection PyUnresolvedReferences
import modules.datastore.datastore
# noinspection PyUnresolvedReferences
import modules.scenarios.scenarios
# noinspection PyUnresolvedReferences
import modules.help.help


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

if __name__ == '__main__':
    import sys, getopt

    try:
        opts, args = getopt.getopt(sys.argv[1:], "d:",["datafolder="])
    except getopt.GetoptError:
        print('rass.py -datafolder <absolute path to file storage location>')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-d", "--datafolder"):
            set_upload_folder(arg)            

    app.run(host='0.0.0.0')
