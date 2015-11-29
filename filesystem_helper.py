import os, errno

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

def convert_to_unicode(raw_string):
	try:
		return raw_string.decode('utf-8') # converts to unicode
	except UnicodeDecodeError, e:
		pass
	try:
		return raw_string.decode('latin2') # converts to unicode
	except Exception, e:
		pass

	raise UnknownEncoding()
