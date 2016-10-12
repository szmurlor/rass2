# -*- coding: utf-8
help = \
'''
Tnie PLY (Stanford Polygon File) prostopadłe do osi OZ.

Użycie:
  python %s input.ply output.ply plasterki [opcje]

  Plasterki:
       -t z0:z1:z2:...:zn
       -a z0:dz:n
   
'''

import sys
import re
import vtk

def dicomFmt( x ):
  return float(round(x*100))/100

def PolyDataZCutter( vtkPolyData, slices ):
  # Cuts vtkPolyData at z in slices
  result = []
  for z in slices:
    plane = vtk.vtkPlane()
    cutter = vtk.vtkCutter()
    cutter.SetInput(vtkPolyData)
    plane.SetOrigin(0,0,z)
    plane.SetNormal(0,0,1)
    cutter.SetCutFunction(plane)
    cutter.Update()
    cut = cutter.GetOutput()
    # nieudane eksperymenty - ale może trzeba więcej poczytać o vtkSplineFilter
    if False:
      vtkStripper = vtk.vtkStripper()
      vtkStripper.SetInput(cut) 
      vtkStripper.Update()
      cut = vtkStripper.GetOutput()
    if False:
      vtkSplineFilter = vtk.vtkSplineFilter()
      vtkSplineFilter.SetInput(cut)
      vtkSplineFilter.SetNumberOfSubdivisions(20)
      vtkSplineFilter.Update()
      cut = vtkSplineFilter.GetOutput()
    # koniec eksperymentów
    result.append(cut)
  return result

def ConstructContour( line, b, e ):
  # Internal help function for LineToPointList
  # converts segments line[b:e-1] into a list of points forming contour
  c = []
  for s in range(b,e):
    c.append(line[s][0])
  if line[e-1][1] != line[b][0]:  # czy tak może być?
    print "Warning: not closed contour starting at %d, ending at %d" % ( line[b][0], line[e-1][1] )
    c.append( line[e-1][1] )
  return c

def LineToPointList( line ):
  # converts unsorted, but at least partially continuous line of n-segments: [ [pa pb] ... [ pl pk] ]
  # into a list of points [ p1 p2 p3 ... pn ] [p1 p2 p3 ... pm] ...
  contours = []
  s = 0
  for i in range(1,len(line)):
    nxt= None
    #print line[1:i]
    #print line[i+1:]
    #print line[i-1][1]
    for k in range(i,len(line)):
      if line[k][0] == line[i-1][1]:
        nxt= line[k]
        break
    if nxt != None:
      line[k] = line[i]
      line[i] = nxt
    else:
      contours.append( ConstructContour( line, s, i ) )
      s = i
  contours.append( ConstructContour( line, s, len(line) ) )
  return contours

def PolyDataSetToContours( vtkPolyData, slices, debugMode=False ):
  cuts = PolyDataZCutter( vtkPolyData, slices )

  allcontours = []

  for cut in cuts:
    if cut.GetNumberOfLines() == 0:
      continue
    il = vtk.vtkIdList()
    cut.GetLines().InitTraversal()
    line = []
    while cut.GetLines().GetNextCell(il):
      lst= []
      for i in range(il.GetNumberOfIds()):
        lst.append( il.GetId(i) )
      line.append(lst)
    cnts = LineToPointList( line )
    if debugMode:
      print cut.GetNumberOfLines(), "lines,", cut.GetNumberOfPoints(), "points,", len(cnts), " contours"

    pts = cut.GetPoints()
    for cntr in cnts:
      pointlist= []
      xyz = [0,0,0]
      for p in cntr:
        pts.GetPoint( p, xyz )
        pointlist.append( dicomFmt(xyz[0]) )
        pointlist.append( dicomFmt(xyz[1]) )
        pointlist.append( dicomFmt(xyz[2]) )

      allcontours.append( pointlist )

  return allcontours

if __name__ == '__main__':
  if len(sys.argv) == 1 or sys.argv[1].lower().startswith('-h'):
    print help % sys.argv[0]
    sys.exit(0)

  r = reader = vtk.vtkPLYReader()
  r.SetFileName(sys.argv[1])
  inp = r.GetOutput()

  slices = None
  for i in range(2,len(sys.argv)-1):
    if sys.argv[i] == '-t':
      slices = map(lambda s: float(s), sys.argv[i+1].split(':') )
      break
    elif sys.argv[i] == '-a':
      par = map(lambda s: float(s), sys.argv[i+1].split(':') )
      if len(par) == 3:
        slices = map(lambda i: par[0]+i*par[1], range(int(par[2])) )
      else:
        print par, "???"
      break

  if slices == None:
    print "Złe wywołanie!\n", help % sys.argv[0]
    sys.exit(1)

  #print slices

  allcontours = PolyDataSetToContours( inp, slices )

  for c in allcontours:
    print c
