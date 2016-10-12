# -*- coding: utf-8 -*-
from flask import request, flash, g
from modules.scenarios.roi.tools.extract.digRS import resForROIPersistent
from datetime import date
from subprocess import call
from shutil import copy2
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

roimodify_script = "modules/scenarios/roi/tools/extract/roimodify.py"
psr_script = "modules/scenarios/roi/tools/poisson/build/bin/PoissonReconstruction"
makePNG = False
matplotlib = False

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
	if not os.environ.has_key('DISPLAY') or os.environ['DISPLAY'] == '':
		makePNG = False
	return _reload()

def extract(archive):
	if archive.uid is None:
		today = date.today().strftime("%d-%m-%Y")
		directory = os.path.join(g.user_home, 'roi', today)
		archive = storage.store_file(archive, directory)

	if content_type_helper.is_archive(archive.content_type):
		directory = filesystem_helper.extract_archive(archive.path, archive.content_type)
		for path in filesystem_helper.list_path(directory + '/**/RS*.dcm'):
			storage.new_file_from_filesystem(path, 'application/rtss+dicom')
		for path in filesystem_helper.list_path(directory + '/**/rtss*.dcm'):
			storage.new_file_from_filesystem(path, 'application/rtss+dicom')

	return _reload()

def process(rtss):
	rois = []

	f = dicom.read_file(rtss.path)
	if hasattr(f, 'StructureSetLabel'):
		label = f.StructureSetLabel
	else:
		label = 'unlabelled'
	if hasattr(f, 'StructureSetROIs'):
		for r in f.StructureSetROIs:
			res = resForROIPersistent(r.ROIName, f, rtss)
			for c in f.ROIContours:
				if c.RefdROINumber == r.ROINumber:
					try:
						roiName = r.ROIName.decode('utf-8')
					except ValueError, e:
						roiName = r.ROIName.decode('latin2')

					roi = {'name':roiName, 'rsname': f.filename, 'id':roiName + '@' + f.filename + '@' + label, 'color':rgbhex(c.ROIDisplayColor), 'resolution':res}
					rois.append(roi)
					break # go to the next ROI
	f.close()

	data = _reload()
	data.update({
		'roi': rois,
		'selected_rtss': rtss
	})
	return data

def select_roi(roi, rtss):
	session.setdefault('selected_roi', roi)
	session.setdefault('selected_rtss', rtss)
	data = _reload()

	label = 'brak'
	new_roi = 'test'
	resolution = None
	for r in data['roi']:
		if r['name'] == roi:
			resolution = r['resolution']

	data.update({
		'label': label,
		'new_roi': new_roi,
		'resolution': resolution
	})
	return data

def transform_roi(roi, rtss, rotation_mode, dz, dx, dy, rx, ry, rz, tx, ty, tz, psr_depth, new_roi, new_label):
	source = rtss.path
	target = rtss.path + '2'
	copy2(source, target)
	env = os.environ.copy()
	env["PYTHONIOENCODING"] = 'utf-8'  # inaczej nie można robić "print" w programach wywoływanych "call"
	cmd = ['python', roimodify_script, target, roi, new_roi]

	if dx or dy or dz:
		cmd += ['-r', '%s:%s:%s' % (dx or 1, dy or 1, dz or 1)]  # tu chyba lepiej protestować, jak jej nie ma, a powinna być

	if rx or ry or rz:
		if rotation_mode == 'centerOfGrav':
			cmd += ['-loc_rot', '%s:%s:%s' % (rx or 0, ry or 0, rz or 0)]
		else:
			cmd += ['-base_rot', '%s:%s:%s' % (rx or 0, ry or 0, rz or 0)]

	if tx or ty or tz:
		cmd += ['-tr', '%s:%s:%s' % (tx or 0, ty or 0, tz or 0)]

	psr_depth = int(psr_depth) if len(psr_depth) > 0 else 0
	if psr_depth >= 1 and psr_depth <= 10:
		cmd += ['-psr', '%d'%(psr_depth)]
		cmd += ['-psrTool', psr_script]
	else:
		psr_depth = 0

	if new_label and len(new_label) > 0:
		cmd += ['-label', new_label ]

	"""
	imgpath = None
	if makePNG: # za chwilę dodamy tu sprawdzenie, czy użytkownik chce
		imgpath = '%s_vtk.png' % new_roi
		cmd += ['-png', file_path(self.home, 'dataset', imgpath)]

	roi_img = None
	new_roi_img = None
	if matplotlib:
		cmd += ['-matplotlib', file_path(self.home, 'dataset') ]
		roi_img = roi + '.png'
		new_roi_img = new_roi + '.png'
	"""

	print "Calling %s" % (' '.join(cmd))
	if call(cmd, env=env) != 0:
		raise ValueError(u"Błąd przy próbie transformacji")

	return {}
