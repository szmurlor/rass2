#! /usr/bin/python
# -*- coding: utf-8
help = \
'''
Help for %s not yet ready.
'''


import dicom
import sys
from ROIres import resForROI

def coords(c, p):
  x = c.ContourData[3*p+0]
  y = c.ContourData[3*p+1]
  z = c.ContourData[3*p+2]
  return x, y, z

if __name__ == '__main__':
  if len(sys.argv) == 1 or sys.argv[1].lower().startswith('-h'):
    print help % sys.argv[0]
    sys.exit(0)

  for fname in sys.argv[1:len(sys.argv)]:
  	st = dicom.read_file(fname)
  	if hasattr( st, 'StructureSetROIs' ):
		print "\nFILE ", fname,':'
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
			res = resForROI( r.ROIName, st )
			if res != None:
      				print "\t%3d   %-20s   %5d        [%7.2f:%7.2f]x[%7.2f:%7.2f]x[%7.2f:%7.2f]   [%5.2f,%5.2f,%5.2f]" % ( r.ROINumber, r.ROIName, nc, bbox[0], bbox[1], bbox[2], bbox[3], bbox[4], bbox[5], res[0], res[1], res[2] )
			else:
      				print "\t%3d   %-20s   %5d        [%7.2f:%7.2f]x[%7.2f:%7.2f]x[%7.2f:%7.2f]   unknown" % ( r.ROINumber, r.ROIName, nc, bbox[0], bbox[1], bbox[2], bbox[3], bbox[4], bbox[5] )
