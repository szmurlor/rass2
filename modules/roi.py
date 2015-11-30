from flask import request, flash, g
from datetime import date
import content_type_helper
import filesystem_helper
import storage
import session
import os

__scenario__ = "Modyfikacja ROI"

class FileType(object):
	RTSS = 'application/rtss+dicom'
	CT = 'application/ctimage+dicom'

def _reload():
	archive = storage.find_files_by_type('application/zip')
	rtss = storage.find_files_by_type('application/rtss+dicom')
	roi = session.get('roi', [])

	tx = ty = tz = 0
	rx = ry = rz = 0
	rotation_mode = 'GRAV'

	selected_rtss = session.get('selected_rtss')
	selected_roi  = session.get('selected_roi')

	if selected_rtss:
		for one in rtss:
			if one.uid == selected_rtss.uid:
				one.selected = True
	if selected_roi:
		for one in roi:
			one.pop('selected', None)
			if one['name'] == selected_roi:
				one['selected'] = True

	return {
		'roi': roi,
		'archive': archive,
		'tx': tx, 'ty': ty, 'tz': tz,
		'rx': rx, 'ry': ry, 'rz': rz,
		'rotation_mode': rotation_mode,
		'rtss': rtss
	}

def start():
	return _reload()

def extract(archive):
	if archive.uid is None:
		today = date.today().strftime("%d-%m-%Y")
		directory = os.path.join(g.user.home, 'roi', today)
		archive = storage.store_file(archive, directory)

	if content_type_helper.is_archive(archive.content_type):
		directory = filesystem_helper.extract_archive(archive.path, archive.content_type)
		for path in filesystem_helper.list_path(directory + '/**/RS*.dcm'):
			storage.new_file_from_filesystem(path, 'application/rtss+dicom')
		for path in filesystem_helper.list_path(directory + '/**/rtss*.dcm'):
			storage.new_file_from_filesystem(path, 'application/rtss+dicom')

	return _reload()

def process(rtss):
	print rtss.path
	roi = [
		{'color':'#f00', 'name':'ptv'}, 
		{'color':'#0f0', 'name':'ctv'},
		{'color':'#00f', 'name':'outline'}
	]
	
	data = _reload()
	data.update({
		'roi': roi,
		'selected_rtss': rtss
	})
	return data

def select_roi(roi, rtss):
	print 'python %s %s' % (rtss, roi)
	
	session.setdefault('selected_roi', roi)
	session.setdefault('selected_rtss', rtss)

	return _reload()
