# -*- encoding: utf-8
from flask import g, session, abort, render_template, redirect
from datetime import datetime
from rass_app import app
import logger
from session import UserSession
from utils import merge_http_request_arguments


@app.route('/<scenario_name>/')
def start(scenario_name):
	return process(scenario_name, 'start')


@app.route('/<scenario_name>/<step_name>', methods=['GET', 'POST'])
def process(scenario_name, step_name):
	if not g.user_id:
		abort(401)

	if scenario_name not in g.scenarios:
		return render_template("scenarios/no_scenario.html", scenario_name=scenario_name, scenarios=g.scenarios)

	user_data = UserSession()

	scenario_class = g.scenarios[scenario_name]['class']
	step_function = getattr(scenario_class, step_name, None)
	if step_function is None:
		logger.exception('Module %s has no %r function' % (scenario_class, step_name))
		session['error_message'] = "NO STEP FUNCTION '%s'" % step_name
		session['error_date'] = datetime.utcnow()
		session['error_description'] = u"""Bład przetwarzania scenariusza {scenario_name}.
W trakcie przetwarzania kroku '{step_name}' napotkano błąd.
""".format(scenario_name=scenario_name, step_name=step_name)
		return redirect('/error/500')

	args = merge_http_request_arguments()
	step_data = step_function(**args)
	user_data.update(step_data)

	return render_template('scenarios/' + scenario_name + '/' + scenario_name + '.html', user_data=user_data, **user_data)