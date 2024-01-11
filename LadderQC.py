#@ File (label="Input Image", style="file") InputImage
#@ File (label="Output Directory", style="directory") OutputDirectory

# Python modules
import copy, re, os
from collections import Counter
# Java modules
from java.lang import Math
# ImageJ modules
from ij import IJ
from ij import WindowManager
from ij.io import FileSaver
from ij.gui import Line
from ij.gui import Overlay
from ij.gui import Roi
from ij.measure import Measurements
from ij.measure import ResultsTable
from ij.plugin import ZProjector
from ij.plugin.filter import Analyzer
# Bioformats modules
from loci.plugins import BF
from loci.plugins.in import ImporterOptions


def analyzeParticles(
		Binary_Image, 
		Size_Setting, 
		Circularity_Setting):
	"""Runs analyze particles on the binary image, returning the ROI

	Args:
		Binary_Image (ij.ImagePlus): Segmented binary image
		Size_Setting (str): Min/Max size settings for analyse particles
		Circularity_Setting (str): Min/Max circularity settings for analyse particles

	Returns:
		[PolygonRoi]: Outputted Rois
	"""	

	# Defines analyse particles settings
	AnalyzeParticlesSettings = (
		"Size=" 
		+ Size_Setting 
		+ " circularity=" 
		+ Circularity_Setting 
		+ " clear overlay exclude"
	)
	# Runs the analyze particles command to get ROI. 
	# Done by adding to the overlay in order to not have ROIManger shown to user
	IJ.run(Binary_Image, "Analyze Particles...", AnalyzeParticlesSettings)
	# Gets the Overlayed ROIs from analyze particles
	Overlayed_Rois = Binary_Image.getOverlay()
	# Takes the overlay and turns it into an array of ROI
	RoiList = Overlayed_Rois.toArray()
	# Removes this overlay to clean up the image
	IJ.run(Binary_Image, "Remove Overlay", "")
	return RoiList


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


def distanceBetweenPoints(X1, Y1, X2, Y2):
	"""Calculates the distance between two coordinates

	Args:
		X1 (float): Start X coordinate
		Y1 (float): Start Y coordinate
		X2 (float): End X coordinate
		Y2 (float): End Y coordinate

	Returns:
		float: Distance between the two points
	"""	
	xdiff = X1 - X2
	ydiff = Y1 - Y2
	Distance = Math.sqrt((xdiff*xdiff) + (ydiff*ydiff))
	return Distance


def closestPoint(Point, Point_List):
	"""Finds the closest two points in a list of ROIs

	Args:
		Roi (ij.gui.Roi): Roi to compare distances to
		RoiList (ij.gui.Roi[]): List of ROIs

	Returns:
		list: List of the two closest ROIs
	"""	
	MinDistance = float("Infinity")
	MinPoint = (None, None)

	for OtherPoint in Point_List:
		Distance = distanceBetweenPoints(Point[0], Point[1], OtherPoint[0], OtherPoint[1])
		if Distance < MinDistance:
			MinDistance = Distance
			MinPoint = OtherPoint
	return MinPoint
	

def roundToBase(Number, Base):
	"""Rounds the given number to the nearest multiple of the given base

	Args:
		Number (float): Number to be rounded
		Base (int): Base to round to

	Returns:
		int: Rounded number
	"""	
	RoundedNumber = (Base * Math.round(Number/Base))
	return RoundedNumber


def getAngleBetweenPoints(Point1, Point2):
	"""Gets the angle between two points in degrees

	Args:
		Point1 (tuple): X and Y coordinates of first point
		Point2 (tuple): X and Y coordinates of second point

	Returns:
		float: Angle between two points in degrees
	"""	
	Angle = Math.toDegrees(Math.atan2(Point2[1] - Point1[1], Point2[0] - Point1[0]))
	return Angle


def selectWindow(Pattern):
	"""Selects the window with the given pattern in the title

	Args:
		Pattern (string): regex pattern to match

	Returns:
		boolean: Whether the given window was found and selected
	"""	
	TitleList = WindowManager.getImageTitles()
	for Title in TitleList:
		if re.match(Pattern, Title):
			IJ.selectWindow(Title)
			return True
	return False


# This section sets the measurements that will be used
AnalyzerClass = Analyzer()
# Gets original measurements to reset later
OriginalMeasurements = AnalyzerClass.getMeasurements()

# Sets the measurements to be used
AnalyzerClass.setMeasurements(
	Measurements.SHAPE_DESCRIPTORS 
	+ Measurements.CENTROID
)

# Gets the needed paths and filenames for input and output
FileName = InputImage.getName()
FileNameNoExtension = ".".join(FileName.split("."))[:-1]
OutputPath = OutputDirectory.getPath()

# Imports the image using Bioformats-------------------v
Options = ImporterOptions()
Options.setId(InputImage.getPath())
# Ensures that the image is not split into focal planes
Options.setSplitFocalPlanes(False)
Options.setAutoscale(True)
Imp = BF.openImagePlus(Options)[0]
#------------------------------------------------------^

Calibration = Imp.getCalibration()
ZDepth = Calibration.pixelDepth

# Max intensity of the image to get all of the ladder
Projected = ZProjector.run(Imp, "max")
# Removes the scale so ROI coordinates are correct
Projected.removeScale()
# Thresholds the image to get the ladder
IJ.setAutoThreshold(Projected, "Default dark")
IJ.run(Projected, "Convert to Mask", "")
# Runs analyze particles to get a list of ROIs
RoiList = analyzeParticles(Projected, "0-Infinity", "0.00-1.00")

# String needed to get the centroid of the ROI
CentroidString = ["X", "Y"]

# Gets the centroid of each ROI and adds to a list-------------------v
PointList = []
for ThisRoi in RoiList:
	Centroid = getRoiMeasurements(ThisRoi, Projected, CentroidString)
	# Must be a tuple to be hashable in dictionary
	PointList.append(tuple(Centroid))
#--------------------------------------------------------------------^

# For each point it will get the angle of the line between it and the closest point-v
# This will be used to eliminate the points that are not part of the ladder
# As these points will all be running parallel to each other
PointDict = {}
RoundedAngleList = []
for Index, PointItem in enumerate(PointList):
	# Need to deep copy the list to avoid modifying the original
	InputList = copy.copy(PointList)
	# Need to remove the current point from the list to avoid finding itself
	del InputList[Index]
	# Finds the closest point to the current point
	ClosestPoint = closestPoint(PointItem, InputList)
	# Gets the angle between the two points
	LineAngle = getAngleBetweenPoints(PointItem, ClosestPoint)
	# Rounds the angle to the nearest 5 degrees
	# Has to be absolute as the lines can be in either direction
	RoundedAngle = abs(roundToBase(LineAngle, 5))
	# Adds the angle to a dictionary with the point as the key
	PointDict[PointItem] = RoundedAngle
	# Adds the angle to a list of all angles to find the mode
	RoundedAngleList.append(RoundedAngle)
#-----------------------------------------------------------------------------------^

# Gets the mode angle
ModeAngle = Counter(RoundedAngleList).most_common(1)[0][0]
# Gets the points that have the mode angle--------v
# These are the points that are part of the ladder
LadderList = []
for PointItem in PointDict:
	if ModeAngle == PointDict[PointItem]:
		LadderList.append(PointItem)
#-------------------------------------------------^

# Gets the two points that are furthest apart but are still parallel to each other--------------------------v
MaxLadderDistance = 0
for Index, FirstPoint in enumerate(LadderList):
	# Need to deep copy the list to avoid modifying the original
	SecondList = copy.copy(LadderList)
	# Need to remove the current point from the list to avoid finding itself
	del SecondList[Index]
	# Loops though every other list of points to find the furthest apart
	for SecondPoint in SecondList:
		# Gets the angle between the two points, has to be absolute as the lines can be in either direction
		LadderAngle = abs(getAngleBetweenPoints(FirstPoint, SecondPoint))
		# Gets the distance between the two points
		LadderDistance = distanceBetweenPoints(FirstPoint[0], FirstPoint[1], SecondPoint[0], SecondPoint[1])
		# Rounds the angle to the nearest 5 degrees
		RoundedLadderAngle = roundToBase(LadderAngle, 5)
		# If the angle is the same as the mode angle and the distance is greater than the current max
		# Then these are the new furthest apart points
		if RoundedLadderAngle == ModeAngle and LadderDistance > MaxLadderDistance:
			FeducialLine = Line(FirstPoint[0], FirstPoint[1], SecondPoint[0], SecondPoint[1])
			# This angle is not rounded as it is used to rotate the image
			FeducialAngle = LadderAngle
			MaxLadderDistance = LadderDistance
#-----------------------------------------------------------------------------------------------------------^

# Need to use an overlay so it will rotate with the image
LineOverlay = Overlay(FeducialLine)
Imp.setOverlay(LineOverlay)

# Rotates the image so the ladder is horizontal
IJ.run(Imp, "Arbitrarily...", "angle=" + str(FeducialAngle) + " interpolate stack")
# Gets the Rotated Roi from the overlay
RotatedLineOverlay = Imp.getOverlay()
RotatedLineRoi = RotatedLineOverlay.get(0)
# Removes the overlay to clean up the image
Imp.setOverlay(None)

# Gets the centroid of the rotated line
LineCentroid = getRoiMeasurements(RotatedLineRoi, Projected, CentroidString)

# Gets the width of the image
Width = Imp.getWidth()
# Creates a box roi that is 1 pixel high and the width of the image centred on the line centroid
BoxRoi = Roi(0, LineCentroid[1], Width, 1)

# Crops the image to the single line
Imp.setRoi(BoxRoi)
LineImage = Imp.crop("stack")

# Closes the original image to save memory
Imp.close()

# Runs the reslice command to get the XZ image similar to orthagonal view
IJ.run(LineImage, "Reslice [/]...", "output=" + str(ZDepth) +" start=Top avoid")

# Gets the resliced image
selectWindow("Reslice ")
OriginalSlicedImp = IJ.getImage()
# Duplicates the image to only get one slice
SlicedImp = OriginalSlicedImp.crop()
# Close the original image to save memory
OriginalSlicedImp.close()

# Performs gaussian blur to smooth the image
IJ.run(SlicedImp, "Gaussian Blur...", "sigma=6")
# Gets the statistics which includes the minimum and maximum intensity of the image
ImpStats = SlicedImp.getStatistics()
# Sets the prominence for the find maxima command to be half the difference between the min and max intensity
Prominence = str((ImpStats.max - ImpStats.min)/2)
# Finds the maxima in the image and outputs to a results table
IJ.run(SlicedImp, "Find Maxima...", "prominence=" + Prominence + " output=List")

# Saves the XZ image and closes to save memory
FileSaver(SlicedImp).saveAsTiff(os.path.join(OutputPath, FileNameNoExtension + "_XZ.tif"))
SlicedImp.close()

# Gets the results table and copies it so the displayed one can be closed
Results = ResultsTable().getResultsTable()
MaximaResults = Results.clone()
# Needs to reset the table to avoid dialog asking to save
Results.reset()
# Closes the results table
WindowManager.getWindow("Results").close()

# Calculates the axial step size for each maxima
for Row in range(0, MaximaResults.size()):
	AxialStep = MaximaResults.getValue("Y", Row) * ZDepth
	MaximaResults.setValue("AxialStep", Row, AxialStep)

# Sorts the results table by the X coordinate
MaximaResults.sort("X")

# Calculates the axial difference between each maxima
for SortedRow in range(1, MaximaResults.size()):
	AxialDiff = abs(MaximaResults.getValue("AxialStep", SortedRow) - MaximaResults.getValue("AxialStep", SortedRow - 1))
	MaximaResults.setValue("AxialDiff", SortedRow, AxialDiff)

# Saves the results table
MaximaResults.saveAs(os.path.join(OutputPath, FileNameNoExtension + "_XZ.csv"))

# Resets the measurements to the original settings
AnalyzerClass.setMeasurements(OriginalMeasurements)