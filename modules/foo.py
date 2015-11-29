from flask import request, flash, g
from datetime import date
import content_type_helper
import storage
import os

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
	if dataset.uid is None:
		today = date.today().strftime("%d-%m-%Y")
		directory = os.path.join(g.user.home, 'pareto', today)
		dataset = storage.store_file(dataset, directory)

	if content_type_helper.is_archive(dataset.content_type):
		extract()

	return start()

def process(rtplan, rtss=None):
	return {
		'content': rtplan.read()
	}
