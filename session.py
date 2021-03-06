import collections
import _pickle as pickle
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from database import db, UserSessionData, User
from rass_app import app
from flask import g
import logger

def get(key, default=None, user=None):
	if user is None:
		user = getuser(g.user_id)
	if key not in UserSession(user):
		UserSession(user)[key] = default
	return UserSession(user)[key]

def setdefault(key, value, user=None):
	if user is None:
		user = getuser(g.user_id)
	UserSession(user)[key] = value

def getuser(user_id):
	return User.query.filter_by(id=user_id).one()

class UserSession(collections.MutableMapping):
	def __init__(self, user=None):
		if user is None:
			user = getuser(g.user_id)
		self.user_id = user.id
		self.store = dict()
		for key, in self.list_all_keys_in_database():
			self.store[self.__keytransform__(key)] = self.fetch_from_database(key)

	def list_all_keys_in_database(self):
		keys = UserSessionData.query.with_entities(UserSessionData.key).all()
		return keys

	def fetch_from_database(self, key, default=None):
		try:
			user_session_data = UserSessionData.query.filter_by(key=key, user_id=self.user_id).one()
			value = pickle.loads(user_session_data.value)
			return value
		except NoResultFound as e:
			return default
		
	def store_in_database(self, key, value):
		try:
			user_session_data = UserSessionData.query.filter_by(key=key, user_id=self.user_id).first()
			if user_session_data is None:
				user_session_data = UserSessionData(key, '', self.user_id)

			user_session_data.value = pickle.dumps(value)
			db.session.add(user_session_data)
			db.session.commit()
		except Exception as e:
			logger.exception("Error while saving %r -> %r" % (key, value))

	def delete_from_database(self, key):
		try:
			user_session_data = UserSessionData.query.filter_by(key=key, user_id=self.user_id).one()
			db.session.delete(user_session_data)
			db.session.commit()
		except NoResultFound as e:
			logger.exception("Error while removing %r" % (key))

	def __getitem__(self, key):
		value = self.fetch_from_database(key)
		if value is not None:
			self.store[self.__keytransform__(key)] = value
		return self.store[self.__keytransform__(key)]

	def __setitem__(self, key, value):
		self.store_in_database(key, value)
		self.store[self.__keytransform__(key)] = value

	def __delitem__(self, key):
		self.delete_from_database(key)
		del self.store[self.__keytransform__(key)]

	def __iter__(self):
		return iter(self.store)

	def __len__(self):
		return len(self.store)

	def __keytransform__(self, key):
		return key
