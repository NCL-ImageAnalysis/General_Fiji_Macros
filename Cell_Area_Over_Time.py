#@ File (label="Folder containing images:", style="directory") InDir
#@ File (label="CSV output folder:", style="directory") OutFile
#@ Integer (label="Phase Channel:") Phase_Channel

import re, os

from ij import IJ
from ij.measure import ResultsTable, Measurements
from ij.plugin import Duplicator, RoiEnlarger
from ij.plugin.filter import Analyzer
from ij.macro import Variable

def analyzeParticles(
		Binary_Image,
		size_min = "0.00",
		size_max = "Infinity",
		circ_min = "0.00",
		circ_max = "1.00",
		exclude=True,
		stack=False,
		pixel=False
		):
	"""Runs analyze particles on the binary image, returning the ROI

	Args:
		Binary_Image (ij.ImagePlus): Segmented binary image
		size_min (str): Min size setting for analyse particles. Defaults to "0.00"
		size_max (str): Max size setting for analyse particles. Defaults to "Infinity"
		circ_min (str): Min circularity setting for analyse particles. Defaults to "0.00"
		circ_max (str): Max circularity setting for analyse particles. Defaults to "1.00"
		exclude (bool): Whether to exclude certain particles from analysis. Defaults to True
		stack (bool): Whether to include stack in analysis. Defaults to False
		pixel (bool): Whether to include pixel in analysis. Defaults to False

	Returns:
		[PolygonRoi]: Outputted Rois
	"""	

	# Defines analyse particles settings
	AnalyzeParticlesSettings = (
		"size=" 
		+ size_min
		+ "-" 
		+ size_max
		+ " circularity=" 
		+ circ_min
		+ "-" 
		+ circ_max
		+ " overlay"
	)
	if exclude:
		AnalyzeParticlesSettings += " exclude"
	if stack:
		AnalyzeParticlesSettings += " stack"
	if pixel:
		AnalyzeParticlesSettings += " pixel"
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
		Measurement_Options ([str]) or ([ij.measure.Measurements]): Measurements to be taken in the form of either strings of the column headings or ij.measure.Measurements integers

	Returns:
		[float]: Dictionary of measurements with column headings as titles
	"""	

	# This dictionary converts Measurement_Options to the corresponding column names in the results table
	Measurement_Dict = {
		Measurements.ADD_TO_OVERLAY: [None],
		Measurements.AREA: ['Area'],
		Measurements.AREA_FRACTION: ['%Area'],
		Measurements.CENTER_OF_MASS: ['XM', 'YM'],
		Measurements.CENTROID: ['X', 'Y'],
		Measurements.CIRCULARITY: ['Circ.', 'AR', 'Round', 'Solidity'],
		Measurements.ELLIPSE: ['Major', 'Minor', 'Angle'],
		Measurements.FERET: ['Feret', 'FeretX', 'FeretY', 'FeretAngle', 'MinFeret'],
		Measurements.INTEGRATED_DENSITY: ['IntDen'],
		Measurements.INVERT_Y: [None],
		Measurements.KURTOSIS: ['Kurt'],
		Measurements.LABELS: ['Label'],
		Measurements.LIMIT: [None],
		Measurements.MAX_STANDARDS: [None],
		Measurements.MEAN: ['Mean'],
		Measurements.MEDIAN: ['Median'],
		Measurements.MIN_MAX: ['Min', 'Max'],
		Measurements.MODE: ['Mode'],
		Measurements.NaN_EMPTY_CELLS: [None],
		Measurements.PERIMETER: ['Perim.'],
		Measurements.RECT: ['ROI_X', 'ROI_Y', 'ROI_Width', 'ROI_Height'],
		Measurements.SCIENTIFIC_NOTATION: [None],
		Measurements.SHAPE_DESCRIPTORS: ['Circ.', 'AR', 'Round', 'Solidity'],
		Measurements.SKEWNESS: ['Skew'],
		Measurements.SLICE: [None],
		Measurements.STACK_POSITION: [None],
		Measurements.STD_DEV: ['StdDev']
	}

	# Initialises a new empty results table
	RTable = ResultsTable()
	# Initialises an Analyzer object using 
	# the image and the empty results table
	try:
		# If input list is of ij.measure.Measurements will use those measurements for the analyzer
		Measurement_int = sum(Measurement_Options)
		An = Analyzer(Image, Measurement_int, RTable)
	except TypeError:
		# Otherwise will just use global measurement options
		Measurement_int = None
		An = Analyzer(Image, RTable)
	# Selects the roi on the image
	Image.setRoi(SampleRoi)
	# Takes the measurements
	An.measure()
	# If the measurements were not specified
	# will use input column headings
	if Measurement_int == None:
		Output_List = Measurement_Options
	# Otherwise will get measurement options from dictionary
	else:
		Output_List = []
		for Option in Measurement_Options:
			Output_List += Measurement_Dict[Option]
	# Takes the desired results from the results table and adds to the dictionary
	OutputDict = {}
	for Option in Output_List:
		if Option != None:
			OutputDict[Option] = RTable.getValue(Option, 0)
	# Clears the results table
	RTable.reset()
	# Clears the roi from the image
	Image.resetRoi()
	return OutputDict

def dict2ResultsTable(results_dict):
	RT = ResultsTable()
	for key in results_dict.keys():
		VarList = [Variable(var) for var in results_dict[key]]
		RT.setColumn(key, VarList)
	return RT

def try_append_to_dict(dictionary, measurement, filename, value):
	try:
		dictionary[measurement][filename].append(value)
	except KeyError:
		try:
			dictionary[measurement][filename] = [value]
		except KeyError:
			dictionary[measurement] = {filename: [value]}


def main(inputpath, outputpath, phase_channel):
	regexitem = re.compile(r"\.nd2$|\.tif{1,2}")
	filepaths = [os.path.join(inputpath, filepath) for filepath in os.listdir(inputpath) if regexitem.search(filepath)]
	OutDictionary = {}
	for filepath in filepaths:
		imp = IJ.openImage(filepath)
		phase_imp = Duplicator().run(imp, phase_channel, phase_channel, 1, imp.getNSlices(), 1, imp.getNFrames())
		# Thresholds the image
		IJ.run(phase_imp, "Convert to Mask", "method=Default background=Light calculate black")
		roi_list = analyzeParticles(phase_imp, size_min="200.00", stack=True, pixel=True)
		# This checks for any duplicates and errors out if one is found
		slicelist = [roi.getZPosition() for roi in roi_list]
		duplicates = [position for position in set(slicelist) if slicelist.count(position) > 1]
		if len(duplicates) > 0:
			IJ.log("Found duplicate ROIs at positions: " + ", ".join(map(str, duplicates)) + " in " + filepath)
			continue
		x = 0
		for roi in roi_list:
			expanded_roi = RoiEnlarger.enlarge(roi, 5)
			inverted_roi = expanded_roi.getInverse(imp)
			if imp.getNFrames() > imp.getNSlices()
				imp.setSlice(roi.getZPosition())
			else:
				imp.setT(roi.getZPosition())
			for channel in range(1, imp.getNChannels() + 1):
				imp.setRoi(roi)
				imp.setC(channel)
				x+=1
				if x==32:
					imp.show()
					return
				# Measure area and intensity
				measurements_dict = getRoiMeasurements(roi, imp, [Measurements.AREA, Measurements.MEAN])
				area = measurements_dict['Area']
				sub_dict = getRoiMeasurements(inverted_roi, imp, [Measurements.MEAN])
				if channel == phase_channel:
					mean_intensity = sub_dict['Mean'] - measurements_dict['Mean']
				else:
					mean_intensity = measurements_dict['Mean'] - sub_dict['Mean']
				try_append_to_dict(OutDictionary, "Channel-" + str(channel), filepath, mean_intensity)
			try_append_to_dict(OutDictionary, "Area", filepath, area)
		imp.close()
	for measurement in OutDictionary:
		RT = dict2ResultsTable(OutDictionary[measurement])
		RT.save(os.path.join(outputpath, measurement + ".csv"))

if __name__ == "__main__":
	InPath = InDir.getPath()
	OutPath = OutFile.getPath()
	main(InPath, OutPath, Phase_Channel)