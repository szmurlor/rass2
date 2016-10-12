#! /usr/bin/python
# -*- coding: utf-8
help = '''
Wyciąga obrazek kości z katalogu zawierającego CT w formacie DICOM

Użycie: %s katalog-z-CT [ progowa-wartość-jasności-dla-kości [ wynik ] ]

	Domyślna wartość progowa to 200.
        wynik.ply może miec dowolną nazwę, ale rozszerzenie musi być ply ;-)

UWAGA: vtkDICOMImageReader słabo sobie radzi z katalogami, w których
       są pliki inne, niż CT - trzeba nad tym posiedzieć.
'''

import vtk
from vtk.util.colors import *
import sys
import os

if __name__ == '__main__':
	if len(sys.argv) == 1 or sys.argv[1].lower().startswith('-h'):
		print help % sys.argv[0]
		sys.exit(0)

	inp_dir = sys.argv[1]
	treshold = 200 if len(sys.argv) < 3 else float(sys.argv[2])
	print "will make reader"

	reader = vtk.vtkDICOMImageReader()
	print "will set input dir to", inp_dir
	reader.SetDirectoryName(inp_dir)
	print "will update"
	reader.Update()
	print "will read"
	vol = reader.GetOutput()
	print vol.GetBounds()       # x,y,z
	print vol.GetScalarRange()  # intesity
	iso = vtk.vtkMarchingCubes()
	iso.SetInput(vol)
	iso.SetValue(0,treshold)

	bones = iso.GetOutput()
        bones.ComputeBounds()
	bones.Update()
	print bones.GetBounds()

	if len(sys.argv) > 3 and sys.argv[3].endswith('ply'):
		ply = vtk.vtkPLYWriter()
    		ply.SetFileName( sys.argv[3] )
    		ply.SetInput(iso.GetOutput())
    		ply.Write()

	if os.environ.has_key('DISPLAY') and os.environ['DISPLAY'] != '':
		# Visualize: the Mapper and the Actor
		mapper = vtk.vtkPolyDataMapper()
		mapper.SetInput(iso.GetOutput())
		actor = vtk.vtkActor()
		actor.SetMapper(mapper)
		actor.GetProperty().SetDiffuseColor( white ) # to czemuś nie działa - SPRAWDZIĆ
		actor.GetProperty().SetOpacity(.6)

		# Create the Renderer, RenderWindow, and RenderWindowInteractor
		ren = vtk.vtkRenderer()
		renWin = vtk.vtkRenderWindow()
		renWin.AddRenderer(ren)
		renWin.SetSize(640, 480)
		iren = vtk.vtkRenderWindowInteractor()
		iren.SetRenderWindow(renWin)

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

		iren.Initialize()
		renWin.Render()
		iren.Start()

