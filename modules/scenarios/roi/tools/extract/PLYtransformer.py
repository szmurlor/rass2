# -*- coding: utf-8
help = \
'''
Transformer plików PLY (Stanford Polygon File).

Użycie:
  python %s input.ply output.ply [transformacje] [opcje]

  Transformacje układu współrzędnych:
  -t dx:dy:dz  == translacja [dx,dy,dz]
  -r ax:ay:az  == 3 rotacje wokół osi: OX o kąt ax, OY o kąt ay, OZ o kąt az

  Uwaga: Transformacja przekształca układ współrzędnych, a nie obiekt.
         Transformacje można składać.
         Rotacja, dla której podamy ax,ay i az będzie wykonana jako złożenie najpierw rotacji wokół OX, potem OY i na końcu OZ.
           (Oznacza to, że "-r 0:90:45" i "-r 0:0:45 -r 0:90:0" to dwie różne transformacje.)

  Opcje:
  -stl - zapisz wynik także w postaci STL
'''


import sys
import re
import vtk

def TransformPolyData( vtkPolyData, vtkTransform ):
  transFilter = vtk.vtkTransformPolyDataFilter()
  transFilter.SetInput(vtkPolyData)
  transFilter.SetTransform(vtkTransform)
  return transFilter.GetOutput()

if __name__ == '__main__':
  if len(sys.argv) == 1 or sys.argv[1].lower().startswith('-h'):
    print help % sys.argv[0]
    sys.exit(0)

  r = reader = vtk.vtkPLYReader()
  r.SetFileName(sys.argv[1])
  inp = r.GetOutput()

  print sys.argv[1] + " read"

  userTransform = vtk.vtkTransform()
  userTransform.PostMultiply()
  userTransform.Identity()
  for i in range(3,len(sys.argv)-1):
    if sys.argv[i] == '-t':
        dx, dy, dz = map(lambda s: float(s), sys.argv[i+1].split(':') )
        userTransform.Translate([dx,dy,dz])
    if sys.argv[i] == '-r':
        ax, ay, az = map(lambda s: float(s), sys.argv[i+1].split(':') )
        if ax != None and ax != 0.0:
          userTransform.RotateX(ax)
        if ay != None and ay != 0.0:
          userTransform.RotateY(ay)
        if az != None and az != 0.0:
          userTransform.RotateZ(az)

  writeSTL = False;
  for i in range(3,len(sys.argv)):
    if sys.argv[i] == '-stl':
      writeSTL = True

  out = TransformPolyData( inp, userTransform )

  w = vtk.vtkPLYWriter()
  w.SetInput(out)
  w.SetFileName(sys.argv[2])
  w.Write()
  print sys.argv[2] + " written"

  if writeSTL:
    sfn = re.sub( "\..*?$", ".stl", sys.argv[2] )
    sfn = sfn if sfn != sys.argv[2] else sys.argv[2] + ".stl"
    s = vtk.vtkSTLWriter()
    s.SetInput(out)
    s.SetFileName( sfn )
    s.Write()
    print  sfn + " written"
