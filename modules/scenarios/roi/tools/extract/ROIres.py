# -*- coding: utf-8
help = \
'''
Guesses spatial resolution of images supporting given ROI

    Usage:
            python %s file roires

'''

import dicom
import sys
import os.path

def resForROI( roiname, st ):
	# wygrzebuje informacje o rozdzielczości obrazków pod które jest podpięty ROI o nazwie roiname, zawarty w st
	if hasattr( st, 'StructureSetROIs' ) and hasattr( st, 'ReferencedFrameofReferences'):
		#print fname, "has StructureSetROIs will search for", roiname
		for r in st.StructureSetROIs:
			#print "Testing", r.ROIName
			if r.ROIName == roiname:
				refFrame = r.ReferencedFrameofReferenceUID
				#print "Ref Frame = ", refFrame
				for f in st.ReferencedFrameofReferences:
					if f.FrameofReferenceUID == refFrame:
						s = f.RTReferencedStudies[0].RTReferencedSeries[0]
						#print dir(s)
                                        	seriesUID = s.SeriesInstanceUID
                                        	imgref = s.ContourImages[0]
						#print dir(s)
						#print "seriesUID=%s, First image: class=\"%s\" instance=\"%s\"" % (seriesUID, imgref.ReferencedSOPClassUID, imgref.ReferencedSOPInstanceUID )
						#print dir(imgref.ReferencedSOPClassUID)
						#print imgref.ReferencedSOPClassUID.__doc__
						#print imgref.ReferencedSOPClassUID.type
						#print imgref.ReferencedSOPClassUID.info
						prefix = "CT"
						if "MR" in imgref.ReferencedSOPClassUID.name:
							prefix = "MR"
						imagefilename = os.path.dirname(sys.argv[1]) + "/" + prefix + "." + imgref.ReferencedSOPInstanceUID + ".dcm"
						img = dicom.read_file(imagefilename)
						#print img.PixelSpacing, img.SliceThickness
						return [ float(img.PixelSpacing[0]), float(img.PixelSpacing[1]), float(img.SliceThickness) ]
	return None


if __name__ == "__main__":
	if len(sys.argv) != 3:
		print help % ( sys.argv[0] )
		sys.exit(1)

	fname = sys.argv[1]
	roiname = sys.argv[2]
	st = dicom.read_file( fname )
	res = resForROI( roiname, st )
	print "Resolution (in mm) for ROI %s is %s" % ( roiname, ("unknown" if res == None else res) )

