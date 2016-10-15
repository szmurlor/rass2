# -*- coding: utf-8
import json
import os.path

from sqlalchemy.orm import relationship
from sqlalchemy.sql.sqltypes import DateTime

import content_type_helper
import filesystem_helper
from hashlib import sha512
from random import choice
from string import ascii_lowercase, digits
from datetime import datetime
from flask.ext.sqlalchemy import SQLAlchemy
from rass_app import app

db = SQLAlchemy(app)
db.session.expire_on_commit = False


class User(db.Model):
	__tablename__ = 'user'
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


class Dataset(db.Model):
	__tablename__ = 'dataset'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(128))

	date_created = db.Column(db.DateTime())
	user_created_id = db.Column(db.Integer, db.ForeignKey("user.id"))
	user_created = relationship("User", back_populates="datasets_created", foreign_keys=[user_created_id])

	date_modified = db.Column(db.DateTime())
	user_modified_id = db.Column(db.Integer, db.ForeignKey("user.id"))
	user_modified = relationship("User", back_populates="datasets_modified", foreign_keys=[user_modified_id])

	type_id = db.Column(db.Integer, db.ForeignKey("dataset_type.id"))
	type = relationship("DatasetType", back_populates="datasets", foreign_keys=[type_id])

	short_notes = db.Column(db.String(255))
	long_notes = db.Column(db.String(8192))

	def __init__(self, name, user_created):
		self.user_created = user_created
		self.name = name
		self.date_created = datetime.utcnow()
		self.date_modified = self.date_created
		self.user_modified = user_created

	def files_by_type(self, file_type_name):
		result = []

		for f in self.files:
			if f.type.lower() == file_type_name.lower():
				result.append(f)

		return result


User.datasets_modified = relationship("Dataset", order_by=Dataset.id, back_populates="user_modified", foreign_keys=[Dataset.user_modified_id])
User.datasets_created = relationship("Dataset", order_by=Dataset.id, back_populates="user_created", foreign_keys=[Dataset.user_created_id])


class DatasetType(db.Model):
	__tablename__ = 'dataset_type'
	id = db.Column(db.Integer, primary_key=True)

	name = db.Column(db.String(128))
	file_types = db.Column(db.String(8192))

	def __init__(self, name):
		self.name = name

	def file_types_list(self):
		config = json.loads(self.file_types)
		return config['types']

DatasetType.datasets = relationship("Dataset", order_by=Dataset.id, back_populates="type", foreign_keys=[Dataset.type_id])


class StoredFile(db.Model):
	uid = db.Column(db.Integer, primary_key=True)
	path = db.Column(db.String(512))
	name = db.Column(db.String(128))
	description = db.Column(db.String(512))
	content_type = db.Column(db.String(32))
	type = db.Column(db.String(128))

	stored_at = db.Column(db.DateTime(), default=datetime.utcnow)
	stored_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
	stored_by = relationship("User", foreign_keys=[stored_by_id])

	dataset_id = db.Column(db.Integer, db.ForeignKey("dataset.id"))
	dataset = relationship("Dataset", back_populates="files")

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

Dataset.files = relationship("StoredFile", order_by=StoredFile.uid, back_populates="dataset")

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

