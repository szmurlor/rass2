from flask import request, flash, g
from datetime import date
import content_type_helper
import filesystem_helper
import storage
import os

__scenario__ = "Optymalizacja PARETO"

class FileType(object):
	PARETO = 'text/pareto'
	RTPLAN = 'application/rtplan+dicom'
	RTSS = 'application/rtss+dicom'
	CT = 'application/ctimage+dicom'

def start():
	archive = storage.find_files_by_type('application/zip')
	textfile = storage.find_files_by_type('text/plain')
	rtdose = storage.find_files_by_type('application/rtdose+dicom')
	return {
		'rtdose': rtdose,
		'archive': archive,
		'textfile': textfile
	}

def upload(dataset):
	if dataset.uid is None:
		today = date.today().strftime("%d-%m-%Y")
		directory = os.path.join(g.user.home, 'pareto', today)
		dataset = storage.store_file(dataset, directory)

	return start()

def process(textfile, archive):
	if content_type_helper.is_archive(archive.content_type):
		directory = filesystem_helper.extract_archive(archive.path, archive.content_type)
		for path in filesystem_helper.list_path(directory + '/**/RD.*.dcm'):
			print "Found %s" % path
			storage.new_file_from_filesystem(path, 'application/rtdose+dicom')

	return {
		'content': textfile.read()
	}
