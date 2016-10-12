# -*- encoding: utf-8
import os
from flask import Flask
from flask import g, session, request, flash, abort
from flask import render_template, redirect, url_for
from datetime import datetime

scenarios = None

from rass_app import app

import logger
import database
import storage
import debug

from session import UserSession
from filesystem_helper import convert_to_unicode

def init_scenarios():
	import pkgutil
	import modules
	import modules.scenarios.roi.roi
	global scenarios
	scenarios = {}
	scenarios['roi'] = create_scenario('roi', modules.scenarios.roi.roi)

def create_scenario(module_name, scenario_class):
	return {
		'href' : module_name,
		'class' : scenario_class,
		'name' : getattr(scenario_class, '__scenario__', 'Scenariusz %s' % module_name)
	}

def merge_http_request_arguments():
	logger.debug("Merging following HTTP data:"
		"\n- QueryString: %s" % request.args +
		"\n- Form: %s" % request.form +
		"\n- Files: %s" % request.files)
	
	args = {}
	for key, value in request.args.iteritems():
		args[key] = value

	for key, value in request.form.iteritems():
		args[key] = value # it is OK to overwrite QueryString parameters

	for key, value in request.files.iteritems():
		content = convert_to_unicode(value.read())
		file_name = value.filename
		content_type = value.content_type
		content_length = len(content)

		if key not in args or content_length > 0:
			# it is OK to overwrite Form parameters if we have sent a file
			args[key] = storage.new_file_from_raw_bytes(content, file_name, content_type)

		if key in args and content_length is 0:
			uid = args[key]
			stored_file = storage.find_file_by_uid(uid)
			if stored_file is not None:
				args[key] = stored_file
				logger.debug("Uploaded file has no content, so we fetched the file using selected 'uid'\n" +
				"Name: %s, uid: %s, stored_file: %s" % (key, uid, stored_file))
			else:
				# args[key] has the old value (maybe a not existing uid)
				logger.debug("Uploaded file has no content, the file selected using 'uid' doesn't exist.\n" +
				"Name: %s, uid: %s, args[%s]: %s" % (key, uid, key, args[key]))
	return args

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
	return render_template('error.html', error=error,error_description=error_description,
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
		except Exception, e:
			logger.debug('Could not find the user with id=%s' % user_id)
			logger.debug('Cause: %s' % e)

@app.route('/')
def index():
	return render_template('index.html', scenarios=scenarios)

@app.route('/data/')
def datastore():
	if not g.user_id:
		abort(401)
	return render_template('datastore/datastore.html', scenarios=scenarios, uid=None)

@app.route('/data/<uid>')
def dataset(uid):
	if not g.user_id:
		abort(401)
	return render_template('datastore/dataset.html', scenarios=scenarios, uid=uid)

@app.route('/fs/<uid>')
def download(uid):
        if not g.user_id:
                abort(401)

	stored_file = storage.find_file_by_uid(uid)
	if stored_file is None:
		return render_template("no_file.html", uid=uid), 404

	file_name = os.path.basename(stored_file.path)
	content = stored_file.read(charset=None)
	return content, 200, {
		'Content-Type': stored_file.content_type,
		'Content-Disposition': "attachment; filename=" + file_name
	}

@app.route('/<scenario_name>/')
def start(scenario_name):
	return process(scenario_name, 'start')

@app.route('/<scenario_name>/<step_name>', methods=['GET', 'POST'])
def process(scenario_name, step_name):
        if not g.user_id:
                abort(401)

	if scenario_name not in scenarios:
		return render_template("no_scenario.html", scenario_name = scenario_name, scenarios = scenarios)

	user_data = UserSession()

	scenario_class = scenarios[scenario_name]['class']
	step_function = getattr(scenario_class, step_name, None)
	if step_function is None:
		logger.exception('Module %s has no %r function' % (scenario_class, step_name))
		session['error_message'] = "NO STEP FUNCTION '%s'" % step_name
		session['error_date'] = datetime.utcnow()
		session['error_description'] = u"""Bład przetwarzania scenariusza {scenario_name}.
W trakcie przetwarzania kroku '{step_name}' napotkano błąd.
""".format(scenario_name=scenario_name, step_name=step_name)
		#abort(500)
		return redirect('/error/500')

	args = merge_http_request_arguments()
	step_data = step_function(**args)
	user_data.update(step_data)

	return render_template('scenarios/' + scenario_name + '/' + scenario_name + '.html', user_data=user_data, **user_data)

@app.route('/login/', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		username = request.form.get('username', None)
		password = request.form.get('password', None)
		redirect_url = request.form.get('redirect_url', '')

		if redirect_url is '':
			redirect_url = url_for('index')

		user = database.User(username=username)
		
		try:
			dbuser = database.User.query.filter_by(username=user.username).one()
		except:
			dbuser = None

		if dbuser is not None: # check password
			user.set_password(password, dbuser.salt)

		if dbuser is None or user.password != dbuser.password:
			flash(u'Niepoprawna nazwa użytkownika lub hasło', 'error')
		else:
			session['user_id'] = dbuser.id
			flash(u'Zalogowano użytkownika', 'success')
			return redirect(redirect_url)

	redirect_url = request.args.get('redirect_url', '')
	return render_template('login.html', redirect_url=redirect_url)

@app.route('/logout/')
def logout():
	session.pop('user_id', None)
	flash(u'Wylogowano użytkownika', 'info')
	return render_template('login.html')

init_scenarios()

if __name__ == '__main__':
	app.run(host='0.0.0.0')

