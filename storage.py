import os.path
import filesystem_helper
from database import db, StoredFile, TemporaryStoredFile
from rass_app import app

def new_file_from_raw_bytes(raw_bytes, file_name, content_type=None):
	print 'NFRB %r' % file_name
	stored_file = TemporaryStoredFile(raw_bytes, file_name, content_type)
	return stored_file

def new_file_from_filesystem(file_path, content_type=None):
	print 'NFFF %r' % file_path
	stored_file = StoredFile(file_path, content_type)
	try:
		db.session.add(stored_file)
		db.session.commit()
		return stored_file
	except Exception, e:
		app.logger.debug("Could not save %r" % file_path)
		return None

def find_file_by_uid(uid):
	try:
		stored_file = StoredFile.query.filter_by(uid=uid).one()
		db.session.expunge_all()
		db.session.close()
		return stored_file
	except Exception, e:
		app.logger.debug("0 or more than one file with uid = %s" % uid)
		return None

def find_files_by_type(content_type):
	try:
		matched_files = StoredFile.query.filter_by(content_type=content_type).order_by(StoredFile.stored_at.desc()).all()
		db.session.expunge_all()
		db.session.close()
		return matched_files
	except Exception, e:
		app.logger.debug("Could not find files with 'content_type': %r" % content_type)
		return []

def store_file(temporary_stored_file, directory, charset='utf-8'):
	try:
		temporary_stored_file.write(directory)
    		db.session.add(temporary_stored_file)
		db.session.commit()
		return temporary_stored_file
	except IOError, e:
		app.logger.exception("Could not write %s" % temporary_stored_file)
		return None
	except Exception, e:
		app.logger.exception("Could not save %s in database" % temporary_stored_file)
		return None
