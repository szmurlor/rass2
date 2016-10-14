# -*- encoding: utf-8
import dateutil

from flask import g, session, request, flash
from flask import render_template, redirect, url_for
from datetime import datetime
from rass_app import app
import logger
import database
import dateutil.parser

##################################
# Global variables
##################################
scenarios = None


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


@app.errorhandler(401)
def unauthorized(error):
	logger.debug("Unauthorized access to %s" % request.url)
	return redirect(url_for('login') + '?redirect_url=' + request.url)


@app.errorhandler(500)
@app.route('/error/<error>')
def internal_error(error):
	error_description = session.pop('error_description','')
	error_message = session.pop('error_message','UNKNOWN')
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
		except Exception, e:
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


@app.template_filter('datetime')
def _jinja2_filter_datetime(date, fmt=None):
	format='%d.%m.%Y %H:%M:%S'
	return date.strftime(format)


@app.template_filter('date')
def _jinja2_filter_datetime(date, fmt=None):
	format='%d.%m.%Y'
	return date.strftime(format)


if __name__ == '__main__':
	app.run(host='0.0.0.0')

