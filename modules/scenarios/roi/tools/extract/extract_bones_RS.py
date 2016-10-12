#! /usr/bin/python
# -*- coding: utf-8
help = '''
Wyciąga obrazek kości z katalogu zawierającego CT w formacie DICOM na podstawie pliku RS

Użycie: %s plik-RS [ progowa-wartość-jasności-dla-kości [ wynik ] ]

	Domyślna wartość progowa to 200.
        wynik.ply może miec dowolną nazwę, ale rozszerzenie musi być ply ;-)

Uwaga: jeśli program działa w trybie graficznym, to wynik zostanie zapisany do pliku wynik.ply
       dopiero po naciśnięciu klawisza 's'.
'''

import vtk
from vtk.util.colors import *
import sys
import os
from digRS import frames
import dicom




if __name__ == '__main__':
	if len(sys.argv) == 1 or sys.argv[1].lower().startswith('-h'):
		print help % sys.argv[0]
		sys.exit(0)

	st = dicom.read_file( sys.argv[1] )
	try:	
		threshold = 200 if len(sys.argv) < 3 else float(sys.argv[2])
	except:
		threshold = 200

	#reader.SetDirectoryName( os.path.dirname(sys.argv[1]) )
	frameset = frames( st, sys.argv[1] )
	if frameset != None:
		reader = vtk.vtkImageReader2()
		inpt = vtk.vtkStringArray()
		#print len(framesets)
		for f in frameset:
			#print os.path.basename(f[0]), f[1][2]
			inpt.InsertNextValue( f[0] ) 
		reader.SetFileNames( inpt )
		# each frame:  file-name origin resolution pix
	        ex = ( 0, frameset[0][3][0]-1, 0, frameset[0][3][1]-1, 0, len(frameset)-1 )
		reader.SetDataExtent( ex )
                # do zabawy z przekształcaniem układu współrzędnych
		#frameset[0][2][1] = -frameset[0][2][1]
		#frameset[0][2][2] = -frameset[0][2][2]
		reader.SetDataSpacing( frameset[0][2] )
		reader.SetDataOrigin( frameset[0][1] )
		reader.Update()
	else:
		print "No frames"
		sys.exit(1)

	vol = reader.GetOutput()


	bb = vol.GetBounds()
	#print bb       # x,y,z
	#print vol.GetScalarRange()  # intesity
	if bb[5]-bb[4] < 1e-7:
		sys.exit(1)
	iso = vtk.vtkMarchingCubes()
	iso.SetInput(vol)
	iso.SetValue(0,threshold)

	def sliderCallback(obj, event):
		threshold = obj.GetRepresentation().GetValue()
		iso.SetInput(vol)
		iso.SetValue(0, threshold)
	
	bones = iso.GetOutput()

	#print "got bones", bones

	if True:
	# Kierunek osi Y jest odwrócony, bo w DICOMie OY jest skierowana w dół.
        # Trzeba ją wywrócić z powrotem jak w dicomie
		transform = vtk.vtkTransform()
  		transform.Scale( [ 1, -1, 1 ] )
		transFilter = vtk.vtkTransformPolyDataFilter()
		transFilter.SetInput(bones)
		transFilter.SetTransform(transform)
		bones = transFilter.GetOutput()
		# Ujemne skalowanie osi Y wywraca układ współrzędnych na lewo - trzeba z powrotem wywrócić kości
		reverse = vtk.vtkReverseSense()
		reverse.SetInput(bones)
		bones = reverse.GetOutput()

       	bones.ComputeBounds()
	bones.Update()

	# Obcinanie przez kontur
	for i in range(2,len(sys.argv)-1):
		if sys.argv[i] == '-c' and sys.argv[i+1].endswith('ply'):   #vtkImplicitPolyDataDistance jest chyba w 6.0! 
			print "Z prawdziwym obcinaniem przez kontury trzeba zaczekać do do vtk 6.0\nNa razie tniemy przez BBOX"
			plyreader = vtk.vtkPLYReader()
			plyreader.SetFileName(sys.argv[i+1])
  			clip = plyreader.GetOutput()
			clip.ComputeBounds()
			clip.Update()
			if False: # czekamy na 6.0
				cf = vtk.vtkImplicitPolyDataDistance()
				cf.SetInput(clip)
			else: # na razie
				cf = vtk.vtkBox()
				cf.SetBounds( clip.GetBounds() )
			pClipper = vtk.vtkClipPolyData()
			pClipper.SetClipFunction( cf )
			pClipper.InsideOutOn()
			pClipper.SetInput(bones)
			bones = pClipper.GetOutput()

	#print bones.GetBounds()

	def save( filename, data ):
		ply = vtk.vtkPLYWriter()
		ply.SetFileName( filename )
		ply.SetInput( data )
		ply.Write()
		print "Result saved to", filename 

	if os.environ.has_key('DISPLAY') and os.environ['DISPLAY'] != '':
		# Visualize: the Mapper and the Actor
		mapper = vtk.vtkPolyDataMapper()
		mapper.SetInput(bones)
		mapper.ScalarVisibilityOff() # zeby umozliwic kolorowanie aktora
		actor = vtk.vtkActor()
		actor.SetMapper(mapper)
		actor.GetProperty().SetDiffuseColor( white )
		actor.ApplyProperties()
		actor.GetProperty().SetOpacity(.6)

		# Create the Renderer, RenderWindow, and RenderWindowInteractor
		ren = vtk.vtkRenderer()
		renWin = vtk.vtkRenderWindow()
		renWin.AddRenderer(ren)
		renWin.SetSize(640, 480)
		iren = vtk.vtkRenderWindowInteractor()
		iren.SetRenderWindow(renWin)

		#slider 
		sliderRep  = vtk.vtkSliderRepresentation2D()
		sliderMin, sliderMax = vol.GetScalarRange()
		sliderRep.SetMinimumValue(sliderMin)
		sliderRep.SetMaximumValue(sliderMax) 
		sliderRep.SetValue(200)
		sliderRep.SetTitleText("threshold");
		sliderRep.GetSliderProperty().SetColor(0,1,0)
		sliderRep.GetSelectedProperty().SetColor(1,0,0)
  		sliderRep.GetPoint1Coordinate().SetCoordinateSystemToDisplay()
  		sliderRep.GetPoint1Coordinate().SetValue(40, 40)
  		sliderRep.GetPoint2Coordinate().SetCoordinateSystemToDisplay()
  		sliderRep.GetPoint2Coordinate().SetValue(340, 40)

  		sliderWidget = vtk.vtkSliderWidget()
  		sliderWidget.SetInteractor(iren)
  		sliderWidget.SetRepresentation(sliderRep)
  		sliderWidget.EnabledOn()
  		sliderWidget.AddObserver("EndInteractionEvent", sliderCallback)

		# BoxWidget
		# This portion of the code clips the bones with the vtkPlanes implicit
		# function.  The clipped region is colored green.
		planes = vtk.vtkPlanes()
		iClipper = vtk.vtkClipPolyData()
		iClipper.SetInput(bones)
		iClipper.SetClipFunction(planes)
		iClipper.InsideOutOn()
		selectMapper = vtk.vtkPolyDataMapper()
		selectMapper.SetInputConnection(iClipper.GetOutputPort())
		selectMapper.ScalarVisibilityOff()
		selectActor = vtk.vtkLODActor()
		selectActor.SetMapper(selectMapper)
		selectActor.GetProperty().SetColor(green)
		selectActor.VisibilityOff()  # na razie nie można go pokazać, bo iClipper się zbuntuje nie mając planes
		selectActor.SetScale(1.01, 1.01, 1.01)
		ren.AddActor( selectActor )

		# The SetInteractor method is how 3D widgets are associated with the
		# render window interactor.  Internally, SetInteractor sets up a bunch
		# of callbacks using the Command/Observer mechanism (AddObserver()).
		boxWidget = vtk.vtkBoxWidget()
		boxWidget.SetInteractor(iren)
		boxWidget.SetPlaceFactor(1.00)

		# This callback funciton does the actual work: updates the vtkPlanes
		# implicit function.  This in turn causes the pipeline to update.
		def selectPolygons(object, event):
		    # object will be the boxWidget
		    global selectActor, planes
		    object.GetPlanes(planes)
		    selectActor.VisibilityOn()

		# Place the interactor initially. The input to a 3D widget is used to
		# initially position and scale the widget. The "EndInteractionEvent" is
		# observed which invokes the SelectPolygons callback.
		boxWidget.SetInput(bones)
		boxWidget.PlaceWidget()
		boxWidget.AddObserver("EndInteractionEvent", selectPolygons)
		boxWidget.EnabledOn()
		boxWidget.GetPlanes(planes)
		selectActor.VisibilityOn()


		# Add the actors to the renderer
		ren.AddActor(actor)

		# Set the background color.
		ren.SetBackground(slate_grey)

		# Position the camera.
		ren.ResetCamera()
		ren.GetActiveCamera().Dolly(1.2)
		ren.GetActiveCamera().Azimuth(30)
		ren.GetActiveCamera().Elevation(20)
		ren.ResetCameraClippingRange()

		def windowCharEventCallback( obj, event ):
			global boxWidget, planes, iClipper, selectActor, bones, actor, renWin
			#print obj.GetKeyCode(), "pressed"
			if obj.GetKeyCode() == 'z' and  len(sys.argv) > 3 and sys.argv[3].endswith('.ply'):
				boxWidget.GetPlanes(planes)
				bones = iClipper.GetOutput()
				save( sys.argv[3], bones )
			elif obj.GetKeyCode() == 'd':
				boxWidget.PlaceWidget()
				boxWidget.GetPlanes(planes)
			elif obj.GetKeyCode() == 'b':
				if actor.GetVisibility() == 0:
					actor.VisibilityOn()
				else:
					actor.VisibilityOff()
				renWin.Render()
			else:
				print "Interakcja:\nb - pokaż,ukryj całość (zostawia tylko widok obcięcia)\nd - powróć do domyślnego ustawienia pudełka obcinającego\nz - zapisz (tylko, gdy przy wywołaniu podano nazwę pliku ply\nDziałają też standardowe klawisze vtk: j,t,c,a,e,f,p,r,s,u,w."

		iren.AddObserver( "KeyPressEvent", windowCharEventCallback )
		iren.Initialize()
		renWin.Render()
		iren.Start()

	elif len(sys.argv) > 3 and sys.argv[3].endswith('.ply'):
		save( sys.argv[3], bones )
