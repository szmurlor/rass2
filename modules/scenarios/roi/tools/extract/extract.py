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

TODO:
Odczytywać rozdzielczość z pliku(ów) DICOM.
'''


import dicom
import sys
import vtk
from vtk.util.colors import *

# przesunięcie, żeby fiverowi było lepiej - trzeba przesunąć do xc,yc,zc podawanego przez program uruchomiony z
dx = dy = dz = 0.0

res = [0,0,0]
res[0] = 1.601/1000
res[1] = 1.601/1000
res[2] = 3.000/1000

# Funkcje dla konturów
# zwraca wspolrzedne x, y, z punktu o indeksie p z danych konturu c
def coords(c, p):
  x = c.ContourData[3*p+0] / 1000 - dx
  y = c.ContourData[3*p+1] / 1000 - dy
  z = c.ContourData[3*p+2] / 1000 - dz
  return x, y, z

# Funkcje dla sieci
# xn, yn, zn - liczba szescianow wzdluz (odpowiednio) osi x, y, z
def numberOfBoxes(bbox,res):
  xn = (bbox[3] - bbox[0])/res[0]
  yn = (bbox[4] - bbox[1])/res[1]
  zn = (bbox[5] - bbox[2])/res[2]
  return int(xn), int(yn), int(zn)

# xi, yi, zi - indeks punktu wzdluz (odpowiednio) osi x, y, z
def pointIndex(x, y, z, bbox, res):
  xi = (x - bbox[0] + res[0]/2)/res[0]
  yi = (y - bbox[1] + res[1]/2)/res[1]
  zi = (z - bbox[2] + res[2]/2)/res[2]
  return int(xi), int(yi), int(zi)
 
# jednowymiarowy indeks punktu o współrzędnych calkowitych (xi,yi,zi) w siatce [0:xn]x[0:yn]x[0:zn]
def pointNumber(xi, yi, zi, xn, yn):
  i = xi + yi * (xn+1) + zi * (xn+1)*(yn+1)
  return i

# jednowymiarowy indeks wezla siatki opisanej przez bbox i res, najbliższego (x,y,z)
def nearestPointNumber( x, y, z, bbox, res ):
  xi = int((x - bbox[0] + res[0]/2)/res[0])
  yi = int((y - bbox[1] + res[1]/2)/res[1])
  zi = int((z - bbox[2] + res[2]/2)/res[2])
  xn = int((bbox[3] - bbox[0])/res[0])
  yn = int((bbox[4] - bbox[1])/res[1])
  return xi + yi * (xn+1) + zi * (xn+1)*(yn+1)

# xi, yi, zi - indeks szescianu wzdluz (odpowiednio) osi x, y, z
def boxIndex(x, y, z, bbox, res):
  xi = (x - bbox[0])/res[0]
  yi = (y - bbox[1])/res[1]
  zi = (z - bbox[2])/res[2]
  return int(xi), int(yi), int(zi)

# jednowymiarowy indeks szescianu o współrzędnych (xi,yi,zi) w siatce [0:xn-1]x[0:yn-1]x[0:zn-1]
def boxNumber(xi, yi, zi, xn, yn, zn=0):
  i = xi + yi * (xn) + zi * (xn * yn)
  return i

# zwraca identyfikator szescianu wygenerowanego wew. bounding box (bbox)
# na podstawie wspolrzednych x, y, z
def boxAt(x, y, z, bbox, res):
  xn, yn, zn = numberOfBoxes(bbox,res)
  xi, yi, zi = boxIndex(x, y, z, bbox, res)
  return boxNumber(xi, yi, zi, xn, yn, zn)

# funkcja pomocnicza do nearestInside
def goodMove( di, dj, x, y, z, c, bbox, res, val ):
  return inside( x+di*res[0], y+dj*res[1], c ) and val.GetValue(nearestPointNumber(x+di*res[0],y+dj*res[1],z,bbox,res)) != 1.0

# najblizszy (x,y,z) punkt wewnątrz konturu c
def nearestInside( x, y, z, c, bbox, res, val ):
  # trzeba to przepisać ładniej! ##########################################################
  xn,yn,zn = numberOfBoxes(bbox,res)
  i, j, k = pointIndex( x, y, z, bbox, res )
  x = bbox[0]+i*res[0]
  y = bbox[1]+j*res[1]
  if debugPrint:
    print "x,y,z=%f,%f,%f -> i,j,k=%d,%d,%d" % (x,y,z,i,j,k)
  if inside( x,y, c ) and val.GetValue(pointNumber(i,j,k,xn,yn)) != 1.0:
    return (i,j,k)

  moves = [ (2,0),(2,2),(0,2),(-2,2),(-2,0),(-2,-2),(0,-2),(2,-2),(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1) ] 
  for m in moves:
    if goodMove( m[0], m[1], x, y, z, c, bbox, res, val ):
      return (i+m[0],j+m[1],k)
  return (None,None,k)
'''
  elif inside( x+res[0], y, c ) and val.GetValue(nearestPointNumber(x+res[0],y,z,bbox,res)) != 1.0:  # +0
    return (i+1,j,k)
  elif inside( x+res[0], y+res[1], c) and val.GetValue(nearestPointNumber(x+res[0],y+res[1],z,bbox,res)) != 1.0: # ++
    return (i+1,j+1,k)
  elif inside( x, y+res[1] and val.GetValue(nearestPointNumber(x,y+res[1],z,bbox,res)) != 1.0, c ): # 0+
    return (i,j+1,k)
  elif inside( x-res[0], y+res[1], c ) and val.GetValue(nearestPointNumber(x-res[0],y+res[1],z,bbox,res)) != 1.0: # -+
    return (i-1,j+1,k)
  elif inside( x-res[0], y, c ) and val.GetValue(nearestPointNumber(x-res[0],y,z,bbox,res)) != 1.0: # -0
    return (i-1,j,k)
  elif inside( x-res[0], y-res[1], c ) and val.GetValue(nearestPointNumber(x-res[0],y-res[1],z,bbox,res)) != 1.0: # --
    return (i-1,j-1,k)
  elif inside( x, y-res[1], c ) and val.GetValue(nearestPointNumber(x,y-res[1],z,bbox,res)) != 1.0: # 0-
    return (i,j-1,k)
  elif inside( x+res[0], y-res[1], c ) and val.GetValue(nearestPointNumber(x+res[0],y-res[1],z,bbox,res)) != 1.0: # +-
    return (i+1,j-1,k)
  else:
    return (None,None,k)
'''

# sprawdza, czy cały poziom iz nie został przypadkiem wypełniony 1.0
def valFlooded( iz, xn, yn, val ):
  c = 0
  for i in range(iz*(xn+1)*(yn+1),(iz+1)*(xn+1)*(yn+1)):
    if val.GetValue(i) == 1.0:
      c += 1
  ret= float(c)/((xn+1)*(yn+1))
  #print "level %d: filled %d out of %d, returning %f" % ( iz, c, (xn+1)*(yn+1), ret )
  return ret

# f pomocnicza do alg Bresenhama
def putPix( x, y, lev, xn, yn, val, ctr):
  np = pointNumber(x, y, lev, xn, yn)
  val.InsertValue( np, 1.0 )
  point = [ 0.0, 0.0, 0.0 ]
  vp.GetPoint( np, point )
  #print "%d %d %d -> %f %f %f" % ( x, y, lev, point[0], point[1], point[2] )
  ctr.append( point )

# Alg bresenhama do wypełniania wszystkich wezłow na konturze
def bresenham( x1, y1, x2, y2, lev, xn, yn, val, ctr ):
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
  putPix( x, y, lev, xn, yn, val, ctr )
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
      putPix( x, y, lev, xn, yn, val, ctr )
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
      putPix( x, y, lev, xn, yn, val, ctr )

# wypełnianie - złe jest, bo nie radzi sobie z koncówkami obszaru składającymi się s poj. pixeli
# trzeba zobić flood-fill po zamknieciu konturu
def levelFill( lev, xn, yn, val, ctr ):
  print "Filling %f" % lev
  for y in range(yn+1):
    points = 0
    inside = False
    for x in range(xn+1):
      n = pointNumber(x, y, lev, xn, yn)
      if val.GetValue(n) == 1.0:
        points += 1
    if points % 2 != 0:
      print "%d points in coord y=%f, z=%f" % (points, y, lev)
      continue
    for x in range(xn+1):
      n = pointNumber(x, y, lev, xn, yn)
      if val.GetValue(n) == 1.0:
        inside = not inside
      if inside:
          print "Putting pixel %f, %f, %f" % (x, y, lev)
          putPix( x, y, lev, xn, yn, val, ctr ) # will do val.setValue(n,1.0)

def floodLevelFill( x, y, lev, xn, yn, val, ctr ):
  if val.GetValue(pointNumber(x,y,lev,xn,yn)) == 1.0:
    print "Bad seed (%d,%d,%d)" % (x,y,lev)
    return False
  Q = []
  Q.append((x, y))
  while len(Q):
    x, y = Q.pop()
    n = pointNumber(x, y, lev, xn, yn)
    if val.GetValue(n) == 0.0:
      w = e = x
      while w < xn+1 and val.GetValue(pointNumber(w+1, y, lev, xn, yn)) == 0.0:
        w += 1
      while e > 0 and val.GetValue(pointNumber(e-1, y, lev, xn, yn)) == 0.0:
        e -= 1
      #print "%d-%d,%d" % (e,w,y)
      for i in range(e, w+1):
        putPix(i, y, lev, xn, yn, val, ctr)
      if y < yn+1:
        for i in range(e,w+1):
	  north = pointNumber(i, y+1, lev, xn, yn)
	  if val.GetValue(north) == 0.0:
	    Q.append((i, y+1))
      if y > 0:
        for i in range(e,w+1):
	  south = pointNumber(i, y-1, lev, xn, yn)
	  if val.GetValue(south) == 0.0:
	    Q.append((i, y-1))
  return True
        
def floodFill( x, y, lev, xn, yn, val, ctr ):
  base = lev*(xn+1)*(yn+1)
  Q = []
  Q.append((x, y))
  while len(Q):
    x, y = Q.pop()
    n = pointNumber(x, y, lev, xn, yn)
    if val.GetValue(n) == 1.0:
      putPix(x, y, lev, xn, yn, val, ctr)
      Q.append((x+1, y+0))
      Q.append((x+0, y-1))
      Q.append((x-1, y+0))
      Q.append((x+0, y+1))
      #Q.append((x+1, y-1))
      #Q.append((x-1, y-1))
      #Q.append((x-1, y+1))
      #Q.append((x+1, y+1))
  return

def crossProduct( x0,y0, x1,y1, x2,y2 ):
  # cross product of 0-1 and 2-1 vectors
  return (x2-x1)*(y0-y1) - (x0-x1)*(y2-y1)

def lowestRightmost( c ):
  # calculates lowest,rightmost vertex of contour c
  xl,yl,z = coords( c, 0 )
  pl = 0
  for p in range(1,c.NumberofContourPoints):
    x,y,z = coords( c, p )
    if y < yl or y == yl and x > xl:
      xl = x
      yl = y
      pl = p
  return (pl, xl, yl ) 

def contourOrientedClockwise( c ):
  # returns True if c is oriented clockwise, False otherwise
  v,x,y = lowestRightmost( c )
  pv = v-1 if v > 0 else c.NumberofContourPoints-1 # previous of v
  vn = v+1 if v < c.NumberofContourPoints-1 else 0 # next 
  xp,yp,z = coords( c, pv )
  xn,yn,z = coords( c, vn )
  return crossProduct( xp,yp, x,y, xn, yn ) < 0 

def insideTriangle( x0, y0, x1, y1, x2, y2, x, y ):
  # returns True if (x,y) is inside triangle 0-1-2
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

def inside( x, y, c ):
  # returns True if (x,y) is inside c 
  # alg. from http://www.exaflop.org/docs/cgafaq/cga2.html
  cross = False
  xj,yj,z = coords( c, c.NumberofContourPoints-1)
  for i in range(c.NumberofContourPoints):
    xi,yi,z = coords(c,i)
    if (( yi <= y and y < yj ) or ( yj <= y and y < yi )) and ( x < xi + (xj-xi)*(y-yi)/(yj-yi) ):
      cross = not cross
    xj = xi
    yj = yi
  return cross;

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
  roiname = sys.argv[2]
  for r in st.StructureSetROIs:
    if r.ROIName == roiname:
      roi = r.ROINumber
  if roi == None:
    print roiname, " not found!"
    sys.exit(1)

  first= last= -1
  for i in range(3,len(sys.argv)-1):
    if sys.argv[i] == '-l':
	first, last = map(lambda s: int(s), sys.argv[i+1].split(':') )

  for i in range(3,len(sys.argv)-1):
    if sys.argv[i] == '-r':
	res[0], res[1], res[2] = map(lambda s: float(s), sys.argv[i+1].split(':') )
        print "Resolution changed to [%f %f %f]" % ( res[0], res[1], res[2] )

  for i in range(3,len(sys.argv)-1):
    if sys.argv[i] == '-t':
	dx, dy, dz = map(lambda s: float(s), sys.argv[i+1].split(':') )
        print "Translation by [%f %f %f]" % ( dx, dy, dz )

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

  co = None
  for r in st.ROIContours:
    if r.RefdROINumber == roi:
      co = r
  # tworze bounding box i licze wszystkie punkty
  bbox = [1000, 1000, 1000, -1000, -1000, -1000]
  npoints = 0
  centrOfGrav = [0.0,0.0,0.0]
  for c in co.Contours:
    npoints += c.NumberofContourPoints
    # test code
    if debugPrint:
      print c.ContourData
      print "Contour oriented " + ( "clockwise" if contourOrientedClockwise( c ) else "counter-clockwise" )
      if c.NumberofContourPoints < 10:
        for p in range(c.NumberofContourPoints):
          print coords(c,p)
      else:
        print c.NumberofContourPoints
    # end of test code
    for p in range(c.NumberofContourPoints):
      x, y, z = coords(c, p)
      bbox[0] = x if x < bbox[0] else bbox[0]
      bbox[1] = y if y < bbox[1] else bbox[1]
      bbox[2] = z if z < bbox[2] else bbox[2]
      bbox[3] = x if x > bbox[3] else bbox[3]
      bbox[4] = y if y > bbox[4] else bbox[4]
      bbox[5] = z if z > bbox[5] else bbox[5]
      centrOfGrav[0] += x
      centrOfGrav[1] += y
      centrOfGrav[2] += z

  centrOfGrav[0] /= npoints
  centrOfGrav[1] /= npoints
  centrOfGrav[2] /= npoints

  # zabezpieczenie przed "dziurami" na krancach"
  bbox[0] -= 2*res[0]
  bbox[1] -= 2*res[1]
  bbox[3] += 2*res[0]
  bbox[4] += 2*res[1]

  # specjalnie po z - tylko przed pierwszym lub po ostatnim
  bbox[2] -= 2*res[2]
  if first > 0:
    bbox[2] += first*res[2]

  if last <= 0:
    bbox[5] += 2*res[2]
  else:
    bbox[5] = bbox[2] + res[2] * (last-first)

  if dx == 0.0 and dy == 0.0 and dz == 0.0:
    print "BBox center: %f %f %f" % ((bbox[0]+bbox[3])/2, (bbox[1]+bbox[4])/2, (bbox[2]+bbox[5])/2)
  
  # tworze siatke VTK
  # voxel points
  xn, yn, zn = numberOfBoxes(bbox,res)
  first = 0 if first == -1 else first
  last = zn if last == -1 else last
  print "Slices: %d-%d -> z in (%f,%f)" % ( first, last, bbox[2], bbox[5] )
  print "BBox: [%f,%f]x[%f,%f]x[%f,%f]" % ( bbox[0], bbox[3], bbox[1], bbox[4], bbox[2], bbox[5] )
  print "Center of gravity: (%f,%f,%f)" % ( centrOfGrav[0], centrOfGrav[1], centrOfGrav[2] )
  print "Res: %s" % res
  print "Grid size: %dx%dx%d cubes" % (xn, yn, zn)
  vp  = vtk.vtkPoints()
  val = vtk.vtkFloatArray()

  if debugPrint:
    print "x: ", map( lambda i: bbox[0]+i*res[0], range(xn+1) )
    print "y: ", map( lambda i: bbox[1]+i*res[1], range(yn+1) )
    print "z: ", map( lambda i: bbox[2]+i*res[2], range(zn+1) )

  for zi in range(zn+1):
    for yi in range(yn+1):
      for xi in range(xn+1):
        vp.InsertNextPoint( bbox[0]+xi*res[0], bbox[1]+yi*res[1], bbox[2]+zi*res[2] )
        val.InsertNextValue(0.0)
  gr = vtk.vtkUnstructuredGrid()
  gr.Allocate(xn*yn*zn,10)
  for zi in range(zn):
    for yi in range(yn):
      for xi in range(xn):
        ids = vtk.vtkIdList()
        ids.InsertNextId( pointNumber(xi  , yi  , zi  , xn, yn) )
        ids.InsertNextId( pointNumber(xi+1, yi  , zi  , xn, yn) )
        ids.InsertNextId( pointNumber(xi+1, yi+1, zi  , xn, yn) )
        ids.InsertNextId( pointNumber(xi  , yi+1, zi  , xn, yn) )
        ids.InsertNextId( pointNumber(xi  , yi  , zi+1, xn, yn) )
        ids.InsertNextId( pointNumber(xi+1, yi  , zi+1, xn, yn) )
        ids.InsertNextId( pointNumber(xi+1, yi+1, zi+1, xn, yn) )
        ids.InsertNextId( pointNumber(xi  , yi+1, zi+1, xn, yn) )
	gr.InsertNextCell(12,ids)
  gr.SetPoints(vp)
  ctr = []
  for c in co.Contours:
    xp, yp, zp = coords(c, 0)
    if zp < bbox[2]-0.01*res[2] or zp > bbox[5]+0.01*res[2]:
      if debugPrint:
        print "%f not in (%f : %f)" % ( zp, bbox[2], bbox[5] )
      continue
    ip, jp, kp = pointIndex(xp, yp, zp, bbox, res)
    xm, ym = xp, yp # fllod seed calculated as centre of gravity
    for p in range(1,c.NumberofContourPoints):
      x, y, z = coords(c, p)
      i, j, k = pointIndex(x, y, z, bbox, res)  # to jest chyba źle, bo z obcięciem, a nie zaokrągleniem float->int
      xm += x
      ym += y
      if k != kp:
        print "Error in contour ", c
        print "Points no. %d and %d have different z-coordinates!" % ( p-1, p )
        sys.exit(1)
      bresenham( ip, jp, i, j, k, xn, yn, val, ctr )
      ip = i
      jp = j
      kp = k
    x, y, z = coords(c, 0)
    i, j, k = pointIndex(x, y, z, bbox, res)
    bresenham( ip, jp, i, j, k, xn, yn, val, ctr )

    xm /= c.NumberofContourPoints
    ym /= c.NumberofContourPoints
    
    i, j, k = nearestInside( xm, ym, z, c, bbox, res, val )
    if i != None:
      if debugPrint:
        print "before floodLevelFill: i,j,k=%d,%d,%d z=%f" % (i,j,k,z)
      filled = floodLevelFill( i, j, k, xn, yn, val, ctr )
      if valFlooded( k, xn, yn, val ) > 0.95:
        print "WARNING: level at z=%f was flooded! " % (z), "by contour ", c.ContourData, " started at %d,%d (%f,%f)" % (i,j,1000*(bbox[0]+i*res[0]),1000*(bbox[1]+j*res[1]))
    else:
      print "Warning: no suitable seed point around centre of gravity (%f,%f)" % (1000*xm,1000*ym)
      filled = False

    # a tu pomysł z najniższym wierzchołkiem z prawej
    if not filled:
      v,xm,ym = lowestRightmost( c )
      pv = v-1 if v > 0 else c.NumberofContourPoints-1 # previous of v
      vn = v+1 if v < c.NumberofContourPoints-1 else 0 # next 
      px,py,z = coords( c, pv )
      nx,ny,z = coords( c, vn )
      if debugPrint:
        print "v,xm,ym=%d,%f,%f" % (v,xm,ym)
        print "prev=%d, next=%d" % (pv,vn)
      p = vn+1
      xi= None
      while True:
        if p == c.NumberofContourPoints:
          p = 0
        if p == pv:
          break
        x,y,z = coords( c, p )
        if insideTriangle( xp, yp, xm, ym, xn, yn, x, y ):
	  if xi == None or (x-xm)*(x-xm)+(y-ym)*(y-ym) < m2:
            xi = x
            yi = y
            pi = p
            m2 = (x-xm)*(x-xm)+(y-ym)*(y-ym)
        p += 1
        #print p
      # end while
      if xi == None:
        if debugPrint:
          print "pi == none"
        xm= 0.5*(px+nx)
        ym= 0.5*(py+ny)
      else:
        if debugPrint:
          print "pi == %d" % (pi)
        xm= 0.5*(xm+xi)
        ym= 0.5*(ym+yi)
      i, j, k = nearestInside( xm, ym, z, c, bbox, res, val )
      if i != None:
        if debugPrint:
          print "xm,ym=%f,%f -> i,j,k=%d,%d,%d" % (xm,ym,i,j,k)
          print "before floodLevelFill: i,j,k=%d,%d,%d z=%f" % (i,j,k,z)
        filled = floodLevelFill( i, j, k, xn, yn, val, ctr )
        if valFlooded( k, xn, yn, val ) > 0.95:
          print "WARNING: level at z=%f was flooded! " % (z), "by contour ", c.ContourData, " started at %d,%d (%f,%f)" % (i,j,1000*(bbox[0]+i*res[0]),1000*(bbox[1]+j*res[1]))
      else:
        print "Warning: no suitable seed point around lowest-rightmost (%f,%f)" % (1000*xm,1000*ym)
    #koniec pomysłu w wierzchołkiem dolnym z prawej

    # pomysł ze sprawdzaniem wszystkich wierzchołków
    if not filled:
      for p in range(c.NumberofContourPoints):
        xm,ym,z = coords(c, p )
        i, j, k = nearestInside( xm, ym, z, c, bbox, res, val )
        if i != None:
          if debugPrint:
            print "xm,ym=%f,%f -> i,j,k=%d,%d,%d" % (xm,ym,i,j,k)
            print "before floodLevelFill: i,j,k=%d,%d,%d z=%f" % (i,j,k,z)
          filled = floodLevelFill( i, j, k, xn, yn, val, ctr )
          if valFlooded( k, xn, yn, val ) > 0.95:
            print "WARNING: level at z=%f was flooded! " % (z), "by contour ", c.ContourData, " started at %d,%d (%f,%f)" % (i,j,1000*(bbox[0]+i*res[0]),1000*(bbox[1]+j*res[1]))
          break
      if not filled:
        print "Warning: no suitable seed points around corners"


    if not filled:
      if i == None:
        print "Warning: unable to fill contour ", c.ContourData, " at slice # %d (z=%f mm) - no suitable seed point around (%f,%f) (This happens for small contours filled by the boundary itself.)" % (k,1000*z,1000*xm,1000*ym)
      else:
        print "Warning: unable to fill contour ", c.ContourData, " at slice # %d (z=%f mm) with seed at (%f,%f)" % (k,1000*z, 1000*(bbox[0]+i*res[0]), 1000*(bbox[1]+j*res[1]))
    else:
      print "Finished contour at slice # %d (z=%f mm)" % (k, 1000*z)
    # do skasowania po uruchomieniu
    #for kk in range(k):
    #  if valFlooded( kk, xn, yn, val ) > 0.95:
    #    print "WARNING: slice # %d (z=%f mm) was flooded in more than 95 %%!" % (kk,1000*(bbox[2]+kk*res[2]))

    
  gr.GetPointData().SetScalars(val)

  if debugPoints:
    ctrf = open('ctr.xml','w')
    print >>ctrf, '''<?xml version="1.0"?>
<dolfin xmlns:dolfin="http://fenicsproject.org">
<mesh celltype="tetrahedron" dim="3">
<vertices size="%d">''' % (len(ctr))
    for i in range(len(ctr)):
      print >>ctrf, '<vertex index="%d" x="%f" y="%f" z="%f" />' % (i, ctr[i][0], ctr[i][1], ctr[i][2] )
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
<vertices size="%d">''' % (vp.GetNumberOfPoints())
    for i in range(vp.GetNumberOfPoints()):
      p = [0.,0.,0.]
      vp.GetPoint(i,p)
      print >>allp, '<vertex index="%d" x="%f" y="%f" z="%f" />' % (i, p[0], p[1], p[2] )
    print >>allp, '''</vertices>
<cells size="0">
</cells>
</mesh>
</dolfin>
'''

  if debugGrid:
    wr = vtk.vtkXMLUnstructuredGridWriter()
    wr.SetFileName('grid.vtu')
    wr.SetDataModeToAscii()
    wr.SetInput( gr )
    wr.Write()

  marching = vtk.vtkContourFilter()
  marching.SetInput(gr)
  marching.SetValue(0, 0.5)
  marching.Update()

  if debugPrint:
    print marching.GetOutputDataObject(0)

  if polyData:
    w = vtk.vtkPolyDataWriter()
    w.SetInput(marching.GetOutput())
    w.SetFileName(roiname+".vtk")
    w.Write()
    print roiname+".vtk written"

  if writeSTL:
    stl = vtk.vtkSTLWriter()
    stl.SetFileName(roiname+".stl")
    stl.SetInputConnection(marching.GetOutputPort())
    stl.Write()
    print roiname+".stl written"

  if writePLY:
    ply = vtk.vtkPLYWriter()
    ply.SetFileName(roiname+".ply")
    ply.SetInputConnection(marching.GetOutputPort())
    ply.Write()
    print roiname+".ply written"

  if decimate:
    dec = vtk.vtkQuadricClustering()
    dec.SetNumberOfXDivisions(secX)
    dec.SetNumberOfYDivisions(secY)
    dec.SetNumberOfZDivisions(secZ)
    dec.SetInput(marching.GetOutputDataObject(0))

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
    aShrinker.SetInputConnection(marching.GetOutputPort())
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


