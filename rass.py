# -*- encoding: utf-8
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

def reload_scenarios():
	import pkgutil
	import modules
	global scenarios

	scenarios = {} # clear all previous scenarios
	for importer, module_name, is_package in pkgutil.iter_modules(modules.__path__):
		logger.debug("Found scenario %s (is a package: %s)" % (module_name, is_package))
		try:
			scenario_class = getattr(__import__('modules.%s' % module_name), module_name)
			scenario =  {
				'href' : module_name,
				'class' : scenario_class,
				'name' : getattr(scenario_class, '__scenario__', 'Scenariusz %s' % module_name)
			}
	
			scenarios[module_name] = scenario
		except Exception, e:
			logger.exception("Problem while importing modules.%s: %s" % (module_name, e))

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
			args[key] = storage.new_file(content, file_name, g.user.home, content_type)

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
	g.user = None
	user_id = session.get('user_id')
	if user_id:
		try:
			g.user = database.User.query.filter_by(id=user_id).one()
		except:
			logger.debug('Could not find the user with id=%s' % user_id)

@app.route('/')
def index():
	return render_template('index.html', scenarios=scenarios)

@app.route('/fs/<uid>')
def download(uid):
        if not g.user:
                abort(401)

	stored_file = storage.find_file_by_uid(uid)
	if stored_file is None:
		return render_template("no_file.html", uid=uid), 404

	content = stored_file.read(charset=None)
	return content, 200, { 'Content-Type': stored_file.content_type }

@app.route('/<scenario_name>/')
def start(scenario_name):
	return process(scenario_name, 'start')

@app.route('/<scenario_name>/<step_name>', methods=['GET', 'POST'])
def process(scenario_name, step_name):
        if not g.user:
                abort(401)

	if scenario_name not in scenarios:
		return render_template("no_scenario.html", scenario_name = scenario_name, scenarios = scenarios)

	user_data = UserSession(g.user)

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

	return render_template(scenario_name + '.html', context=user_data, **user_data)

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

reload_scenarios()

if __name__ == '__main__':
	app.run(host='0.0.0.0')

