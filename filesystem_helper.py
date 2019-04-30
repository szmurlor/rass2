import logger
import os, errno
import content_type_helper
from glob import glob

class UnknownEncoding(Exception):
	pass

def mkdir_directories_for(path):
	directory, name = os.path.split(path)
	try:
		os.makedirs(directory)
	except OSError as exc: # Python >2.5
		if exc.errno == errno.EEXIST and os.path.isdir(directory):
			pass
		else:
			raise

def extract_archive(file_path, content_type):
	extractor = content_type_helper.get_archive_extractor(content_type)
	return extractor().extract(file_path)

def list_path(pattern):
	return glob(pattern)
		
def convert_to_unicode(raw_string):
	try:
		return raw_string.decode('utf-8') # converts to unicode
	except UnicodeDecodeError as e:
		pass
	try:
		return raw_string.decode('latin2') # converts to unicode
	except Exception as e:
		pass
	
	logger.debug("Could not convert %r using neither utf-8 nor latin2 decoder" % raw_string[:10])
	return raw_string
