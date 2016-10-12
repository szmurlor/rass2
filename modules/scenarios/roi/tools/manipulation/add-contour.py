# -*- coding: utf-8
help = \
'''
Jeszcze nie gotowe - coś jest źle, ale nie wiem, co.

Wstawia obszar zainteresowania (ROI) w  postaci konturów do pliku DICOM.

Użycie:
  python %s plik-wejsciowy-dicom plik-z-obszarem-ROI

W wyniku działania programu zostaje zmodyfikowany plik wejsciowy.

'''


import dicom
import copy
import sys

if __name__ == '__main__':
  if len(sys.argv) == 1 or sys.argv[1].lower().startswith('-h'):
    print help % sys.argv[0]
    sys.exit(0)

  fname = sys.argv[1]
  st = dicom.read_file(fname)
  if len(sys.argv) < 3:
    for r in st.StructureSetROIs:
      print r.ROIName
    sys.exit(0)

  roi = None
  roifile = open( sys.argv[2], 'r' )
  roiname = roifile.readline().rstrip('\r\n')

  for i, r in enumerate(st.StructureSetROIs):
    if r.ROIName == roiname:
      print "ROI named ",roiname," already exists i input DICOM - use another name"
      sys.exit(1)

  # skopiuj pierwszy ROI 
  ds = copy.deepcopy(st.StructureSetROIs[0])
  # popraw w nim dane
  ds.ROIName = roiname
  ds.ROINumber = len(st.StructureSetROIs[0])+1
  # dodaj go na koniec
  st.StructureSetROIs.append(ds)

  # To samo z konturami - ale na razie źle działa
  ds = copy.deepcopy(st.ROIContours[0])
  ds.RefdROINumber = ds.ReferencedROINumber = len(st.StructureSetROIs[0])
  ds.ROIDisplayColor = [ 224,255,64 ]
  del ds.Contours[1:len(ds.Contours)]
  ds.Contours[0].ContourData = [ -200, -200, -394, -200, -500, -394, 200, -500, -394, 200, -200, -394 ]
  ds.Contours[0].NumberofContourPoints = 4
  st.ROIContours.append(ds)

  dicom.write_file(fname,st)
  
