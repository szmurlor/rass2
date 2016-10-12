#! /usr/bin/python
# -*- coding: utf-8
help = \
'''
Modyfikuje (dodaje zmodyfikowaną kopię) wskazany ROI we wskazanym pliku DICOM.

Uwaga: jeśli nie zostanie podana żadna transformacja, to DICOM nie będzie modyfikowany.
       ale może zostać dokonana ekstrakcja (i ewentualna wizualizacja 3D i/lub zapis do pliku)
       wskazanego ROI. Nie trzeba wtedy podawać nazwy nowego ROI.

   Użycie: 
     [python] %s plik-dicom nazwa-ROIName [ nazwa-nowego-ROI ] [ opcje ]

   Opcje:
     -h - wyświetlenie opisu (domyślne zachowanie także przy braku argumentów wywołania)

    Parametry wpływające na ekstrakcję:
     -r rx:ry:rz - określenie rozdzielczości (domyślna rozdzielczość jest równa tej z plików DICOM)
     -discrete - użyj równomiernej siatki sześciennej (domyślnie siatka jest przyciągana do konturów)
     -treshold treshVal - użyj wartości treshVal jako progu do wyznaczenia granicy ROI
                          (dozwolone wartości: (0:1), domyślnie 0.5, mała wartość rozszerza ROI, duża - zawęża)
     -l od:do - przetwarzanie tylko fragmentu ROI: od i do to numery przekrojów
     -sqc nx:ny[:nz] - uproszczenie powierzchni ROI (vtkQuadricClustering), argument to liczby podziałów po x,y i z 
                       UWAGA: to nie działa najlepiej - radzimy nie używać!
     -smooth [nit:bp] - wygładzenie powierzchni ROI przez alg."windowed sinc function interpolation kernel";
                      argument to liczba iteracji (domyślnie 15) i współczynnik Band Pass (domyślnie 0.05);
                      współczynnik Band Pass jest mnożony przez min(rx,ry,rz) (patrz opcja -r)
      Przy włączeniu sqc i smooth najpierw wykonywany jest klastering, a następnie wygładzanie.

    Parametry wpływające na zapis wyników:
     -vtk - zapisz wynik w formacie vtk (pliki ROIName.vtk i new-ROIName.vtk)
     -ply - zapisz wynik w formacie ply (pliki ROIName.ply i new-ROIName.ply)
     -stl - zapisz wynik w formacie stl (pliki ROIName.stl i new-ROIName.stl)
     -png nazwa - zapisz wynik w formacie PNG - zrzut okna graficznego do pliku nazwa.png
            (uwaga: zrzuty okna można też wykonywać w trybie interaktywnym przez naciśniecie klawisza z w oknie vtk)

    Transformacje:
     -tr tx:ty:tz - translacja
     -rot ax:ay:az - obrót wokół osi (X,Y,Z) w globalnym ukł. wsp. (kąty w stopniach)
     -loc_rot ax:ay:az - obrót wokół osi (X,Y,Z) w ukł. wsp. zaczepionym w środku ciężkości ROI (kąty w stopniach)

    Określenie przekrojów - uwaga - użycie jednej z tych opcji zamazuje domyślną listę przekrojów wyznaczaną z BBox ROI:
     -slicelist z1:..zk - zadanie listy ze współrzędnymi przekrojów
     -slicealg z1:dz:n - zadanie algorytmu generacji przekrójów: z1,z1+dz,z1+2*dz, ...., z1+(n-1)*dz

    Parametry nowego ROI dopisywanego do pliku DICOM:
     -color r:g:b - ustawienie koloru, którym zostanie zaznaczony nowy ROI

    Debugging:
     -d grid:points:print:all - zapisz sieć (grid), wypisz punkty (points), wypisuj, co robisz (print)
     -v - wizualizuj wynik (vtk)

Uwaga: użycie opcji -v i/lub -png wymaga dostępu do servera XWindow.

'''


import dicom
import sys
import vtk
from vtk.util.colors import *
from extractor import ROIExtractor
from PLYtransformer import TransformPolyData
from PLYzcutter import PolyDataSetToContours
from digRS import resForROIPersistent
from addORdelROI import addROI

def savePLY( pd, filename ):
    ply = vtk.vtkPLYWriter()
    ply.SetFileName( filename+".ply")
    ply.SetInput(pd)
    ply.Write()
    print filename+".ply zapisany"

def saveSTL(pd,filename):
    stl = vtk.vtkSTLWriter()
    stl.SetFileName(filename+".stl")
    stl.SetInput(pd)
    stl.Write()
    print filename+".stl zapisany"

def saveVTK( pd, filename ):
    w = vtk.vtkPolyDataWriter()
    w.SetFileName(filename+".vtk")
    w.SetInput(pd)
    w.Write()
    print filename+".vtk zapisany"

def showPolyData( pdlist, contours=[], colors=[ green, banana, orange, tomato, red ], interactive=True, dumpPNG=False, namePNG='roidump', ax_origin = [0,0,0], ax_length=20, ax_font_size=20, ax_font_color=black ):
  global noShots
  actors = []

  if ax_length != 0:
    axes = vtk.vtkAxesActor()
    axtrans = vtk.vtkTransform()
    axtrans.Translate( ax_origin )
    axes.SetUserTransform( axtrans )
    axes.SetTotalLength( ax_length, ax_length, ax_length )
    axes.SetNormalizedLabelPosition( 0.75, 0.75, 0.75 )
    axes.GetXAxisCaptionActor2D().GetTextActor().SetTextScaleMode(vtk.vtkTextActor.TEXT_SCALE_MODE_NONE)
    axes.GetXAxisCaptionActor2D().GetTextActor().GetTextProperty().SetFontSize(ax_font_size)
    axes.GetXAxisCaptionActor2D().GetTextActor().GetTextProperty().SetColor(ax_font_color)
    axes.GetYAxisCaptionActor2D().GetTextActor().SetTextScaleMode(vtk.vtkTextActor.TEXT_SCALE_MODE_NONE)
    axes.GetYAxisCaptionActor2D().GetTextActor().GetTextProperty().SetFontSize(ax_font_size)
    axes.GetYAxisCaptionActor2D().GetTextActor().GetTextProperty().SetColor(ax_font_color)
    axes.GetZAxisCaptionActor2D().GetTextActor().SetTextScaleMode(vtk.vtkTextActor.TEXT_SCALE_MODE_NONE)
    axes.GetZAxisCaptionActor2D().GetTextActor().GetTextProperty().SetFontSize(ax_font_size)
    axes.GetZAxisCaptionActor2D().GetTextActor().GetTextProperty().SetColor(ax_font_color)
    actors.append( axes )

  for i,pd in enumerate(pdlist):
    shrinker = vtk.vtkShrinkPolyData()
    shrinker.SetShrinkFactor(0.9)
    shrinker.SetInput(pd)
    mapper = vtk.vtkPolyDataMapper()
    mapper.ScalarVisibilityOff()
    mapper.SetInputConnection(shrinker.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetDiffuseColor( colors[ i%len(colors)] )
    actor.GetProperty().SetOpacity(.6)
    actors.append( actor )

  for i,c in enumerate(contours):
    pts = vtk.vtkPoints()
    aSplineX = vtk.vtkCardinalSpline()
    aSplineY = vtk.vtkCardinalSpline()
    aSplineZ = vtk.vtkCardinalSpline()
    for i in range(len(c)/3):
      pts.InsertNextPoint( c[3*i], c[3*i+1], c[3*i+2] )
      aSplineX.AddPoint(i, c[i*3] )
      aSplineY.AddPoint(i, c[i*3+1] )
      aSplineZ.AddPoint(i, c[i*3+2] )
    numberOfInputPoints = int(len(c)/3)

    inputData = vtk.vtkPolyData()
    inputData.SetPoints(pts)
    balls = vtk.vtkSphereSource()
    balls.SetRadius(.25)
    balls.SetPhiResolution(10)
    balls.SetThetaResolution(10)
    glyphPoints = vtk.vtkGlyph3D()
    glyphPoints.SetInput(inputData)
    glyphPoints.SetSource(balls.GetOutput())
    glyphMapper = vtk.vtkPolyDataMapper()
    glyphMapper.SetInputConnection(glyphPoints.GetOutputPort())
    glyph = vtk.vtkActor()
    glyph.SetMapper(glyphMapper)
    glyph.GetProperty().SetDiffuseColor(yellow_ochre)
    glyph.GetProperty().SetSpecular(.3)
    glyph.GetProperty().SetSpecularPower(30)
    actors.append(glyph)

    # Generate the polyline for the spline.
    points = vtk.vtkPoints()
    profileData = vtk.vtkPolyData()
    # Number of points on the spline
    numberOfOutputPoints = 100
    # Interpolate x, y and z by using the three spline filters and
    # create new points
    for i in range(numberOfOutputPoints):
        t = (numberOfInputPoints-1.0)/(numberOfOutputPoints-1.0)*i
        points.InsertPoint(i, aSplineX.Evaluate(t), aSplineY.Evaluate(t), aSplineZ.Evaluate(t) )
    # Create the polyline.
    lines = vtk.vtkCellArray()
    lines.InsertNextCell(numberOfOutputPoints)
    for i in range(0, numberOfOutputPoints):
        lines.InsertCellPoint(i)
    profileData.SetPoints(points)
    profileData.SetLines(lines)
    # Add thickness to the resulting line.
    profileTubes = vtk.vtkTubeFilter()
    profileTubes.SetNumberOfSides(8)
    profileTubes.SetInput(profileData)
    profileTubes.SetRadius(.1)
    profileMapper = vtk.vtkPolyDataMapper()
    profileMapper.SetInputConnection(profileTubes.GetOutputPort())
    profile = vtk.vtkActor()
    profile.SetMapper(profileMapper)
    profile.GetProperty().SetDiffuseColor(wheat)
    profile.GetProperty().SetSpecular(.3)
    profile.GetProperty().SetSpecularPower(30)
    actors.append( profile )

  # Create the Renderer, RenderWindow, and RenderWindowInteractor
  ren = vtk.vtkRenderer()
  renWin = vtk.vtkRenderWindow()
  renWin.AddRenderer(ren)
  renWin.SetSize(800, 600)
  iren = vtk.vtkRenderWindowInteractor()
  iren.SetRenderWindow(renWin)

  # Add the actors to the renderer
  for a in actors:
    ren.AddActor(a)

  # Set the background color.
  ren.SetBackground(slate_grey)

  # Position the camera.
  ren.ResetCamera()
  #ren.GetActiveCamera().Dolly(1.2)
  ren.GetActiveCamera().Elevation(-65)
  ren.GetActiveCamera().Azimuth(30)
  ren.GetActiveCamera().Roll(-30)
  ren.ResetCameraClippingRange()

  def writePNG( name ):
    if False:    # vtkRenderLargeImage nie pokazuje osi układu współrzędnych
      imgRen = vtk.vtkRenderLargeImage()
      imgRen.SetInput(ren)
      #imgRen.SetMagnification(2)
    else:
      imgRen = vtk.vtkWindowToImageFilter()
      imgRen.SetInput(renWin)
    writer = vtk.vtkPNGWriter()
    writer.SetInputConnection(imgRen.GetOutputPort())
    writer.SetFileName( name )
    writer.Write()

  noShots = 0
  def windowCharEventCallback( obj, event ):
    global noShots
    #print obj.GetKeyCode(), "pressed"
    if obj.GetKeyCode() == 'z':
      filename = "screenshot%d.png" % (noShots,)
      writePNG( filename )
      noShots += 1
    elif obj.GetKeyCode() == '?':
      cam = ren.GetActiveCamera()
      print cam

  iren.AddObserver( "KeyPressEvent", windowCharEventCallback )

  iren.Initialize()
  renWin.Render()

  if dumpPNG:
    filename = namePNG if namePNG.endswith( '.png' ) else ( "%s.png" % ( namePNG ) )
    writePNG( filename )

  if interactive:
    iren.Start()

def translation( tx, ty, tz, vtkPolyData ):
  transform = vtk.vtkTransform()
  transform.Translate( [ tx, ty, tz ] )
  return TransformPolyData( vtkPolyData, transform )

def rotationX( ax, vtkPolyData ):
  transform = vtk.vtkTransform()
  transform.RotateX( ax )
  return TransformPolyData( vtkPolyData, transform )

def rotationY( ay, vtkPolyData ):
  transform = vtk.vtkTransform()
  transform.RotateY( ay )
  return TransformPolyData( vtkPolyData, transform )

def rotationZ( az, vtkPolyData ):
  transform = vtk.vtkTransform()
  transform.RotateZ( az )
  return TransformPolyData( vtkPolyData, transform )

def rotationPX( p, ax, vtkPolyData ):
  transform = vtk.vtkTransform()
  transform.PostMultiply()
  transform.Translate( [ -p[0], -p[1], -p[2] ] )
  transform.RotateX( ax )
  transform.Translate( p )
  return TransformPolyData( vtkPolyData, transform )

def rotationPY( p, ay, vtkPolyData ):
  transform = vtk.vtkTransform()
  transform.PostMultiply()
  transform.Translate( [ -p[0], -p[1], -p[2] ] )
  transform.RotateY( ay )
  transform.Translate( p )
  return TransformPolyData( vtkPolyData, transform )

def rotationPZ( p, az, vtkPolyData ):
  transform = vtk.vtkTransform()
  transform.PostMultiply()
  transform.Translate( [ -p[0], -p[1], -p[2] ] )
  transform.RotateZ( az )
  transform.Translate( p )
  return TransformPolyData( vtkPolyData, transform )

if __name__ == '__main__':
  if len(sys.argv) == 1 or sys.argv[1].lower().startswith('-h'):
    print help % sys.argv[0]
    sys.exit(0)

  # process arguments
  fname = sys.argv[1]
  st = dicom.read_file(fname)
  if not hasattr( st, 'StructureSetROIs' ):
    print "W pliku", fname, " nie jest zdefiniowany żaden ROI!"
    sys.exit(1)

  if len(sys.argv) < 3:
    for r in st.StructureSetROIs:
      print r.ROIName
    sys.exit(0)

  roiname = sys.argv[2]

  if not sys.argv[3].startswith( '-' ):
    new_roiname = sys.argv[3]
    found = False
    for r in st.StructureSetROIs:
      if r.ROIName == new_roiname:
        print "ROI o nazwie", new_roiname, "już jest zdefiniowany - proszę wybrać inną nazwę"
        sys.exit(1)
      if r.ROIName == roiname:
        found = True
    if not found:
      print "W pliku nie ma ROI o nazwie", roiname
      sys.exit(1)
    optstart = 4
  else:
    new_roiname = None
    optstart = 3

  # process options
  debugPoints= debugGrid= debugPrint= False
  for i in range(optstart,len(sys.argv)-1):
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

  first= last= -1
  for i in range(optstart,len(sys.argv)-1):
    if sys.argv[i] == '-l':
	first, last = map(lambda s: int(s), sys.argv[i+1].split(':') )

  res = resForROIPersistent( roiname, st, fname )
  if debugPrint:
    print "Automatycznie wyznaczona rozdzielczość: ", res
  for i in range(optstart,len(sys.argv)-1):
    if sys.argv[i] == '-r':
      res = map(lambda s: float(s), sys.argv[i+1].split(':') )
      if debugPrint:
        print "Rozdzielczość podana przez użytkownika: [%f %f %f] mm" % ( res[0], res[1], res[2] )
  if res == None or len(res) !=3:
    print "Nie podano rozdzielczości i nie można jej ustalić na podstawie pliku wejściowego!"
    sys.exit(1)

  for i in range(optstart,len(sys.argv)-1):
    if sys.argv[i] == '-t':
	dx, dy, dz = map(lambda s: float(s), sys.argv[i+1].split(':') )
        #print "Translacja: [%f %f %f] mm" % ( dx, dy, dz )

  visualize = False
  for i in range(optstart,len(sys.argv)):
    if sys.argv[i] == '-v':
	visualize = True
 
  dumpPNG = False
  namePNG = None
  for i in range(optstart,len(sys.argv)-1):
    if sys.argv[i] == '-png':
	namePNG = sys.argv[i+1]
	dumpPNG = True

  polyData = False
  for i in range(optstart,len(sys.argv)):
    if sys.argv[i] == '-vtk':
        polyData = True

  writePLY = False
  for i in range(optstart,len(sys.argv)):
    if sys.argv[i] == '-ply':
        writePLY = True

  writeSTL = False
  for i in range(optstart,len(sys.argv)):
    if sys.argv[i] == '-stl':
        writeSTL = True

  quadClust = False
  for i in range(optstart,len(sys.argv)-1):
    if sys.argv[i] == '-sqc':
      sqcDiv = map(lambda s: int(s), sys.argv[i+1].split(':') )
      quadClust = True

  smooth = False
  for i in range(optstart,len(sys.argv)):
    if sys.argv[i] == '-smooth':
      smooth = True
      try:
        arg = map(lambda s: float(s), sys.argv[i+1].split(':') )
        smoothNIt = int(arg[0])
        smoothRt = 0.05 if len(arg) < 2 else arg[1]
      except:
        smoothNIt = 15
        smoothRt = 0.05

  new_color = [43,204,234]
  for i in range(optstart,len(sys.argv)-1):
    if sys.argv[i] == '-color':
      rgb = map(lambda s: int(s), sys.argv[i+1].split(':') )
      if len(rgb) == 3:
        new_color = [ rgb[0], rgb[1], rgb[2] ]
      else:
        print "Złe określenie coloru: ", sys.argv[i+1], "->", rgb
      break

  exactly = True
  for i in range(optstart,len(sys.argv)):
    if sys.argv[i] == '-discrete':
      exactly = False

  showColors = []

  # prepare extractor
  ex = ROIExtractor( st, res, debugPrint=debugPrint, debugGrid=debugGrid, debugPoints=debugPoints, beQuiet=not debugPrint )
  # try to extract countour
  if not ex.extract( roiname, first, last, exactly ):
    print "ROI", roiname, "nie został odnaleziony w zbiorze danych"
    sys.exit(1)
  else:
    shapes = [ ex.roisurface ]
    showColors.append( map( lambda x: x/255.0, ex.roicolor ) )

  if polyData:
    saveVTK( ex.roisurface, roiname )
  if writeSTL:
    saveSTL( ex.roisurface, roiname )
  if writePLY:
    savePLY( ex.roisurface, roiname )

  # simplify if wanted
  if smooth or quadClust:
    tmp = ex.roisurface
    if quadClust:
      sim = vtk.vtkQuadricClustering()
      sim.SetNumberOfXDivisions(sqcDiv[0])
      sim.SetNumberOfYDivisions(sqcDiv[1])
      if len(sqcDiv) > 2:
        sim.SetNumberOfZDivisions(sqcDiv[2])
      sim.SetInput( tmp )
      tmp = sim.GetOutput()
    if smooth: # smooth
      if False:  # próbowałem ten prosty filtr (Laplace - ściąganie wierzchołków do środka wieloboku), ale słabo działa
        sim = vtk.vtkSmoothPolyDataFilter()
        sim.SetNumberOfIterations( smoothNIt )
        sim.SetInput(tmp)
      else:
        sim = vtk.vtkWindowedSincPolyDataFilter()
        sim.SetNumberOfIterations(smoothNIt)
        sim.BoundarySmoothingOff()
        sim.FeatureEdgeSmoothingOff();
        #sim.SetFeatureAngle(45);   # wydaje się nie mieć wpływu
        sim.SetPassBand(smoothRt*min(res));
        sim.NonManifoldSmoothingOn();
        sim.NormalizeCoordinatesOn();
        sim.SetInput(tmp)
        sim.Update();
    oldroisurface = sim.GetOutput()
    shapes.append( oldroisurface )
    showColors.append( banana )
    if polyData:
      saveVTK( oldroisurface, roiname + "_sim" )
    if writeSTL:
      saveSTL(oldroisurface, roiname + "_sim")
    if writePLY:
      savePLY(oldroisurface, roiname + "_sim")
  else:
    oldroisurface = ex.roisurface

  # prepare transformation
  newroisurface = oldroisurface
  transf = ""
  for i in range(optstart,len(sys.argv)-1):
    atransf = None
    if sys.argv[i] == '-tr':
      dx, dy, dz = map(lambda s: float(s), sys.argv[i+1].split(':') )
      newroisurface = translation( dx, dy, dz, newroisurface )
      atransf = "tr[%f,%f,%f]"%(dx,dy,dz)
    if sys.argv[i] == '-rot':
      ax, ay, az = map(lambda s: float(s), sys.argv[i+1].split(':') )
      if ax != None and ax != 0.0:
        newroisurface = rotationX( ax, newroisurface )
      if ay != None and ay != 0.0:
        newroisurface = rotationY( ay, newroisurface )
      if az != None and az != 0.0:
        newroisurface = rotationZ( az, newroisurface )
      atransf = "rot[%f,%f,%f]"%(ax,ay,az)
    if sys.argv[i] == '-loc_rot':
      ax, ay, az = map(lambda s: float(s), sys.argv[i+1].split(':') )
      cg = ex.centrOfGrav
      if ax != None and ax != 0.0:
        newroisurface = rotationPX( cg, ax, newroisurface )
      if ay != None and ay != 0.0:
        newroisurface = rotationPY( cg, ay, newroisurface )
      if az != None and az != 0.0:
        newroisurface = rotationPZ( cg, az, newroisurface )
      atransf = "loc_rot[%f,%f,%f]"%(ax,ay,az)
    if atransf != None:
      transf = transf + " * " + atransf if transf != "" else atransf

  newcontours = []
  if transf != "":
    if debugPrint:
      print roiname + " --{ " + transf + " }--> " + new_roiname
    shapes.append( newroisurface )
    showColors.append( map( lambda x: x/255.0, new_color ) )

    # automatic generation of slicing range:
    newroisurface.ComputeBounds()
    newroisurface.Update()
    xmin,xmax,ymin,ymax,zmin,zmax = newroisurface.GetBounds()
    minZ = ex.bbox[2]
    while minZ > zmin:
      minZ -= ex.res[2]
    maxZ = ex.bbox[5]
    while maxZ < zmax:
      maxZ += ex.res[2]
    slices = map( lambda i: minZ+i*ex.res[2], range(int((maxZ-minZ)/ex.res[2])+1) )
    if debugPrint:
      print "Wyliczone przekroje: (%f,%f):" % (minZ, maxZ), slices
    # user option will overwrite the default
    for i in range(optstart,len(sys.argv)-1):
      if sys.argv[i] == '-slicelist':
        slices = map(lambda s: float(s), sys.argv[i+1].split(':') )
        break
      elif sys.argv[i] == '-slicealg':
        par = map(lambda s: float(s), sys.argv[i+1].split(':') )
        if len(par) == 3:
          slices = map(lambda i: par[0]+i*par[1], range(int(par[2])) )
        else:
          slices = None
          print "Złe określenie przekrojów: ", par
        break

    if slices == None:
      print "Złe wywołanie - brak przekrojów!\n", help % sys.argv[0]
      sys.exit(1)

    newcontours = PolyDataSetToContours( newroisurface, slices )

    #dodajemy i zapisujemy
    addROI( st, new_roiname, newcontours, baseROI=roiname, color=new_color )
    dicom.write_file( fname, st )

    # some testing output and visualisation
    if polyData:
      saveVTK( newroisurface, new_roiname )
    if writeSTL:
      saveSTL( newroisurface, new_roiname )
    if writePLY:
      savePLY( newroisurface, new_roiname )
  #end of if transf != ""

  if visualize or dumpPNG:
    if len(showColors) > 0:
      showPolyData( shapes, ex.incontours + newcontours, colors=showColors, interactive=visualize, dumpPNG=dumpPNG, namePNG=namePNG, ax_origin = [ ex.bbox[0], ex.bbox[1], ex.bbox[2] ], ax_length = 0.2*(ex.bbox[3]-ex.bbox[0]) )
    else:
      showPolyData( shapes, ex.incontours + newcontours, interactive=visualize, dumpPNG=dumpPNG, namePNG=namePNG, ax_origin = [ ex.bbox[0], ex.bbox[1], ex.bbox[2] ], ax_length = 0.2*(ex.bbox[3]-ex.bbox[0]) )
