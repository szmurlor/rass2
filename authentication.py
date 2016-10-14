# -*- encoding: utf-8
from flask import g, session, request, flash
from flask import render_template, redirect, url_for
from rass_app import app
import database


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

		if dbuser is not None:  # check password
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