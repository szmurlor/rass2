# -*- coding: utf-8
import os.path
import content_type_helper
import filesystem_helper
from hashlib import sha512
from random import choice
from string import ascii_lowercase, digits
from datetime import datetime
from flask.ext.sqlalchemy import SQLAlchemy
from rass_app import app

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/rass.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(80), unique=True)
	password = db.Column(db.String(128))
	salt = db.Column(db.String(5))
	home = db.Column(db.String(64), unique=True)

	def __init__(self, username, root='/tmp'):
		self.username = username
		self.home = '%s/%s' % (root, username)

	def set_password(self, password, salt=None):
		if salt is None:
			salt = ''.join(choice(ascii_lowercase + digits) for x in range(10))
		self.password = sha512(salt + password).hexdigest()
		self.salt = salt

	def __repr__(self):
		return '<User %r>' % self.username

class UserSessionData(db.Model):
	uid = db.Column(db.Integer, primary_key=True)
	user_id = db.Column(db.Integer)
	key = db.Column(db.String(32))
	value = db.Column(db.Binary())

	def __init__(self, key, value, user_id):
		self.user_id = user_id
		self.key = key
		self.value = value

class StoredFile(db.Model):
	uid = db.Column(db.Integer, primary_key=True)
	path = db.Column(db.String(512))
	name = db.Column(db.String(128))
	content_type = db.Column(db.String(32))
	stored_at = db.Column(db.DateTime(), default=datetime.utcnow)

	def __init__(self, file_path, content_type=None):
                directory, name = os.path.split(file_path)

		if len(name) > 0:
			name, extension = os.path.splitext(name)
			self.name = name
			self.path = os.path.join(directory, name + extension)

			if content_type is None:
				content_type = content_type_helper.get_content_type_by_extension(extension)
				if content_type is None:
					content_type = 'application/octet-stream'
			self.content_type = content_type
		else: # path is a directory (ends with '/')
			self.name = os.path.join(os.path.basename(directory), '')
			self.path = directory
			self.content_type = 'inode/directory'

	def read(self, charset='latin2'):
		with open(self.path, 'rb') as f:
			raw_bytes = f.read()
			if charset:
				return raw_bytes.decode(charset)
			return raw_bytes

	def __repr__(self):
		return '<StoredFile (uid: %s, name:"%s", path:"%s") %s>' % (self.uid, self.name, self.path, self.content_type)

	def __str__(self):
		return self.path

class TemporaryStoredFile(StoredFile):
	content = str()

	def __init__(self, content, file_name, content_type):
		self.content = content

		StoredFile.__init__(self, file_name, content_type)

	def read(self):
		return self.content

	def write(self, directory, charset='latin2'):
		self.path = os.path.join(directory, self.path)
		filesystem_helper.mkdir_directories_for(self.path)
		with open(self.path, 'wb') as f:
			content = self.read()
			if charset:
				content = content.encode(charset)
			f.write(content)

	def __repr__(self):
		return '<TemporaryStoredFile %s supposed to be written in %r (%s)>' % (self.name, self.path, self.content_type)

