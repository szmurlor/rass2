#! /usr/bin/python
# -*- coding: utf-8
help = \
'''
Ekstraktor obszarów zainteresowania (ROI) zaznaczonych przez lekarza w postaci konturów.
Przetwarza pliki DICOM.  Zapisuje wyciągnięty obszar w postaci pliku vtk zawierającego PolyDataset.

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
'''


import dicom
import sys
import vtk
from vtk.util.colors import *

class ROIExtractor:
	def __init__(self, dataset, res, debugPrint=False, debugGrid=False, debugPoints=False, beQuiet=False, tresholdValue=0.5):
		self.res = res
		self.bbox = None
		self.dataset = dataset
		self.roiname = None
		self.roinumber = None
		self.roicolor = None
		self.roisurface = None
		self.centrOfGrav = None
		self.co = None
		self.first = self.last = -1
                self.debugPrint = debugPrint
                self.debugGrid = debugGrid
                self.debugPoints = debugPoints
		self.Quiet = beQuiet
		self.tresholdValue = tresholdValue
		self.incontours = None

	def extract(self, roiname, first=-1, last=-1, exactly=True):
		if not self.setROIname( roiname ):
			return False
 		self.first = first
		self.last = last
		self.roisurface = None
		self.dobbox()
		if self.bbox == None:
			return False

		# tworze siatke VTK
		xn, yn, zn = self.numberOfBoxes()
		self.first = 0 if self.first == -1 else self.first
		self.last = zn if self.last == -1 else self.last
		if not self.Quiet:
			print "Slices: %d-%d -> z in (%f,%f)" % ( self.first, self.last, self.bbox[2], self.bbox[5] )
			print "BBox: [%f,%f]x[%f,%f]x[%f,%f]" % ( self.bbox[0], self.bbox[3], self.bbox[1], self.bbox[4], self.bbox[2], self.bbox[5] )
			print "Center of gravity: (%f,%f,%f)" % ( self.centrOfGrav[0], self.centrOfGrav[1], self.centrOfGrav[2] )
			print "Res: %s" % self.res
			print "Grid size: %dx%dx%d cubes" % (xn, yn, zn)

		if self.debugPrint:
			print "x: ", map( lambda i: self.bbox[0]+i*self.res[0], range(xn+1) )
			print "y: ", map( lambda i: self.bbox[1]+i*self.res[1], range(yn+1) )
			print "z: ", map( lambda i: self.bbox[2]+i*self.res[2], range(zn+1) )
			print "will make grid"

		gr = self.makeGrid()

		if self.debugPrint:
			print "gread created, will mark contours"

		self.ctr = []
		self.incontours = []
		for c in self.co.Contours:
			i,j,k,xm,ym,zm,filled = self.markContour( c, gr, exactly )

			# a tu pomysł z najniższym wierzchołkiem z prawej
			if not filled:
				i,j,k,xm,ym,zm,filled = self.fillFromLowestRightmost( c )

			# pomysł ze sprawdzaniem wszystkich wierzchołków
			if not filled:
				i,j,k,xm,ym,zm,filled = self.fillFromAnyCorner( c )

			if not filled and not self.Quiet:
				if i == None:
					print "Warning: unable to fill contour ", c.ContourData, " at slice # %d (z=%f mm) - no suitable seed point around (%f,%f) (This happens for small contours filled by the boundary itself.)" % (k,zm,xm,ym)
				else:
					print "Warning: unable to fill contour ", c.ContourData, " at slice # %d (z=%f mm) with seed at (%f,%f)" % (k,zm, (self.bbox[0]+i*self.res[0]), (self.bbox[1]+j*self.res[1]))
			elif not self.Quiet:
				print "Finished contour at slice # %d (z=%f mm)" % (k, zm)

			
		gr.GetPointData().SetScalars(self.val)

		if self.debugPoints:
			self.savePointsIfWanted()

		if self.debugGrid:
			wr = vtk.vtkXMLUnstructuredGridWriter()
			wr.SetFileName('grid.vtu')
			wr.SetDataModeToAscii()
			wr.SetInput( gr )
			wr.Write()

		if self.debugPrint:
			print "will now start marching cubes"

		marching = vtk.vtkContourFilter()
		marching.SetInput(gr)
		marching.SetValue(0, self.tresholdValue )
		marching.Update()

		self.roisurface = marching.GetOutputDataObject(0)

		if self.debugPrint:
			print "marching cubes finished. All done"

		if self.debugPrint:
			print self.roisurface
		return True

	def setROIname(self, roiname ):
		# sprawdza, czy w self.dataset jest ROI o podanej nazwie
                # i jeśli jest, to ustawia tę nazwę jako self.roiname, ustawia też self.roinumber
                # oraz zeruje kontur i bbox
		self.co = None
		self.bbox = None
		self.roiname = None
		self.roinumber = None
		self.incontours = None
		for r in self.dataset.StructureSetROIs:
			if r.ROIName == roiname:
				self.roiname = roiname
				self.roinumber = r.ROINumber
				for c in self.dataset.ROIContours:
					if c.RefdROINumber == self.roinumber:
						self.co = c
						self.roicolor = map( lambda x: int(x), c.ROIDisplayColor )
				return self.co != None
		return False

	# Funkcje dla konturów
	def makeGrid(self):
                # Tworzy bazową równomierną siatkę pokrywającą bbox
		xn, yn, zn = self.numberOfBoxes()
                self.vp = vtk.vtkPoints()
                self.val = vtk.vtkFloatArray()
                for zi in range(zn+1):
                        for yi in range(yn+1):
                                for xi in range(xn+1):
                                        self.vp.InsertNextPoint( self.bbox[0]+xi*self.res[0], self.bbox[1]+yi*self.res[1], self.bbox[2]+zi*self.res[2] )
                                        self.val.InsertNextValue(0.0)

		gr = vtk.vtkUnstructuredGrid()
                gr.Allocate(xn*yn*zn,10)
                for zi in range(zn):
                        for yi in range(yn):
                                for xi in range(xn):
                                        ids = vtk.vtkIdList()
                                        ids.InsertNextId( self.pointNumber(xi  , yi,   zi,   xn, yn) )
                                        ids.InsertNextId( self.pointNumber(xi+1, yi,   zi,   xn, yn) )
                                        ids.InsertNextId( self.pointNumber(xi+1, yi+1, zi,   xn, yn) )
                                        ids.InsertNextId( self.pointNumber(xi,   yi+1, zi,   xn, yn) )
                                        ids.InsertNextId( self.pointNumber(xi,   yi,   zi+1, xn, yn) )
                                        ids.InsertNextId( self.pointNumber(xi+1, yi,   zi+1, xn, yn) )
                                        ids.InsertNextId( self.pointNumber(xi+1, yi+1, zi+1, xn, yn) )
                                        ids.InsertNextId( self.pointNumber(xi,   yi+1, zi+1, xn, yn) )
                                        gr.InsertNextCell(12,ids)
                gr.SetPoints(self.vp)
		return gr

	def markContour( self, c, gr, exactly ):
		# zaznacza brzeg konturu c w tablicy self.val
		# (zaznaczanie jest schowane w f. putPix wywoływanej z f. bresenham i floodLevelFill)
                # stara się go wypełnić startując ze środka ciężkości
                # Jeśli exactly == True, przesuwa węzły siatki gr tak, aby leżały dokładnie na krawędziach konturu
		xn, yn, zn = self.numberOfBoxes()
		xp, yp, zp = self.cords(c, 0)
		ip, jp, kp = self.pointIndex(xp, yp, zp)
		if zp < self.bbox[2]-0.01*self.res[2] or zp > self.bbox[5]+0.01*self.res[2]:
			if self.debugPrint:
				print "%f not in (%f : %f)" % ( zp, self.bbox[2], self.bbox[5] )
			return True # kontur nie pasuje - DZIWNE - ale może rozdzielczość CT nie pasuje do siatki
		xm, ym = xp, yp # ziarno do wypełnienia konturu będzie obliczane jako środek ciężkości
		incn= [ xp, yp, zp ]
		for p in range(1,c.NumberofContourPoints):
			x, y, z = self.cords(c, p)
			incn.append( x )
			incn.append( y )
			incn.append( z )
			i, j, k = self.pointIndex(x, y, z)
			xm += x # środek ciężkości
			ym += y
			if k != kp:
				print "Error in contour ", c
				print "Points no. %d and %d have different z-coordinates!" % ( p-1, p )
				return False
			if exactly:
				self.continuousBresenham( ip, jp, i, j, k, xn, yn, xp, yp, x, y, z, gr ) # przesuniecie i zaznaczenie węzłów
			else:
				self.bresenham( ip, jp, i, j, k, xn, yn ) # tylko zaznaczenie węzłów
			ip = i
			jp = j
			xp = x
			yp = y
			kp = k
		# domknięcie konturu
		self.incontours.append( incn )
		x, y, z = self.cords(c, 0)
		i, j, k = self.pointIndex(x, y, z)
		if exactly:
			self.continuousBresenham( ip, jp, i, j, k, xn, yn, xp, yp, x, y, z, gr )
		else:
			self.bresenham( ip, jp, i, j, k, xn, yn )

		xm /= c.NumberofContourPoints
		ym /= c.NumberofContourPoints
		
		i, j, k = self.nearestInside( xm, ym, z, c )
		if i != None:
			if self.debugPrint:
				print "before self.floodLevelFill: i,j,k=%d,%d,%d z=%f" % (i,j,k,z)
			filled = self.floodLevelFill( i, j, k, xn, yn )
			if self.valFlooded( k, xn, yn ) > 0.95:
				print "WARNING: level at z=%f was flooded! " % (z), "by contour ", c.ContourData, " started at %d,%d (%f,%f)" % (i,j,1000*(self.bbox[0]+i*self.res[0]),1000*(self.bbox[1]+j*self.res[1]))
				sys.exit(2)
		else:
			if not self.Quiet:
				print "Warning: no suitable seed point around centre of gravity (%f,%f)" % (1000*xm,1000*ym)
			filled = False
		return (i,j,k,xm,ym,z,filled)

	def fillFromLowestRightmost( self, c ):
		# Wypełnianie startujące z najniższego i najbardziej prawego wierzchołka
		filled = False
		xn, yn, zn = self.numberOfBoxes()
		v,xm,ym = self.lowestRightmost( c )
		pv = v-1 if v > 0 else c.NumberofContourPoints-1 # previous of v
		vn = v+1 if v < c.NumberofContourPoints-1 else 0 # next 
		px,py,z = self.cords( c, pv )
		nx,ny,z = self.cords( c, vn )
		if self.debugPrint:
			print "v,xm,ym=%d,%f,%f" % (v,xm,ym)
			print "prev=%d, next=%d" % (pv,vn)
		p = vn+1
		xi= None
		while True:
			if p == c.NumberofContourPoints:
				p = 0
			if p == pv:
				break
			x,y,z = self.cords( c, p )
			if self.insideTriangle( px, py, xm, ym, nx, ny, x, y ):
				if xi == None or (x-xm)*(x-xm)+(y-ym)*(y-ym) < m2:
					xi = x
					yi = y
					pi = p
					m2 = (x-xm)*(x-xm)+(y-ym)*(y-ym)
			p += 1
			#print p
		# end while
		if xi == None:
			if self.debugPrint:
				print "pi == none"
			xm= 0.5*(px+nx)
			ym= 0.5*(py+ny)
		else:
			if self.debugPrint:
				print "pi == %d" % (pi)
			xm= 0.5*(xm+xi)
			ym= 0.5*(ym+yi)
		i, j, k = self.nearestInside( xm, ym, z, c )
		if i != None:
			if self.debugPrint:
				print "xm,ym=%f,%f -> i,j,k=%d,%d,%d" % (xm,ym,i,j,k)
				print "before self.floodLevelFill: i,j,k=%d,%d,%d z=%f" % (i,j,k,z)
			filled = self.floodLevelFill( i, j, k, xn, yn )
			if self.valFlooded( k, xn, yn ) > 0.95:
				print "WARNING: level at z=%f was flooded! " % (z), "by contour ", c.ContourData, " started at %d,%d (%f,%f)" % (i,j,1000*(self.bbox[0]+i*self.res[0]),1000*(self.bbox[1]+j*self.res[1]))
				sys.exit(2)
		elif not self.Quiet:
			print "Warning: no suitable seed point around lowest-rightmost (%f,%f)" % (1000*xm,1000*ym)
		return (i,j,k,xm,ym,z,filled)

	def fillFromAnyCorner( self, c ):
                # start filling from near of a corner
		filled = False
		xn, yn, zn = self.numberOfBoxes()
		for p in range(c.NumberofContourPoints):
			xm,ym,z = self.cords(c, p )
			i, j, k = self.nearestInside( xm, ym, z, c )
			if i != None:
				if self.debugPrint:
					print "xm,ym=%f,%f -> i,j,k=%d,%d,%d" % (xm,ym,i,j,k)
					print "before self.floodLevelFill: i,j,k=%d,%d,%d z=%f" % (i,j,k,z)
				filled = self.floodLevelFill( i, j, k, xn, yn )
				if self.valFlooded( k, xn, yn ) > 0.95:
					print "WARNING: level at z=%f was flooded! " % (z), "by contour ", c.ContourData, " started at %d,%d (%f,%f)" % (i,j,1000*(self.bbox[0]+i*self.res[0]),1000*(self.bbox[1]+j*self.res[1]))
					sys.exit(2)
				break

		if not filled and not self.Quiet:
			print "Warning: no suitable seed points around corners"
		return (i,j,k,xm,ym,z,filled)

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

		allp = open('all.xml','w')
		print >>allp, '''<?xml version="1.0"?>
<dolfin xmlns:dolfin="http://fenicsproject.org">
<mesh celltype="tetrahedron" dim="3">
<vertices size="%d">''' % (self.vp.GetNumberOfPoints())
		for i in range(self.vp.GetNumberOfPoints()):
			p = [0.,0.,0.]
			self.vp.GetPoint(i,p)
			print >>allp, '<vertex index="%d" x="%f" y="%f" z="%f" />' % (i, p[0], p[1], p[2] )
		print >>allp, '''</vertices>
<cells size="0">
</cells>
</mesh>
</dolfin>
'''
	# end savePointsIfWanted

	# zwraca wspolrzedne x, y, z punktu o indeksie p z danych konturu c
	def cords(self, c, p):
		x = float(c.ContourData[3*p+0])
		y = float(c.ContourData[3*p+1])
		z = float(c.ContourData[3*p+2])
		return x, y, z

	# Funkcje dla sieci
	# xn, yn, zn - liczba szescianow wzdluz (odpowiednio) osi x, y, z
	def numberOfBoxes(self):
		xn = (self.bbox[3] - self.bbox[0])/self.res[0]
		yn = (self.bbox[4] - self.bbox[1])/self.res[1]
		zn = (self.bbox[5] - self.bbox[2])/self.res[2]
		return int(xn), int(yn), int(zn)

	# xi, yi, zi - indeks punktu wzdluz (odpowiednio) osi x, y, z
	def pointIndex(self, x, y, z):
		xi = (x - self.bbox[0] + self.res[0]/2)/self.res[0]
		yi = (y - self.bbox[1] + self.res[1]/2)/self.res[1]
		zi = (z - self.bbox[2] + self.res[2]/2)/self.res[2]
		return int(xi), int(yi), int(zi)
 
	# jednowymiarowy indeks punktu o współrzędnych calkowitych (xi,yi,zi) w siatce [0:xn]x[0:yn]x[0:zn]
	def pointNumber(self, xi, yi, zi, xn, yn):
		i = xi + yi * (xn+1) + zi * (xn+1)*(yn+1)
		return i

	# jednowymiarowy indeks wezla siatki opisanej przez bbox i res, najbliższego (x,y,z)
	def nearestPointNumber(self,  x, y, z):
		xi = int((x - self.bbox[0] + self.res[0]/2)/self.res[0])
		yi = int((y - self.bbox[1] + self.res[1]/2)/self.res[1])
		zi = int((z - self.bbox[2] + self.res[2]/2)/self.res[2])
		xn = int((self.bbox[3] - self.bbox[0])/self.res[0])
		yn = int((self.bbox[4] - self.bbox[1])/self.res[1])
		return xi + yi * (xn+1) + zi * (xn+1)*(yn+1)

	# xi, yi, zi - indeks szescianu wzdluz (odpowiednio) osi x, y, z
	def boxIndex(self, x, y, z):
		xi = (x - self.bbox[0])/self.res[0]
		yi = (y - self.bbox[1])/self.res[1]
		zi = (z - self.bbox[2])/self.res[2]
		return int(xi), int(yi), int(zi)

	# jednowymiarowy indeks szescianu o współrzędnych (xi,yi,zi) w siatce [0:xn-1]x[0:yn-1]x[0:zn-1]
	def boxNumber(self, xi, yi, zi, xn, yn, zn=0):
		i = xi + yi * (xn) + zi * (xn * yn)
		return i

	# zwraca identyfikator szescianu wygenerowanego wew. bounding box (bbox)
	# na podstawie wspolrzednych x, y, z
	def boxAt(self, x, y, z):
		xn, yn, zn = self.numberOfBoxes()
		xi, yi, zi = boxIndex(x, y, z)
		return boxNumber(xi, yi, zi, xn, yn, zn)

	# funkcja pomocnicza do nearestInside
	def goodMove(self,  di, dj, x, y, z, c ):
  		return self.inside( x+di*self.res[0], y+dj*self.res[1], c ) and self.val.GetValue(self.nearestPointNumber(x+di*self.res[0],y+dj*self.res[1],z)) != 1.0

	# najblizszy (x,y,z) punkt wewnątrz konturu c
	def nearestInside(self,  x, y, z, c ):
		xn,yn,zn = self.numberOfBoxes()
		i, j, k = self.pointIndex( x, y, z )
		x = self.bbox[0]+i*self.res[0]
		y = self.bbox[1]+j*self.res[1]

		if self.debugPrint:
			print "x,y,z=%f,%f,%f -> i,j,k=%d,%d,%d" % (x,y,z,i,j,k)
		if self.inside( x,y, c ) and self.val.GetValue(self.pointNumber(i,j,k,xn,yn)) != 1.0:
  			return (i,j,k)

		moves = [ (2,0),(2,2),(0,2),(-2,2),(-2,0),(-2,-2),(0,-2),(2,-2),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1) ] 
		for m in moves:
			if self.goodMove( m[0], m[1], x, y, z, c ):
				return (i+m[0],j+m[1],k)
		return (None,None,k)

	# sprawdza, czy cały poziom iz nie został przypadkiem wypełniony 1.0
	def valFlooded(self, iz, xn, yn ):
		c = 0
		for i in range(iz*(xn+1)*(yn+1),(iz+1)*(xn+1)*(yn+1)):
			if self.val.GetValue(i) == 1.0:
				c += 1
		ret= float(c)/((xn+1)*(yn+1))
		#print "level %d: filled %d out of %d, returning %f" % ( iz, c, (xn+1)*(yn+1), ret )
		return ret

	# f pomocnicza do alg Bresenhama
	def putPix(self,  x, y, lev, xn, yn):
		np = self.pointNumber(x, y, lev, xn, yn)
		self.val.InsertValue( np, 1.0 )
		point = [ 0.0, 0.0, 0.0 ]
		self.vp.GetPoint( np, point )
  		#print "%d %d %d -> %f %f %f" % ( x, y, lev, point[0], point[1], point[2] )
		if self.debugPoints:
			self.ctr.append( point )

	# Alg bresenhama do wypełniania wszystkich wezłow na konturze
	def bresenham(self,  x1, y1, x2, y2, lev, xn, yn ):
		x = x1
		y = y1
		if x1 < x2 :
			xi = 1
			dx = x2 - x1
		else:
			xi = -1
			dx = x1 - x2
		if y1 < y2:
			yi = 1
			dy = y2 -y1
		else:
			yi = -1
			dy = y1 -y2
		self.putPix( x, y, lev, xn, yn )
		if dx > dy:
			ai = (dy-dx)*2
			bi = dy*2
			d = bi - dx
			while x != x2:
				if d >= 0:
					x += xi
					y += yi
					d += ai
				else:
					d += bi
					x += xi
				self.putPix( x, y, lev, xn, yn )
		else:
			ai = (dx-dy)*2
			bi = dx*2
			d = bi - dy
			while y != y2:
				if d >= 0:
					x += xi
					y += yi
					d += ai
				else:
					d += bi
					y += yi
				self.putPix( x, y, lev, xn, yn )

	# Alg bresenhama do wypełniania wszystkich wezłow na konturze
	def continuousBresenham(self,  x1, y1, x2, y2, lev, xn, yn, cx1, cy1, cx2, cy2, cz, gr ):
		x = x1
		y = y1
		if x1 < x2 :
			xi = 1
			dx = x2 - x1
		else:
			xi = -1
			dx = x1 - x2
		if y1 < y2:
			yi = 1
			dy = y2 -y1
		else:
			yi = -1
			dy = y1 -y2
		self.putPix( x, y, lev, xn, yn )
		gr.GetPoints().SetPoint( self.pointNumber(x,y,lev,xn,yn), cx1, cy1, cz )
		if dx > dy:
			cdx = 0 if x2 == x1 else (cx2 - cx1)/(x2-x1)
			cdy = 0 if x2 == x1 else (cy2 - cy1)/(x2-x1)
			ai = (dy-dx)*2
			bi = dy*2
			d = bi - dx
			while x != x2:
				if d >= 0:
					x += xi
					y += yi
					d += ai
				else:
					x += xi
					d += bi
				self.putPix( x, y, lev, xn, yn )
				gr.GetPoints().SetPoint( self.pointNumber(x,y,lev,xn,yn), cx1+cdx*(x-x1), cy1+cdy*(x-x1), cz )
		else:
			cdx = 0 if y2 == y1 else (cx2 - cx1)/(y2-y1)
			cdy = 0 if y2 == y1 else (cy2 - cy1)/(y2-y1)
			ai = (dx-dy)*2
			bi = dx*2
			d = bi - dy
			while y != y2:
				if d >= 0:
					x += xi
					y += yi
					d += ai
				else:
					d += bi
					y += yi
				self.putPix( x, y, lev, xn, yn )
				gr.GetPoints().SetPoint( self.pointNumber(x,y,lev,xn,yn), cx1+cdx*(y-y1), cy1+cdy*(y-y1), cz )

	def floodLevelFill(self,  x, y, lev, xn, yn ):
		# UWAGA: to jest za wolne!
		if self.val.GetValue(self.pointNumber(x,y,lev,xn,yn)) == 1.0:
			if self.debugPrint:
				print "Bad seed (%d,%d,%d)" % (x,y,lev)
			return False
		Q = set()
		Q.add((x, y))
		while len(Q):
			#print len(Q)
			x, y = Q.pop()
			n = self.pointNumber(x, y, lev, xn, yn)
			if self.val.GetValue(n) == 0.0:
				w = e = x
				while w < xn+1 and self.val.GetValue(self.pointNumber(w+1, y, lev, xn, yn)) == 0.0:
					w += 1
				while e > 0 and self.val.GetValue(self.pointNumber(e-1, y, lev, xn, yn)) == 0.0:
					e -= 1
				#print "%d-%d,%d" % (e,w,y)
				nFlag= sFlag= False
				for i in range(e, w+1):
					self.putPix(i, y, lev, xn, yn)
					if y < yn+1:
						north = self.pointNumber(i, y+1, lev, xn, yn)
						if self.val.GetValue(north) == 0.0 and not nFlag:
							Q.add((i, y+1))
							nFlag = True
						else:
							nFlag = False
					if y > 0:
						south = self.pointNumber(i, y-1, lev, xn, yn)
						if self.val.GetValue(south) == 0.0 and not sFlag:
							Q.add((i, y-1))
							sFlag = True
						else:
							sFlag = False
		return True
        
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

	def insideTriangle(self, x0, y0, x1, y1, x2, y2, x, y ):
		# returns True if (x,y) is self.inside triangle 0-1-2
		v0x = x2 - x0
		v0y = y2 - y0
		v1x = x1 - x0
		v1y = y1 - y0
		v2x = x - x0
		v2y = y - y0
		dot00 = v0x*v0x + v0y*v0y
		dot01 = v0x*v1x + v0y*v1y
		dot02 = v0x*v2x + v0y*v2y
		dot11 = v1x*v1x + v1y*v1y
		dot12 = v1x*v2x + v1y*v2y
		den = dot00*dot11 - dot01*dot01
		if den < 1e-7:
			#print "Degenerated triangle: (%f,%f)-(%f,%f)-(%f,%f)" % (x0, y0, x1, y1, x2, y2)
			return False
		u = (dot11*dot02 - dot01*dot12) / den
		v = (dot00*dot12 - dot01*dot02) / den
		return u >= 0 and v >= 0 and u+v < 1

	def inside(self, x, y, c ):
		# returns True if (x,y) is self.inside c 
		# alg. from http://www.exaflop.org/docs/cgafaq/cga2.html
		cross = False
		xj,yj,z = self.cords( c, c.NumberofContourPoints-1)
		for i in range(c.NumberofContourPoints):
			xi,yi,z = self.cords(c,i)
			if (( yi <= y and y < yj ) or ( yj <= y and y < yi )) and ( x < xi + (xj-xi)*(y-yi)/(yj-yi) ):
				cross = not cross
			xj = xi
			yj = yi
		return cross;

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

  ex = ROIExtractor( st, res, debugPrint=debugPrint, debugGrid=debugGrid, debugPoints=debugPoints, beQuiet=False )
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


