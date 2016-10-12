#! /usr/bin/python
# -*- coding: utf-8
help = \
'''
Wygrzebuje różne informacje z pliku DICOM RS (RT Structure Set)

    Użycie:
            [ python ] %s plik-RS [ nazwa-ROI | -f ] 

	Wywołany z samą nazwą pliku - wylistuje ROI.
	Wywołany z nazwą pliku i opcją -f - wylistuje obrazy odniesienia dla pierwszego ROI z pliku.
	Wywołany z nazwą pliku i nazwą ROI - wylistuje obrazy odniesienia dla podanego ROI.

'''

import dicom
import sys
import os.path

def frames( st, path ):
	# wygrzebuje informacje o obrazkach pod które jest podpięty pierwszy z brzegu ROI, zawarty w st
	try:
		if  hasattr( st, 'ReferencedFrameofReferences'):
			sq = st.ReferencedFrameofReferences[0]
			st = sq.RTReferencedStudies[0]
			sr = st.RTReferencedSeries[0]
			frames = []
			for f in sr.ContourImages:
				prefix = 'CT' if 'CT' in f.ReferencedSOPClassUID.name else 'MR'
				filename = os.path.dirname(path) + "/" + prefix + "." + f.ReferencedSOPInstanceUID + ".dcm"
				tmp = dicom.read_file( filename )
				xyz = map( lambda x: float(x) , tmp.ImagePositionPatient ) if hasattr( tmp, 'ImagePositionPatient' ) else (0.0, 0.0, 0.0 )
				z = float(tmp.SliceLocation) if hasattr( tmp, 'SliceLocation' ) else 0.0
				if z != xyz[2]:
					print "UWAGA: w pliku",filename," wartość ImagePositionPatient jest inna niż SliceLocation!"
				res = map( lambda x: float(x) , tmp.PixelSpacing ) if hasattr( tmp, 'PixelSpacing' ) else (0.0, 0.0 )	
				res.append( float(tmp.SliceThickness) if hasattr( tmp, 'SliceThickness' ) else 0.0 )
				pix =  [ int(tmp.Columns) if hasattr( tmp, 'Columns' ) else 0, int(tmp.Rows) if hasattr( tmp, 'Rows' ) else 0 ]	
				frames.append( (filename, xyz, res, pix ) )
			frames = sorted( frames, key=lambda x: x[1][2] )  # sortujemy rosnąco po z
			return frames
	except:
		pass
	return None

def framesForROI( roiname, st, path ):
	# wygrzebuje informacje o obrazkach pod które jest podpięty ROI o nazwie roiname, zawarty w st
	try:
		if hasattr( st, 'StructureSetROIs' ) and hasattr( st, 'ReferencedFrameofReferences'):
			#print fname, "has StructureSetROIs will search for", roiname
			for r in st.StructureSetROIs:
				if r.ROIName == roiname:
					refFrame = r.ReferencedFrameofReferenceUID
					sequences = []
					for sq in st.ReferencedFrameofReferences:
						if sq.FrameofReferenceUID == refFrame:
							for st in sq.RTReferencedStudies:
								for sr in st.RTReferencedSeries:
									frames = []
									for f in sr.ContourImages:
										prefix = 'CT' if 'CT' in f.ReferencedSOPClassUID.name else 'MR'
										filename = os.path.dirname(path) + "/" + prefix + "." + f.ReferencedSOPInstanceUID + ".dcm"
										try:
											tmp = dicom.read_file( filename )
										except:
											frames.append( (filename, [0,0,0], [0,0], [0,0], 'missing/unreadable file' ) )
											continue
										xyz = map( lambda x: float(x) , tmp.ImagePositionPatient ) if hasattr( tmp, 'ImagePositionPatient' ) else (0.0, 0.0, 0.0 )
										z = float(tmp.SliceLocation) if hasattr( tmp, 'SliceLocation' ) else 0.0
										if z != xyz[2]:
											print "UWAGA: w pliku",filename," wartość ImagePositionPatient jest inna niż SliceLocation!"
										res = map( lambda x: float(x) , tmp.PixelSpacing ) if hasattr( tmp, 'PixelSpacing' ) else (0.0, 0.0 )	
										res.append( float(tmp.SliceThickness) if hasattr( tmp, 'SliceThickness' ) else 0.0 )
										pix =  [ int(tmp.Columns) if hasattr( tmp, 'Columns' ) else 0, int(tmp.Rows) if hasattr( tmp, 'Rows' ) else 0 ]	
										frames.append( (filename, xyz, res, pix, 'OK' ) )
									frames = sorted( frames, key=lambda x: x[1][2] )
									sequences.append( frames )
					return sequences
	except:
		pass
	return None

def listROI( st, path ):
        if hasattr( st, 'StructureSetROIs' ):
                print "\t  #   Name                # of contours                         BBox [mm]                           resolution [mm]"
                print "\t  -------------------------------------------------------------------------------------------------------------------"
                for i,r in enumerate(st.StructureSetROIs):
                        nc = 0
                        for c in st.ROIContours:
                                if c.RefdROINumber == r.ROINumber:
                                        nc = len(c.Contours)
                                        bbox = [ 1e6, -1e6, 1e6, -1e6, 1e6, -1e6 ]
                                        for co in c.Contours:
                                                for p in range(co.NumberofContourPoints):
                                                        x, y, z = coords(co, p)
                                                        bbox[0] = x if x < bbox[0] else bbox[0]
                                                        bbox[1] = x if x > bbox[1] else bbox[1]
                                                        bbox[2] = y if y < bbox[2] else bbox[2]
                                                        bbox[3] = y if y > bbox[3] else bbox[3]
                                                        bbox[4] = z if z < bbox[4] else bbox[4]
                                                        bbox[5] = z if z > bbox[5] else bbox[5]
                        res = resForROI( r.ROIName, st, path )
                        if res != None:
                                print "\t%3d   %-20s   %5d        [%7.2f:%7.2f]x[%7.2f:%7.2f]x[%7.2f:%7.2f]   [%5.2f,%5.2f,%5.2f]" % ( r.ROINumber, r.ROIName, nc, bbox[0], bbox[1], bbox[2], bbox[3], bbox[4], bbox[5], res[0], res[1], res[2] )
                        else:
                                print "\t%3d   %-20s   %5d        [%7.2f:%7.2f]x[%7.2f:%7.2f]x[%7.2f:%7.2f]   unknown" % ( r.ROINumber, r.ROIName, nc, bbox[0], bbox[1], bbox[2], bbox[3], bbox[4], bbox[5] )

def coords(c, p):
  x = c.ContourData[3*p+0]
  y = c.ContourData[3*p+1]
  z = c.ContourData[3*p+2]
  return x, y, z

def resForROI( roiname, st, path ):
        # wygrzebuje informacje o rozdzielczości obrazków pod które jest podpięty ROI o nazwie roiname, zawarty w st
	try:
		if hasattr( st, 'StructureSetROIs' ) and hasattr( st, 'ReferencedFrameofReferences'):
			for r in st.StructureSetROIs:
				if r.ROIName == roiname:
					refFrame = r.ReferencedFrameofReferenceUID
					for f in st.ReferencedFrameofReferences:
						if f.FrameofReferenceUID == refFrame:
							s = f.RTReferencedStudies[0].RTReferencedSeries[0]
							seriesUID = s.SeriesInstanceUID
							imgref = s.ContourImages[0]
							prefix = "CT"
							if "MR" in imgref.ReferencedSOPClassUID.name:
								prefix = "MR"
							imagefilename = os.path.dirname(path) + "/" + prefix + "." + imgref.ReferencedSOPInstanceUID + ".dcm"
							img = dicom.read_file(imagefilename)
							return [ float(img.PixelSpacing[0]), float(img.PixelSpacing[1]), float(img.SliceThickness) ]
	except:
		pass
	return None

def resForROIPersistent( roiname, st, path ):
        # wygrzebuje informacje o rozdzielczości obrazków pod które jest podpięty ROI o nazwie roiname, zawarty w st
	try:
		if hasattr( st, 'StructureSetROIs' ) and hasattr( st, 'ReferencedFrameofReferences'):
			for r in st.StructureSetROIs:
				if r.ROIName == roiname:
					refFrame = r.ReferencedFrameofReferenceUID
					for f in st.ReferencedFrameofReferences:
						if f.FrameofReferenceUID == refFrame:
							for st in f.RTReferencedStudies:
								for sr in st.RTReferencedSeries:
                                                                        for f in sr.ContourImages:
										seriesUID = sr.SeriesInstanceUID
										prefix = "CT"
										if "MR" in f.ReferencedSOPClassUID.name:
											prefix = "MR"
										imagefilename = os.path.dirname(path) + "/" + prefix + "." + f.ReferencedSOPInstanceUID + ".dcm"
										try:
											img = dicom.read_file(imagefilename)
											return [ float(img.PixelSpacing[0]), float(img.PixelSpacing[1]), float(img.SliceThickness) ]
										except:
											continue
	except:
		pass
	return None

if __name__ == "__main__":
	if len(sys.argv) < 2:
		print help % ( sys.argv[0] )
		sys.exit(1)

	if os.path.isdir( sys.argv[1] ):
		from os import listdir
		files = [ os.path.join(sys.argv[1],f) for f in listdir(sys.argv[1]) if os.path.isfile( os.path.join(sys.argv[1],f)) ]
	else:
		files = [ sys.argv[1] ]

	for fname in files:
		#print fname
		try:
			st = dicom.read_file( fname )
		except:
			#print "\t NOT DICOM"
			continue
		if not hasattr( st, 'StructureSetROIs'):
			#print "\t HAS NO ROIs"
			continue

                print "\nFILE ", fname,':'

		if len(sys.argv) < 3:
			listROI( st, fname )
			continue

		if len(sys.argv) == 3 and sys.argv[2] == '-f':
			frames = frames( st, fname )
 			for fn in frames:
				print "\t", fn[0], "\t", fn[1:]
			continue

		roiname = sys.argv[2]
		frames = framesForROI( roiname, st, fname )
		if frames == None:
			print "Nie znaleziono obrazów dla", roiname, "w pliku", fname
			continue

		print len(frames), " sekwencji obrazów dla", roiname 
		for i,s in enumerate(frames):
			print "Sekwencja nr %d, %d obrazów:" % (i+1,len(s))
			for fn in s:
				print "\t", fn[0], "\t", fn[1:]
