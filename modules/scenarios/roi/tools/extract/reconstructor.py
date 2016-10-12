#! /usr/bin/python
# -*- coding: utf-8
help = \
'''
Ekstraktor obszarów zainteresowania (ROI) zaznaczonych przez lekarza w postaci konturów.
Przetwarza pliki DICOM.  Zapisuje wyciągnięty obszar w postaci pliku vtk zawierającego PolyDataset.

    -----------------------------------------------------------------------------
    |  Bazuje na klasie vtkSurfaceReconstructionFilter i nie działa najlepiej!  |
    -----------------------------------------------------------------------------

Użycie:
  python %s plik-wejsciowy [ nazwa-ROI [ opcje ] ]

Wynik zostaje zapisany w pliku nazwa-ROI.vtk (można to wyłączyć opcją -novtk)
Wynik może też zostać zapisany jako STL w pliku nazwa-ROI.stl lub jako Stanford Polygon File w pliku nazwa-ROI.ply.

Wynikowa siatka może też zostać uproszczona (alg. Quadric Decimation) i zapisana w pliku nazwa-ROI_sim.(vtk,stl,ply)

Wywołany bez nazwy-ROI wylistuje wszystkie ROI znalezione w pliku wejsciowym.

Opcje:
 -l first:last - działa tylko w przekrojach od first do last włącznie (przekroje sa liczone od dołu (wsp. z) wyciąganego obszaru)
 -t dx:dy:dz   - przesuwa wynik o wektor [dx,dy,dz]
 -stl - zapisz STL
 -ply - zapisz ply
 -novtk - nie zapisuj vtk
 -s stepx:stepy:stepz - uprość siatkę -> wynik zostaje zapisany w pliku nazwa-ROI_sim.(vtk,stl,ply).
 -d points:grid:print:all - zapisz pliki z punktami / siecią (do testowania) / drukuj dodatkowe informacje
 -v  - pokaż wynik
 -r rx:ry:rz - zmienia rozdzielczość na zadaną

TODO:
Odczytywać rozdzielczość z pliku(ów) DICOM.
'''


import dicom
import sys
import vtk
from vtk.util.colors import *

class ROIReconstructor:
	def __init__(self, dataset, res, debugPrint=False, debugGrid=False, debugPoints=False, beQuiet=False, tresholdValue=0.5):
		self.res = res
		self.bbox = None
		self.dataset = dataset
		self.roiname = None
		self.roinumber = None
		self.roisurface = None
		self.centrOfGrav = None
		self.co = None
		self.first = self.last = -1
                self.debugPrint = debugPrint
                self.debugGrid = debugGrid
                self.debugPoints = debugPoints
		self.Quiet = beQuiet
		self.tresholdValue = tresholdValue

	def extract(self, roiname, first=-1, last=-1, exactly=True):
		if not self.setROIname( roiname ):
			return False
 		self.first = first
		self.last = last
		self.roisurface = None
		self.dobbox()
		if self.bbox == None:
			return False

		self.ctr = []
		pointSource = vtk.vtkProgrammableSource()

		def collectPoints():
 			output = pointSource.GetPolyDataOutput()
			points = vtk.vtkPoints()
			output.SetPoints(points)
			for c in self.co.Contours:
                		for p in range(c.NumberofContourPoints):
                        		x, y, z = self.cords(c, p)
                        		points.InsertNextPoint( x, y, z )
                        		self.ctr.append( [x, y, z] )
                	if self.debugPoints:
                        	self.savePointsIfWanted()
 
		pointSource.SetExecuteMethod(collectPoints)
	
		if self.debugPrint:
			print "will now reconstruct surface"

		# Construct the surface and create isosurface.
		surf = vtk.vtkSurfaceReconstructionFilter()
		surf.SetInputConnection(pointSource.GetOutputPort())

		cf = vtk.vtkContourFilter()
		cf.SetInputConnection(surf.GetOutputPort())
		cf.SetValue(0, 0.0)

		# Sometimes the contouring algorithm can create a volume whose gradient
		# vector and ordering of polygon (using the right hand rule) are
		# inconsistent. vtkReverseSense cures this problem.
		reverse = vtk.vtkReverseSense()
		reverse.SetInputConnection(cf.GetOutputPort())
		reverse.ReverseCellsOn()
		reverse.ReverseNormalsOn()

		self.roisurface = reverse.GetOutput()

		if self.debugPrint:
			print self.roisurface

		if self.debugPrint:
			print "reconstruction finished. All done"

		return True

	def setROIname(self, roiname ):
		# sprawdza, czy w self.dataset jest ROI o podanej nazwie
                # i jeśli jest, to ustawia tę nazwę jako self.roiname, ustawia też self.roinumber
                # oraz zeruje kontur i bbox
		self.co = None
		self.bbox = None
		self.roiname = None
		self.roinumber = None
		for r in self.dataset.StructureSetROIs:
			if r.ROIName == roiname:
				self.roiname = roiname
				self.roinumber = r.ROINumber
				for c in self.dataset.ROIContours:
					if c.RefdROINumber == self.roinumber:
						self.co = c
				return self.co != None
		return False

	# Pomocnicze metody
	def savePointsIfWanted( self ):
		ctrf = open('ctr.xml','w')
		print >>ctrf, '''<?xml version="1.0"?>
<dolfin xmlns:dolfin="http://fenicsproject.org">
<mesh celltype="tetrahedron" dim="3">
<vertices size="%d">''' % (len(self.ctr))
		for i in range(len(self.ctr)):
			print >>ctrf, '<vertex index="%d" x="%f" y="%f" z="%f" />' % (i, self.ctr[i][0], self.ctr[i][1], self.ctr[i][2] )
		print >>ctrf, '''</vertices>
<cells size="0">
</cells>
</mesh>
</dolfin>
'''
	# end savePointsIfWanted

        def crossProduct(self, x0,y0, x1,y1, x2,y2):
                # cross product of 0-1 and 2-1 vectors
                return (x2-x1)*(y0-y1) - (x0-x1)*(y2-y1)

        def lowestRightmost(self,  c):
                # calculates lowest,rightmost vertex of contour c
                xl,yl,z = self.cords( c, 0 )
                pl = 0
                for p in range(1,c.NumberofContourPoints):
                        x,y,z = self.cords( c, p )
                        if y < yl or y == yl and x > xl:
                                xl = x
                                yl = y
                                pl = p
                return (pl, xl, yl )

        def contourOrientedClockwise( self, c ):
                # returns True if c is oriented clockwise, False otherwise
                v,x,y = self.lowestRightmost( c )
                pv = v-1 if v > 0 else c.NumberofContourPoints-1 # previous of v
                vn = v+1 if v < c.NumberofContourPoints-1 else 0 # next 
                xp,yp,z = self.cords( c, pv )
                xn,yn,z = self.cords( c, vn )
                return self.crossProduct( xp,yp, x,y, xn, yn ) < 0


	# zwraca wspolrzedne x, y, z punktu o indeksie p z danych konturu c
	def cords(self, c, p):
		x = c.ContourData[3*p+0]
		y = c.ContourData[3*p+1]
		z = c.ContourData[3*p+2]
		return x, y, z

	def dobbox(self):
		if self.co == None:
			self.bbox = None
			return False
		self.bbox = [1e8, 1e8, 1e8, -1e8, -1e8, -1e8]
		npoints = 0
		self.centrOfGrav = [0.0,0.0,0.0]
		for c in self.co.Contours:
			npoints += c.NumberofContourPoints
			# test code
			if self.debugPrint:
				print c.ContourData
				print "Contour oriented " + ( "clockwise" if self.contourOrientedClockwise( c ) else "counter-clockwise" )
				if c.NumberofContourPoints < 10:
					for p in range(c.NumberofContourPoints):
						print self.cords(c,p)
				else:
					print c.NumberofContourPoints
			# end of test code
			for p in range(c.NumberofContourPoints):
				x, y, z = self.cords(c, p)
				self.bbox[0] = x if x < self.bbox[0] else self.bbox[0]
				self.bbox[1] = y if y < self.bbox[1] else self.bbox[1]
				self.bbox[2] = z if z < self.bbox[2] else self.bbox[2]
				self.bbox[3] = x if x > self.bbox[3] else self.bbox[3]
				self.bbox[4] = y if y > self.bbox[4] else self.bbox[4]
				self.bbox[5] = z if z > self.bbox[5] else self.bbox[5]
				self.centrOfGrav[0] += x
				self.centrOfGrav[1] += y
				self.centrOfGrav[2] += z
	
		self.centrOfGrav[0] /= npoints
		self.centrOfGrav[1] /= npoints
		self.centrOfGrav[2] /= npoints
	
		# zabezpieczenie przed "dziurami" na krancach"
		self.bbox[0] -= 2*self.res[0]
		self.bbox[1] -= 2*self.res[1]
		self.bbox[3] += 2*self.res[0]
		self.bbox[4] += 2*self.res[1]
	
		# specjalnie po z - tylko przed pierwszym lub po ostatnim
		self.bbox[2] -= 2*self.res[2]
		if self.first > 0:
			self.bbox[2] += self.first*self.res[2]
	
		if self.last <= 0:
			self.bbox[5] += 2*self.res[2]
		else:
			self.bbox[5] = self.bbox[2] + self.res[2] * (self.last-self.first)

		return True

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

  roiname = sys.argv[2]

  first= last= -1
  for i in range(3,len(sys.argv)-1):
    if sys.argv[i] == '-l':
	first, last = map(lambda s: int(s), sys.argv[i+1].split(':') )

  res = [ 1.6, 1.6, 3 ]
  for i in range(3,len(sys.argv)-1):
    if sys.argv[i] == '-r':
	res[0], res[1], res[2] = map(lambda s: float(s), sys.argv[i+1].split(':') )
        print "Resolution changed to [%f %f %f] mm" % ( res[0], res[1], res[2] )

  for i in range(3,len(sys.argv)-1):
    if sys.argv[i] == '-t':
	dx, dy, dz = map(lambda s: float(s), sys.argv[i+1].split(':') )
        print "Translation by [%f %f %f] mm" % ( dx, dy, dz )

  visualize = False;
  for i in range(3,len(sys.argv)):
    if sys.argv[i] == '-v':
	visualize = True

  polyData = True
  for i in range(3,len(sys.argv)):
    if sys.argv[i] == '-novtk':
        polyData = False

  writePLY = False
  for i in range(3,len(sys.argv)):
    if sys.argv[i] == '-ply':
        writePLY = True

  writeSTL = False
  for i in range(3,len(sys.argv)):
    if sys.argv[i] == '-stl':
        writeSTL = True

  debugPoints= debugGrid= debugPrint= False
  for i in range(3,len(sys.argv)-1):
    if sys.argv[i] == '-d':
      if sys.argv[i+1].find( 'grid' ) >= 0:
        debugGrid = True
      if sys.argv[i+1].find( 'points' ) >= 0:
        debugPoints = True
      if sys.argv[i+1].find( 'print' ) >= 0:
        debugPrint = True
      if sys.argv[i+1].find( 'all' ) >= 0:
        debugPrint = True
        debugPoints = True
        debugGrid = True

  decimate = False
  for i in range(3,len(sys.argv)-1):
    if sys.argv[i] == '-s':
      secX, secY, secZ = map(lambda s: int(s), sys.argv[i+1].split(':') )
      decimate = True

  ex = ROIReconstructor( st, res, debugPrint=debugPrint, debugGrid=debugGrid, debugPoints=debugPoints, beQuiet=False )
  if not ex.extract( roiname, first, last ):
    print roiname, "not found in dataset"
    sys.exit(1)


  if polyData:
    w = vtk.vtkPolyDataWriter()
    w.SetInput(ex.roisurface)
    w.SetFileName(roiname+".vtk")
    w.Write()
    print roiname+".vtk written"

  if writeSTL:
    stl = vtk.vtkSTLWriter()
    stl.SetFileName(roiname+".stl")
    stl.SetInput(ex.roisurface)
    stl.Write()
    print roiname+".stl written"

  if writePLY:
    ply = vtk.vtkPLYWriter()
    ply.SetFileName(roiname+".ply")
    ply.SetInput(ex.roisurface)
    ply.Write()
    print roiname+".ply written"

  if decimate:
    dec = vtk.vtkQuadricClustering()
    dec.SetNumberOfXDivisions(secX)
    dec.SetNumberOfYDivisions(secY)
    dec.SetNumberOfZDivisions(secZ)
    dec.SetInput(ex.roisurface)

    if polyData:
      w = vtk.vtkPolyDataWriter()
      w.SetInput(dec.GetOutput())
      w.SetFileName(roiname+"_sim.vtk")
      w.Write()
      print roiname+"_sim.vtk written"

    if writeSTL:
      stl = vtk.vtkSTLWriter()
      stl.SetFileName(roiname+"_sim.stl")
      stl.SetInputConnection(dec.GetOutputPort())
      stl.Write()
      print roiname+"_sim.stl written"

    if writePLY:
      ply = vtk.vtkPLYWriter()
      ply.SetFileName(roiname+"_sim.ply")
      ply.SetInputConnection(dec.GetOutputPort())
      ply.Write()
      print roiname+"_sim.ply written"

  if visualize:
    aShrinker = vtk.vtkShrinkPolyData()
    aShrinker.SetShrinkFactor(0.9)
    aShrinker.SetInput(ex.roisurface)
    aMapper = vtk.vtkPolyDataMapper()
    aMapper.ScalarVisibilityOff()
    aMapper.SetInputConnection(aShrinker.GetOutputPort())
    Triangles = vtk.vtkActor()
    Triangles.SetMapper(aMapper)
    Triangles.GetProperty().SetDiffuseColor(banana)
    Triangles.GetProperty().SetOpacity(.6)

    # Create the Renderer, RenderWindow, and RenderWindowInteractor
    ren = vtk.vtkRenderer()
    renWin = vtk.vtkRenderWindow()
    renWin.AddRenderer(ren)
    renWin.SetSize(640, 480)
    iren = vtk.vtkRenderWindowInteractor()
    iren.SetRenderWindow(renWin)

    # Add the actors to the renderer
    ren.AddActor(Triangles)

    # Set the background color.
    ren.SetBackground(slate_grey)

    # Position the camera.
    ren.ResetCamera()
    ren.GetActiveCamera().Dolly(1.2)
    ren.GetActiveCamera().Azimuth(30)
    ren.GetActiveCamera().Elevation(20)
    ren.ResetCameraClippingRange()

    iren.Initialize()
    renWin.Render()
    iren.Start()


