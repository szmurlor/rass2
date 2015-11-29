from flask import request, flash
import content_type_helper
import storage

__scenario__ = "Optymalizacja PARETO"

class FileType(object):
	PARETO = 'text/pareto'
	RTPLAN = 'application/rtplan+dicom'
	RTSS = 'application/rtss+dicom'
	CT = 'application/ctimage+dicom'

def start():
	rtplan = storage.find_files_by_type('text/plain')
	rtss = []
	return {
		'rtplan': rtplan,
		'rtss': rtss
	}

def upload(dataset):
	print 'DATASET %r' % dataset
	if dataset.uid is None:
		dataset = storage.store_file(dataset)
	if content_type_helper.is_archive(dataset.content_type):
		extract()
	return {'uploaded':True}
