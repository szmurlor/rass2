#! /usr/bin/python
# -*- coding: utf-8
help = \
'''
Usuwa obszar zainteresowania (ROI) z pliku DICOM.

Użycie:
  python %s plik-wejsciowy-dicom [ argumenty-opcjonalne ]

    Wywołany bez argumentów opcjonalnych wstawia do DICOMA trzy obszary testowe.
    Wywołany z dwoma argumentami opcjonalnymi: -r wzorzec  usunie z pliku wszystkie ROI o nawach zawierających wzorzec (wyr. regularne)
    Wywołany w jednym lub więcej arg. opcjonalnymi (pierwszym nie może być -r) potraktuje te argumenty jako nazwy ROI, które trzeba usunąć.

W wyniku działania programu zostaje zmodyfikowany plik wejsciowy.
'''


import dicom
import copy
import sys

def addROI( st, roiname, contours, algorithm="Added by GOOPESoft", baseROI=None, color=[43,204,234] ):
	if hasattr( st, 'StructureSetROIs' ) and len(st.StructureSetROIs) > 0:
		numbers = []
		baseIdx = 0
		for i,r in enumerate(st.StructureSetROIs):
			if r.ROIName == roiname:
				return False  # already exists a ROI with this name
			numbers.append( r.ROINumber )
			if baseROI != None and r.ROIName == baseROI:
				baseIdx = i
		numbers.sort()
		newNumber = numbers[-1]+1
		# copy base ROI
		newROI = copy.deepcopy(st.StructureSetROIs[baseIdx])
                # replace necessary data
		newROI.ROINumber = newNumber
		newROI.ROIGenerationAlgorithm = algorithm
		newROI.ROIName = roiname
		# and append an updated copy to st
		st.StructureSetROIs.append( newROI )

 		# contours 
                # find that matching baseROI
                baseCIdx = 0
		for i,c in enumerate(st.ROIContours):
			if c.RefdROINumber == st.StructureSetROIs[baseIdx].ROINumber:
				baseCIdx = i
		# make a copy of it
		newContourSet = copy.deepcopy(st.ROIContours[baseCIdx])
		# replace data
		newContourSet.RefdROINumber = newContourSet.ReferencedROINumber = newNumber
		newContourSet.ROIDisplayColor = color
		cTemplate = copy.deepcopy(  newContourSet.Contours[0] ) # a template for contour
		del newContourSet.Contours[:] 
		# create new set od contours
		for c in contours:
			nc = copy.deepcopy( cTemplate )
			nc.NumberofContourPoints = int(len(c) / 3)
			nc.ContourData = map(str, c)
			nc.ContourGeometricType = 'CLOSED_PLANAR'
			newContourSet.Contours.append( nc )
		# append to st
		st.ROIContours.append( newContourSet )
		return True
	else:
		print "\n\nSORRY: addind a ROI to dataset which does not contain any ROIS is not yet implemented!!!\n\n"
		return False

def delROI( st, roiname ):
	if hasattr( st, 'StructureSetROIs' ) and len(st.StructureSetROIs) > 0:
		roiNumber = None
		for i,r in enumerate(st.StructureSetROIs):
			if r.ROIName == roiname:
				idx = i
				roiNumber = r.ROINumber
				break
		if roiNumber == None:
			return False
		del st.StructureSetROIs[idx]
		#return True
                
		for i,c in enumerate(st.ROIContours):
			if c.RefdROINumber == roiNumber:
				del st.ROIContours[i]
				return True
	return False

def delMatchingROIs( st, roiname_pattern ):
	if hasattr( st, 'StructureSetROIs' ) and len(st.StructureSetROIs) > 0:
		import re
		roiNumbers = []
		idx = []
		for i,r in enumerate(st.StructureSetROIs):
			if re.search( roiname_pattern, r.ROIName ) != None:
				idx.append( i )
				roiNumbers.append( r.ROINumber )
		if len(roiNumbers) == 0:
			return False
		for ix in reversed(idx):
			del st.StructureSetROIs[ix]
                
		from itertools import izip
		reverse_enumerate = lambda l: izip(xrange(len(l)-1, -1, -1), reversed(l))
		for i,c in reverse_enumerate(st.ROIContours):
			if c.RefdROINumber in roiNumbers:
				del st.ROIContours[i]
				return True
	return False

if __name__ == '__main__':
  if len(sys.argv) == 1 or sys.argv[1].lower().startswith('-h'):
    print help % sys.argv[0]
    sys.exit(0)

  fname = sys.argv[1]
  st = dicom.read_file(fname)
  if len(sys.argv) == 4 and sys.argv[2] == '-r':
    delMatchingROIs( st, sys.argv[3] )
  elif len(sys.argv) > 2:
    for roi in sys.argv[2:]:
      if delROI( st, roi ):
        print roi, "deleted"
      else:
        print roi, "not found"
  else: # simple test - adds 3 contours to dataset
    c1= [ [ -200, -200, -398, -200, -500, -398, 200, -500, -398, 200, -200, -398 ],
          [ -200, -200, -396.5, -200, -500, -396.5, 200, -500, -396.5, 200, -200, -396.5 ],
          [ -200, -200, -395, -200, -500, -395, 200, -500, -395, 200, -200, -395 ] ]
    c2= [ [ -150, -150, -398, -150, -500, -398, 150, -500, -398, 150, -150, -398 ],
          [ -150, -150, -396.5, -150, -500, -396.5, 150, -500, -396.5, 150, -150, -396.5 ],
          [ -150, -150, -395, -150, -500, -395, 150, -500, -395, 150, -150, -395 ] ]
    c3= [ [ -100, -100, -398, -100, -500, -398, 100, -500, -398, 100, -100, -398 ],
          [ -100, -100, -396.5, -100, -500, -396.5, 100, -500, -396.5, 100, -100, -396.5 ],
          [ -100, -100, -395, -100, -500, -395, 100, -500, -395, 100, -100, -395 ] ]

    addROI( st, "test1", c1 )
    addROI( st, "test2", c2, baseROI=st.StructureSetROIs[1].ROIName )
    addROI( st, "test3", c3, baseROI=st.StructureSetROIs[3].ROIName, algorithm="MyGorithm", color=[43,204,65] )

  dicom.write_file(fname,st)
    
