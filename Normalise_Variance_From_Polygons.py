# Script parameters inputting settings-------------------------------------------------------------------------v
#@ File (label="Input Images:", style="directory") Image_Folder
#@ File (label="Input Roi:", style="directory") Roi_Folder
#@ File (label="Output", style="file") Output_File

import os, sys

from ij import ImagePlus
from ij.plugin.filter import Analyzer
from ij.measure import Measurements
from ij.measure import ResultsTable
from ij.plugin.frame import RoiManager

def getRoiMeasurements(SampleRoi, Image, Measurement_Options):
	"""Gets the given measurements of the provided Roi for the given image

	Args:
		SampleRoi (ij.gui.Roi): Roi to be analysed
		Image (ij.ImagePlus): Image to be analysed
		Measurement_Options ([str]): ij.Measure.Measurements to be taken

	Returns:
		[float]: List of measurements in same order as Measurement_Options
	"""	
	
	# Initialises a new empty results table
	RTable = ResultsTable()
	# Initialises an Analyzer object using 
	# the image and the empty results table
	An = Analyzer(Image, RTable)
	# Selects the roi on the image
	Image.setRoi(SampleRoi)
	# Takes the measurements
	An.measure()
	# Takes the desired results from 
	# the results table and adds to a list
	OutputList = []
	for Option in Measurement_Options:
		OutputList.append(RTable.getValue(Option, 0))
	# Clears the results table
	RTable.reset()
	# Clears the roi from the image
	Image.resetRoi()
	return OutputList

# Gets the path from the Java.io.File object
InputPath = Image_Folder.getPath()
RoiPath = Roi_Folder.getPath()
OutputPath = Output_File.getPath()
RoiMan = RoiManager()
# This section sets the measurements that will be used
AnalyzerClass = Analyzer()
# Gets original measurements to reset later
OriginalMeasurements = AnalyzerClass.getMeasurements()
# Sets the measurements to be used
AnalyzerClass.setMeasurements(
	Measurements.STD_DEV 
	+ Measurements.MIN_MAX
)
OutputFile = open(OutputPath, "w")
sys.stdout = OutputFile

for ImageFilename in os.listdir(InputPath):
	Imp = ImagePlus(os.path.join(InputPath, ImageFilename))
	splitfilename = "_".join(ImageFilename.split("_")[:-1])
	RoiMan.runCommand("Open", os.path.join(RoiPath, splitfilename+".zip"))
	RoiList = RoiMan.getRoisAsArray()
	outputlist = []
	for Roi in RoiList:
		Measurements = getRoiMeasurements(Roi, Imp, ["StdDev", "Max"])
		Variance = Measurements[0]**2
		NormalisedVariance = Variance/(Measurements[1]**2)
		outputlist.append(NormalisedVariance)
	print ImageFilename,",",
	for value in outputlist:
		print value,",",
	print ""
	RoiMan.reset()

OutputFile.close()
AnalyzerClass.setMeasurements(OriginalMeasurements)