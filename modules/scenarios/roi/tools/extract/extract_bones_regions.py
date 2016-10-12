#! /usr/bin/python
# -*- coding: utf-8
help = '''
Wyświetla oznaczone różnymi kolorami rozłączne
regiony PolyData przy użyciu PolyDataConnectivityFilter
użycie %s plik.ply

Prawdopodobnie do scalenia z extract_bones_RS 
'''
import vtk
from vtk.util.colors import *
import sys
import os
import argparse
import ipdb


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('file_name')
    parser.add_argument('-t', '--thresholdValue', default='10')
    parser.add_argument('-r', '--setScalarRange', nargs=2)
    parser.add_argument('-s', '--smooth', action='store_true')
    parser.add_argument('-c', '--clean', action='store_true')

    args = parser.parse_args()

    if len(sys.argv) == 1 or sys.argv[1].lower().startswith('-h'):
        print help % sys.argv[0]
        sys.exit(0)

    plyreader = vtk.vtkPLYReader()
    plyreader.SetFileName(args.file_name)

    bones = plyreader.GetOutputPort()
    if(args.smooth):
        sim = vtk.vtkWindowedSincPolyDataFilter()
        sim.SetNumberOfIterations(15)
        sim.BoundarySmoothingOff()
        sim.FeatureEdgeSmoothingOff();
        sim.NonManifoldSmoothingOn();
        sim.NormalizeCoordinatesOn();
        sim.SetInputConnection(bones)
        sim.Update()
        bones = sim.GetOutputPort()

    connectivityFilter = vtk.vtkPolyDataConnectivityFilter()
    connectivityFilter.SetInputConnection(bones)
    #connectivityFilter.SetExtractionModeToLargestRegion()
    connectivityFilter.SetExtractionModeToAllRegions()
    connectivityFilter.ColorRegionsOn()
    connectivityFilter.Update()

    print connectivityFilter.GetNumberOfExtractedRegions()
    print connectivityFilter.GetColorRegions()
    #print connectivityFilter.GetRegionSizes() # na to trzeba zaczekać na wersję 6.0
    print connectivityFilter.GetOutput()
    

    #Create a mapper and actor for original data
    originalMapper = vtk.vtkPolyDataMapper()
    originalMapper.SetInputConnection(plyreader.GetOutputPort())
    originalMapper.Update()

    originalActor = vtk.vtkActor()
    originalActor.SetMapper(originalMapper)
    originalActor.GetProperty().SetRepresentationToWireframe()

    try:
        thresholdValue = int(thresholdValue)
    except:
        thresholdValue = 10

    threshold = vtk.vtkThreshold()
    threshold.ThresholdByLower(thresholdValue)
    threshold.SetInputConnection( connectivityFilter.GetOutputPort() )
    threshold.Update()

    g2tp = vtk.vtkGeometryFilter()
    g2tp.SetInput( threshold.GetOutput() )
    g2tp.Update()

    if args.clean:
        gf = vtk.vtkGeometryFilter()
        gf.SetInput( threshold.GetOutput() )
        gf.Update()
        _, mr = connectivityFilter.GetOutput().GetScalarRange()

        select = vtk.vtkAppendPolyData()
        for t in range(int(mr)+1):
            print t
            threshold.ThresholdBetween(t, t)
            threshold.Update()
            gf.Update()
            if gf.GetOutput().GetNumberOfCells() > 16:
                wyn = vtk.vtkPolyData()
                wyn.CopyStructure(gf.GetOutput())
                select.AddInput(wyn)
                print "znalazlem"
            gf.Update()

        cleanedMapper = vtk.vtkPolyDataMapper()
        cleanedMapper.SetInputConnection(select.GetOutputPort())
        cleanedMapper.Update()
        cleanedActor = vtk.vtkActor()
        cleanedActor.SetMapper(cleanedMapper)
        cleanedActor.VisibilityOff()


    #Create a mapper and actor for extracted data
    extractedMapper = vtk.vtkPolyDataMapper()
    try:
        a = int( args.setScalarRange[0])
        b = int( args.setScalarRange[1])
    except:
    	a,b = connectivityFilter.GetOutput().GetScalarRange()
    lut = vtk.vtkColorTransferFunction()
    lut.AddRGBPoint(a,         0.0, 0.0, 1.0)
    lut.AddRGBPoint(a+(b-a)/4, 0.0, 0.5, 0.5)
    lut.AddRGBPoint(a+(b-a)/2, 0.0, 1.0, 0.0)
    lut.AddRGBPoint(b-(b-a)/4, 0.5, 0.5, 0.0)
    lut.AddRGBPoint(b,         1.0, 0.0, 0.0)
    extractedMapper.SetLookupTable(lut)
    extractedMapper.SetScalarRange(a,b)
    #extractedMappe.SetInputConnection(connectivityFilter.GetOutputPort())
    extractedMapper.SetInputConnection(g2tp.GetOutputPort())
    #extractedMapper.SetScalarRange(connectivityFilter.GetOutput().GetPointData().GetArray("RegionId").GetRange())
    extractedMapper.Update()

    extractedActor = vtk.vtkActor()
    #extractedActor.GetProperty().SetColor(1, 0, 0)
    extractedActor.SetMapper(extractedMapper)

    renderer = vtk.vtkRenderer()
    renderer.AddActor(originalActor)
    renderer.AddActor(extractedActor)
    if args.clean:
        renderer.AddActor(cleanedActor)

    renderWindow = vtk.vtkRenderWindow()
    renderWindow.SetSize(800,600)
    renderWindow.AddRenderer(renderer)

    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(renderWindow)

    #seed widget - representation
    handle = vtk.vtkPointHandleRepresentation2D()
    handle.GetProperty().SetColor(0,0,0)
    rep = vtk.vtkSeedRepresentation()
    rep.SetHandleRepresentation(handle)

    #seed widget
    seedWidget = vtk.vtkSeedWidget()
    seedWidget.SetInteractor(interactor)
    seedWidget.SetRepresentation(rep)

    def seedCallback(obj, event):
        #ipdb.set_trace()
        print obj.GetSeedRepresentation().GetNumberOfSeeds()

    seedWidget.AddObserver("PlacePointEvent", seedCallback)

    def sliderCallback(obj, event):
        treshold = int(obj.GetRepresentation().GetValue())
        obj.GetRepresentation().SetValue(treshold)
	print treshold
        threshold.ThresholdBetween( treshold-0.5, treshold+0.5 )
        threshold.Update()
	g2tp.Update()
	print g2tp.GetOutput().GetNumberOfCells()

    #slider 
    sliderRep  = vtk.vtkSliderRepresentation2D()
    sMin,sMax = connectivityFilter.GetOutput().GetScalarRange()
    sliderRep.SetMinimumValue(sMin)
    sliderRep.SetMaximumValue(sMax)
    sliderRep.SetValue(thresholdValue)
    sliderRep.SetTitleText("threshold");
    sliderRep.GetSliderProperty().SetColor(0,1,0)
    sliderRep.GetSelectedProperty().SetColor(1,0,0)
    sliderRep.GetPoint1Coordinate().SetCoordinateSystemToDisplay()
    sliderRep.GetPoint1Coordinate().SetValue(40, 40)
    sliderRep.GetPoint2Coordinate().SetCoordinateSystemToDisplay()
    sliderRep.GetPoint2Coordinate().SetValue(340, 40)
    
    sliderWidget = vtk.vtkSliderWidget()
    sliderWidget.SetInteractor(interactor)
    sliderWidget.SetRepresentation(sliderRep)
    sliderWidget.EnabledOn()
    sliderWidget.AddObserver("EndInteractionEvent", sliderCallback)

    def windowCharEventCallback( obj, event ):
            if obj.GetKeyCode() == 'b':
                    if originalActor.GetVisibility() == 0:
                            originalActor.VisibilityOn()
                    else:
                            originalActor.VisibilityOff()
            if obj.GetKeyCode() == 'a':
                    if cleanedActor.GetVisibility() == 0:
                            cleanedActor.VisibilityOn()
                    else:
                            cleanedActor.VisibilityOff()
                    
		    renderWindow.Render()

    interactor.AddObserver( "KeyPressEvent", windowCharEventCallback )

    interactor.Initialize()
    interactor.Start()



