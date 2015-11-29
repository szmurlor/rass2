import os.path
from database import db, StoredFile
from rass_app import app

class TemporaryStoredFile(StoredFile):
	raw_bytes = None

	def __init__(self, raw_bytes, file_name, file_directory, content_type):
		self.raw_bytes = raw_bytes

		file_path = os.path.join(file_directory, file_name)

		StoredFile.__init__(self, file_path, content_type)

	def read(self):
		return self.raw_bytes

	def __repr__(self):
		return '<TemporaryStoredFile %s supposed to be written in %r (%s)>' % (self.name, self.path, self.content_type)

def find_file_by_uid(uid):
	try:
		stored_file = StoredFile.query.filter_by(uid=uid).one()
		return stored_file
	except Exception, e:
		app.logger.debug("0 or more than one file with uid = %s" % uid)
		return None

def find_files_by_type(content_type):
	try:
		matched_files = StoredFile.query.filter_by(content_type=content_type).all()
		return matched_files
	except Exception, e:
		app.logger.debug("Could not find files with 'content_type': %r" % content_type)
		return []

def new_file(raw_bytes, file_name, file_directory, content_type=None):
	stored_file = TemporaryStoredFile(raw_bytes, file_name, file_directory, content_type)
	return stored_file

def store_file(temporary_stored_file):
	try:
		with open(temporary_stored_file.path, 'wb') as f:
			f.write(temporary_stored_file.read())
    		db.session.add(temporary_stored_file)
		db.session.commit()
		stored_file = find_file_by_uid(temporary_stored_file.uid)
		return stored_file
	except IOError, e:
		app.logger.exception("Could not write %s" % temporary_stored_file)
		return None
	except Exception, e:
		app.logger.exception("Could not save %s in database" % temporary_stored_file)
		return None
