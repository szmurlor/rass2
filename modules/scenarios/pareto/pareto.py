# -*- coding: utf-8 -*-
from flask import request, flash, g
from datetime import date
from subprocess import call
import content_type_helper
import filesystem_helper
import storage
import session
import dicom
import os

def rgbhex(rgb):
    r, g, b = rgb
    return '#' + format((r << 16 | g << 8 | b), '06X')

roi_colors = ['2BCCEA','33CCCC','3399CC','FFCC00','FF9900','FF3300','33FF00','33CC00','339900','FFCCFF','FF99CC','FF00CC','9966CC','993399','990066']

create_pareto_script = 'modules/scenarios/pareto/dicomvis/create_pareto_multi'

__scenario__ = "Optymalizacja Pareto"

class FileType(object):
	RTSS = 'application/rtss+dicom'
	CT = 'application/ctimage+dicom'

def _reload():
	archive = storage.find_files_by_type('application/zip')

	return {
		'archive': archive
	}

def start():
	return _reload()

def process(archive):
	if archive.uid is None:
		today = date.today().strftime("%d-%m-%Y")
		directory = os.path.join(g.user_home, 'pareto', today)
		archive = storage.store_file(archive, directory)

	if content_type_helper.is_archive(archive.content_type):
		directory = filesystem_helper.extract_archive(archive.path, archive.content_type)
		for path in filesystem_helper.list_path(directory + '/**/RS*.dcm'):
			storage.new_file_from_filesystem(path, 'application/rtss+dicom')
		for path in filesystem_helper.list_path(directory + '/**/rtss*.dcm'):
			storage.new_file_from_filesystem(path, 'application/rtss+dicom')

	dataset = archive.path
	env = os.environ.copy()
	env["PYTHONIOENCODING"] = 'utf-8'  # inaczej nie można robić "print" w programach wywoływanych "call"
	cmd = [ 'python', create_pareto_script, directory, directory, '-fixNT']

	print "Calling %s" % (' '.join(cmd))
	if call(cmd, env=env) != 0:
		raise ValueError(u"Błąd przy próbie transformacji")

	filename, _ = os.path.splitext(os.path.basename(dataset))
	archive = directory + '/' + filename + '.zip'

	cmd = ['bash', '-c', 'cd ' + directory + '; zip -R ' + archive + ' *.txt']
	if call(cmd) != 0:
		raise ValueError(u"Błąd przy próbie pakowania")

	return {'archive': archive}
