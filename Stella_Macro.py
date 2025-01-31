#@ File (label="Input Image:", style="file") InputFile
#@ File (label="Output csv file:", style="file") OutputFile
#@ Float (label="Max Nuclei Radius - Rolling Ball:", style="format:#####.#####") Nuceli_RollingBall
#@ String (label="Nuclei Analyze Particles Size Setting:") Nuclei_Size_Setting
#@ String (label="Nuclei Analyze Particles Circularity Setting:") Nuclei_Circularity_Setting
#@ Integer (label="Nuclei Channel:") Nuclei_Chan
#@ Integer (label="RAD51 Channel:") RAD_Chan
#@ Integer (label="yH2AX Channel:") yH2AX_Chan
#@ Float (label="RAD51 foci size - Rolling Ball:", style="format:#####.#####") RAD_Foci_RollingBall
#@ Float (label="RAD51 foci prominence:", style="format:#####.#####") RAD_Foci_Prominence
#@ Float (label="yH2AX foci size - Rolling Ball:", style="format:#####.#####") yH2AX_Foci_RollingBall
#@ Float (label="yH2AX foci prominence:", style="format:#####.#####") yH2AX_Foci_Prominence
#@ File (label="Kernel File:", style="file") KernelFile
#@ Boolean (label="Test Mode", value=false) TestMode

from ij import IJ
from ij.gui import GenericDialog, NonBlockingGenericDialog, DialogListener, Overlay, PointRoi
from ij.plugin import ChannelSplitter
from ij.plugin.filter import MaximumFinder, PlugInFilter, PlugInFilterRunner

from loci.plugins import BF
from loci.plugins.in import ImporterOptions
from loci.formats import ImageReader
from loci.formats.services import OMEXMLServiceImpl

import re

class NucleiDialogListener(DialogListener):
	"""Dialog Listner for testing nuclei settings"""
	def __init__(self, AnalysisInstance):
		"""Initializes the dialog listener"""
		# Gives the listener access to the AnalysisInstance
		self.AnalysisInstance = AnalysisInstance
		# Duplicates the processor to keep the original image intact
		self.processor = AnalysisInstance.TestImage.getProcessor().duplicate()

	def dialogItemChanged(self, gd, event):
		"""Method that is called when the dialog is changed"""
		if gd.isPreviewActive():
			# If the preview is active, update the nuclei settings
			self.updateNuclei(gd)
		else:
			# Otherwise just set the processor back to the original image
			self.AnalysisInstance.TestImage.setProcessor(self.processor.duplicate())
		return True
	
	def updateNuclei(self, gd):
		"""Method that updates the nuclei settings and processed image"""
		AnalysisInstance = self.AnalysisInstance
		# Getting the old rolling ball size to check if it has changed
		OldNucleiBall = AnalysisInstance.Nuclei_rollingball
		# Getting the new settings from the dialog
		AnalysisInstance.Nuclei_rollingball = gd.getNextNumber()
		AnalysisInstance.size_setting = gd.getNextString()
		AnalysisInstance.circularity_setting = gd.getNextString()
		# Checking if the settings are valid-------------------------------------------v
		# Matches a number followed by a dash followed by a number or inf
		regex = r"^\d+-\d+$|^\d+-inf$"
		if not re.match(regex, AnalysisInstance.size_setting):
			return
		if not re.match(regex, AnalysisInstance.circularity_setting):
			return
		# Splits the strings into lists of floats
		splitSize = [float(x) for x in AnalysisInstance.size_setting.split("-")]
		splitCirc = [float(x) for x in AnalysisInstance.circularity_setting.split("-")]
		# Checks that the first number is smaller than the second
		if splitSize[0] > splitSize[1] or splitCirc[0] > splitCirc[1]:
			return
		# Checks that they are not less than 0
		if splitSize[0] < 0 or splitCirc[0] < 0:
			return
		# Checks that circularity is not greater than 1
		if splitCirc[1] > 1:
			return
		#------------------------------------------------------------------------------^
		Image = AnalysisInstance.TestImage
		# Only update the image if the rolling ball size has changed
		if OldNucleiBall != AnalysisInstance.Nuclei_rollingball:
			# Starting from original processor
			Image.setProcessor(self.processor.duplicate())
			# Getting the rois
			self.AnalysisInstance.makeNucleiBinary()
			self.AnalysisInstance.analyzeParticles()
			# Setting back to the original processor so can just subtract the background
			Image.setProcessor(self.processor.duplicate())
			# Getting the scaled rolling ball size
			ScaledNucleiBall = int(AnalysisInstance.Nuclei_rollingball / AnalysisInstance.scale)
			# Subtracting the background
			IJ.run(Image, "Subtract Background...", "rolling=" + str(ScaledNucleiBall))
		# Otherwise just update analyze particles
		else:
			try:
				self.AnalysisInstance.analyzeParticles()
			# If the analyze particles has not been run yet, run it
			except AttributeError:
				self.AnalysisInstance.makeNucleiBinary()
				self.AnalysisInstance.analyzeParticles()
		# Clearing the old overlay
		OldOverlay = Image.getOverlay()
		if OldOverlay:
			OldOverlay.clear()
		# Updating the new overlay
		TempRoiList = self.AnalysisInstance.RoiList
		OverlayedNuclei = Overlay()
		for roi in TempRoiList:
			OverlayedNuclei.add(roi)
		Image.setOverlay(OverlayedNuclei)

class FociDialogListener(DialogListener):
	"""Dialog Listener for testing foci settings"""
	def __init__(self, AnalysisInstance, Channel):
		"""Initializes the dialog listener"""
		# Gives the listener access to the AnalysisInstance
		self.AnalysisInstance = AnalysisInstance
		# Duplicates the processor to keep the original image intact
		self.processor = AnalysisInstance.TestImage.getProcessor().duplicate()
		# Adds the channel to the listener
		self.Channel = Channel
		# Sets the run once to false to ensure that the foci are counted at least once
		self.RunOnce = False
		# Sets the correct rolling ball size and noise based on the channel
		if Channel == "RAD51":
			self.BallSize = AnalysisInstance.RAD_foci_rollingball
			self.Noise = AnalysisInstance.RAD_foci_prominence
		elif Channel == "yH2AX":
			self.BallSize = AnalysisInstance.yH2AX_foci_rollingball
			self.Noise = AnalysisInstance.yH2AX_foci_prominence
	
	def dialogItemChanged(self, gd, event):
		"""Method that is called when the dialog is changed"""
		if gd.isPreviewActive():
			# If the preview is active, update the foci settings
			self.updateFoci(gd)
		else:
			# Otherwise just set the processor back to the original image
			self.AnalysisInstance.TestImage.setProcessor(self.processor.duplicate())
		return True
	
	def updateFoci(self, gd):
		"""Method that updates the foci settings and processed image"""
		AnalysisInstance = self.AnalysisInstance
		Image = AnalysisInstance.TestImage
		# Getting the old rolling ball size and noise to check if they have changed
		oldBall = self.BallSize
		oldNoise = self.Noise
		# Getting the new settings from the dialog
		self.BallSize = gd.getNextNumber()
		self.Noise = gd.getNextNumber()
		self.DisplayMode = gd.getNextChoice()
		# Only update the image if the rolling ball size has changed or if it has not been run yet
		if oldBall != self.BallSize or self.RunOnce is False:
			self.FociRoi = AnalysisInstance.countFoci(self.Channel, "roi")
			# Sets the run once to true so that subtraction is not done again unless settings have changed
			self.RunOnce = True
		# Otherwise will only recalulate the foci if the noise has changed
		elif oldNoise != self.Noise:
			self.FociRoi = AnalysisInstance.runMaxima(Image, self.Noise, "roi")
		# Clearing the old overlay
		OldOverlay = Image.getOverlay()
		if OldOverlay:
			OldOverlay.clear()
		# Updating the new overlay
		OverlayedFoci = Overlay()
		OverlayedFoci.add(self.FociRoi)
		Image.setOverlay(OverlayedFoci)
		# Sets the image processor to the selected display mode
		if self.DisplayMode == "Subtracted":
			DisplayProcessor = AnalysisInstance.SubbedProcessor.duplicate()
		elif self.DisplayMode == "Convolved":
			DisplayProcessor = AnalysisInstance.ConvolvedProcessor.duplicate()
		Image.setProcessor(DisplayProcessor)

class HomologousRecombinationAnalysis(PlugInFilter):
	"""Class that runs the analysis for homologous recombination"""
	def __init__(self,
			  	 NucleiImage,
				 RADImage,
				 yH2AXImage,
				 Nuclei_rollingball,
				 size_setting,
				 circularity_setting,
				 RAD_foci_rollingball,
				 RAD_foci_prominence,
				 yH2AX_foci_rollingball,
				 yH2AX_foci_prominence,
				 kernel,
				 scale,
				 testmode=False):
		"""Constructor for the analysis class

		Args:
			NucleiImage (ij.ImagePlus): Single channel nuclei image
			RADImage (ij.ImagePlus): Single channel RAD51 image
			yH2AXImage (ij.ImagePlus): Single channel yH2AX image
			Nuclei_rollingball (float): Size of the rolling ball for nuclei background subtraction in scaled units
			size_setting (str): Analyze particles size setting
			circularity_setting (str): Analyze particles circularity setting
			RAD_foci_rollingball (float): Size of the rolling ball for RAD51 foci background subtraction in scaled units
			RAD_foci_prominence (int): Minimum intensity of RAD51 foci in convolved image
			yH2AX_foci_rollingball (float): Size of the rolling ball for yH2AX foci background subtraction in scaled units
			yH2AX_foci_prominence (int): Minimum intensity of yH2AX foci in convolved image
			kernel (str): Pattern for convolving the images
			scale (float): Physical size of a pixel in microns
			testmode (bool, optional): Whether or not to run the macro in settings test mode. Defaults to False.
		"""
		self.NucleiImage = NucleiImage
		self.RADImage = RADImage
		self.yH2AXImage = yH2AXImage
		self.Nuclei_rollingball = Nuclei_rollingball
		self.size_setting = size_setting
		self.circularity_setting = circularity_setting
		self.RAD_foci_rollingball = RAD_foci_rollingball
		self.RAD_foci_prominence = RAD_foci_prominence
		self.yH2AX_foci_rollingball = yH2AX_foci_rollingball
		self.yH2AX_foci_prominence = yH2AX_foci_prominence
		self.kernel = kernel
		self.scale = scale
		self.testmode = testmode

	def setup(self, arg, imp):
		"""Required method for PlugInFilter"""
		return PlugInFilter.NO_IMAGE_REQUIRED | PlugInFilter.DONE

	def run(self, ip):
		"""Required method for PlugInFilter"""
		pass

	def runMacro(self):
		"""Method that runs the macro"""
		if self.testmode:
			self.test()
		else:
			self.analyze()

	def makeNucleiBinary(self):
		"""Preprocesses and segments the nuclei image"""
		# Duplicates the nuclei image to keep the original intact
		self.NucleiBinary = self.NucleiImage.duplicate()
		# Subtracts the background from the nuclei image 
		# Rolling ball size is scaled to the image and then rounded to an integer
		IJ.run(self.NucleiBinary, 
		 		"Subtract Background...", 
				"rolling=" + str(int(self.Nuclei_rollingball/self.scale)))
		# Saves the processor to be used later if needed for test mode
		self.SubbedProcessor = self.NucleiBinary.getProcessor().duplicate()
		# Segmentation steps
		IJ.run(self.NucleiBinary, "Smooth", "")
		IJ.run(self.NucleiBinary, "Make Binary", "")
		IJ.run(self.NucleiBinary, "Dilate", "")
		IJ.run(self.NucleiBinary, "Fill Holes", "")
		IJ.run(self.NucleiBinary, "Median...", "radius=3")
		IJ.run(self.NucleiBinary, "Watershed", "")

	def analyzeParticles(self):
		"""Runs the analyze particles command on the nuclei image"""
		# Defines analyse particles settings
		AnalyzeParticlesSettings = (
			"size=" 
			+ self.size_setting 
			+ " circularity=" 
			+ self.circularity_setting 
			+ " clear overlay exclude"
		)
		# Runs the analyze particles command to get ROI. 
		# Done by adding to the overlay in order to not have ROIManger shown to user
		IJ.run(self.NucleiBinary, "Analyze Particles...", AnalyzeParticlesSettings)
		# Gets the Overlayed ROIs from analyze particles
		Overlayed_Rois = self.NucleiBinary.getOverlay()
		# Takes the overlay and turns it into an array of ROI
		RoiList = Overlayed_Rois.toArray()
		# Removes this overlay to clean up the image
		IJ.run(self.NucleiBinary, "Remove Overlay", "")
		self.RoiList = RoiList

	def runMaxima(self, Image, noise, mode="number"):
		"""Runs the maxima finder on the image for each nuclei"""
		pointlist = []
		# Iterates through each nuclei ROI
		for roi in self.RoiList:
			Image.setRoi(roi)
			# Gets the maxima for each ROI and appends it as a java.awt.Polygon
			Polygon = MaximumFinder().getMaxima(Image.getProcessor(), noise, False)
			pointlist.append(Polygon)
		# If just number is needed, gets the number of points in each polygon
		if mode == "number":
			return [point.npoints for point in pointlist]
		# If ROI is needed, converts the java.awt.Polygon to a PointRoi
		elif mode == "roi":
			x = []
			y = []
			for point in pointlist:
				x += point.xpoints
				y += point.ypoints
			return PointRoi(x, y)

	def countFoci(self, Channel, mode="number"):
		"""Preprocesses and counts the foci in the image

		Args:
			Channel (str): The channel to be analyzed. Must be either "RAD51" or "yH2AX"
			mode (str, optional): Whether to return the foci ROI or number of foci. Defaults to "number".

		Returns:
			int or ij.gui.PointRoi: Either the number of foci per nuclei or the foci ROI for all nuclei
		"""
		# Sets the image and the rolling ball size and noise based on the channel
		if Channel == "RAD51":
			Image = self.RADImage
			ballsize = self.RAD_foci_rollingball
			noise = self.RAD_foci_prominence
		elif Channel == "yH2AX":
			Image = self.yH2AXImage
			ballsize = self.yH2AX_foci_rollingball
			noise = self.yH2AX_foci_prominence
		# Checks if the channel is valid
		else:
			raise ValueError("Channel must be either RAD51 or yH2AX")
		# Checks if the mode is valid
		if mode != "number" and mode != "roi":
			raise ValueError("Mode must be either number or roi")
		# Subtracts the background from the image
		# Rolling ball size is scaled to the image and then rounded to an integer
		IJ.run(Image, "Subtract Background...", "rolling=" + str(int(ballsize/self.scale)))
		# Saves the processor to be used later if needed for test mode
		self.SubbedProcessor = Image.getProcessor().duplicate()
		# Convolve the image with the kernel
		IJ.run(Image, "Convolve...", "text1=[" + self.kernel +"]")
		# Saves the processor to be used later if needed for test mode
		self.ConvolvedProcessor = Image.getProcessor().duplicate()
		# Gets the maxima for each nuclei from this processed image and returns it
		return self.runMaxima(Image, noise, mode)
	
	def testNuclei(self):
		"""Allows the user to interactively test the nuclei settings"""
		# Duplicates the nuclei image to keep the original intact
		self.TestImage = self.NucleiImage.duplicate()
		# Shows the image to the user
		self.TestImage.show()
		# Creates a dialog for the user to interact with-----------------------------------v
		NucleiDialog = NonBlockingGenericDialog("Nuclei Settings")
		NucleiDialog.addNumericField("Nuclei Rolling Ball Size", self.Nuclei_rollingball)
		NucleiDialog.addStringField("Nuclei Size Setting", self.size_setting)
		NucleiDialog.addStringField("Nuclei Circularity Setting", self.circularity_setting)
		# Adds a preview checkbox to the dialog
		pfr = PlugInFilterRunner(self, "Nuclei Settings", "")
		NucleiDialog.addPreviewCheckbox(pfr)
		# Adds a dialog listener to the dialog
		Listener = NucleiDialogListener(self)
		NucleiDialog.addDialogListener(Listener)
		NucleiDialog.showDialog()
		#----------------------------------------------------------------------------------^
		# If the dialog is canceled, closes the image and returns False
		if NucleiDialog.wasCanceled():
			# Sets the changes to false so that the user is not prompted to save
			self.TestImage.changes = False
			self.TestImage.close()
			return False
		# If the dialog is not canceled, updates the nuclei settings
		self.Nuclei_rollingball = NucleiDialog.getNextNumber()
		self.size_setting = NucleiDialog.getNextString()
		self.circularity_setting = NucleiDialog.getNextString()
		# Generates the nuclei roi for testing foci
		self.makeNucleiBinary()
		self.analyzeParticles()
		# Closes the images and returns True
		# Sets the changes to false so that the user is not prompted to save
		self.TestImage.changes = False
		self.TestImage.close()
		return True
	
	def testFoci(self, Channel):
		"""Allows the user to interactively test the foci settings"""
		# Sets the image, rolling ball size and noise based on the channel
		if Channel == "RAD51":
			self.TestImage = self.RADImage.duplicate()
			ballsize = self.RAD_foci_rollingball
			noise = self.RAD_foci_prominence
		elif Channel == "yH2AX":
			self.TestImage = self.yH2AXImage.duplicate()
			ballsize = self.yH2AX_foci_rollingball
			noise = self.yH2AX_foci_prominence
		# Shows the image to the user
		self.TestImage.show()
		# Creates a dialog for the user to interact with-----------------------------v
		FociDialog = NonBlockingGenericDialog("Foci Settings")
		FociDialog.addNumericField("Foci Rolling Ball Size", ballsize)
		FociDialog.addNumericField("Foci Prominence", noise)
		# This is for setting which image to look at
		FociDialog.addChoice("Preview as", ["Subtracted", "Convolved"], "Subtracted")
		# Adds a preview checkbox to the dialog
		pfr = PlugInFilterRunner(self, "Foci Settings", "")
		FociDialog.addPreviewCheckbox(pfr)
		# Adds a dialog listener to the dialog
		Listener = FociDialogListener(self, Channel)
		FociDialog.addDialogListener(Listener)
		FociDialog.showDialog()
		#----------------------------------------------------------------------------^
		# Closes the image
		# Need to set changes to false so that the user is not prompted to save
		self.TestImage.changes = False
		self.TestImage.close()
		# If the dialog is canceled, returns False
		if FociDialog.wasCanceled():
			return False
		# If the dialog is not canceled, updates the foci settings 
		# depending on the channel and returns True
		if Channel == "RAD51":
			self.RAD_foci_rollingball = FociDialog.getNextNumber()
			self.RAD_foci_prominence = FociDialog.getNextNumber()
		elif Channel == "yH2AX":
			self.yH2AX_foci_rollingball = FociDialog.getNextNumber()
			self.yH2AX_foci_prominence = FociDialog.getNextNumber()
		return True

	def test(self):
		"""Method that runs the test mode"""
		# Tests the nuclei and foci settings
		# If returns False, then the user has 
		# canceled the dialog and the method will end
		if not self.testNuclei():
			return
		if not self.testFoci("RAD51"):
			return
		if not self.testFoci("yH2AX"):
			return
		# Prints the settings to the log
		IJ.log("Nuclei Rolling Ball Size: " + str(self.Nuclei_rollingball))
		IJ.log("Nuclei Size Setting: " + self.size_setting)
		IJ.log("Nuclei Circularity Setting: " + self.circularity_setting)
		IJ.log("RAD51 Rolling Ball Size: " + str(self.RAD_foci_rollingball))
		IJ.log("RAD51 Prominence: " + str(self.RAD_foci_prominence))
		IJ.log("yH2AX Rolling Ball Size: " + str(self.yH2AX_foci_rollingball))
		IJ.log("yH2AX Prominence: " + str(self.yH2AX_foci_prominence))

	def analyze(self):
		"""Method that runs the analysis"""
		# Preprocesses and segments the nuclei image
		self.makeNucleiBinary()
		# Runs analyze particles on the nuclei image to get nuclei roi
		self.analyzeParticles()
		# Counts the foci for each nuclei for the RAD51 and yH2AX channels
		self.RAD51_PointList = self.countFoci("RAD51")
		self.yH2AX_PointList = self.countFoci("yH2AX")

def saveResults(OutputDict, csvfile):
	"""Saves the results to a csv file"""
	# Sorts the keys so that the output is in the correct order
	sortedkeys = sorted(OutputDict.keys())
	# Writes the column titles to the csv file
	csvfile.write(",".join(sortedkeys) + "\n")
	cont = True
	index = 0
	# Iterates through the output dictionary and writes the results to the csv file
	while cont:
		# Initially sets continue to False
		cont = False
		# Default is an empty string
		line = ""
		for key in sortedkeys:
			# Checks if there is a list item for this index
			if index < len(OutputDict[key]):
				# If so will run the loop again
				cont = True
				# Adds the item to the line with a comma
				line += str(OutputDict[key][index]) + ","
			# Otherwise just adds a comma
			else:
				line += ","
		# Writes the line to the csv file
		csvfile.write(line + "\n")
		# Increments the index
		index += 1

def main(imagepath,
		 outputpath,
		 Nuclei_rollingball,
		 size_setting,
		 circularity_setting,
		 nuclei_channel,
		 RAD_channel,
		 yH2AX_channel,
		 RAD_foci_rollingball,
		 RAD_foci_prominence,
		 yH2AX_foci_rollingball,
		 yH2AX_foci_prominence,
		 kernel_file,
		 testmode):
	"""Main function that runs the analysis/testing

	Args:
		imagepath (str): Path to the image
		outputpath (str): Path to the output csv file
		Nuclei_rollingball (Float): Size of the rolling ball for nuclei background subtraction in scaled units
		size_setting (str): Size setting for nuclei analyze particles
		circularity_setting (str): Circularity setting for nuclei analyze particles
		nuclei_channel (int): Channel number for nuclei
		RAD_channel (int): Channel number for RAD51
		yH2AX_channel (int): Channel number for yH2AX
		RAD_foci_rollingball (float): Size of the rolling ball for RAD51 foci background subtraction in scaled units
		RAD_foci_prominence (float): Minimum intensity of RAD51 foci in convolved image
		yH2AX_foci_rollingball (float): Size of the rolling ball for yH2AX foci background subtraction in scaled units
		yH2AX_foci_prominence (float): Minimum intensity of yH2AX foci in convolved image
		kernel_file (str): Path to the kernel file for convolving the images
		testmode (bool): Whether or not to run the macro in settings test mode
	"""
	
	# Initialises the metadata reader
	MetaReader = ImageReader()
	Metadata = OMEXMLServiceImpl().createOMEXMLMetadata()
	MetaReader.setMetadataStore(Metadata)
	MetaReader.setId(imagepath)
	# Initialises the importer options and adds image path
	Options = ImporterOptions()
	Options.setId(imagepath)
	# Generates dialog for selecting image series to use
	GD = GenericDialog("Select Image Series to Process")
	NameList = [Metadata.getImageName(i) for i in range(MetaReader.getSeriesCount())]
	# If in test mode none will be selected by default
	if testmode:
		GD.addCheckboxGroup(len(NameList), 1, NameList, [False] * len(NameList))
	# Otherwise all will be selected by default
	else:
		GD.addCheckboxGroup(len(NameList), 1, NameList, [True] * len(NameList))
	GD.showDialog()
	# If the dialog is canceled, returns and terminates the macro
	if GD.wasCanceled():
		return
	# Iterates through the selected series and sets on for import
	for i in range(MetaReader.getSeriesCount()):
		if GD.getNextBoolean():
			Options.setSeriesOn(i, True)
		else:
			Options.setSeriesOn(i, False)
	# Imports the image series'
	Import = BF.openImagePlus(Options)
	# Reads the kernel file
	kernel = open(kernel_file).read()
	# Initialises the output dictionary
	OutputDict = {}
	# Iterates through the series and runs the analysis
	for series, Image in enumerate(Import):
		# Shows the progress of the analysis
		IJ.showProgress(series, len(Import))
		# Gets the physical size of the pixels
		scale = Metadata.getPixelsPhysicalSizeX(series).value()
		# Splits the image into channels
		Channels = ChannelSplitter.split(Image)
		# Initialises the analysis class
		Analysis = HomologousRecombinationAnalysis(Channels[nuclei_channel-1],
											 		Channels[RAD_channel-1],
													Channels[yH2AX_channel-1],
													Nuclei_rollingball,
													size_setting,
													circularity_setting,
													RAD_foci_rollingball,
													RAD_foci_prominence,
													yH2AX_foci_rollingball,
													yH2AX_foci_prominence,
													kernel,
													scale,
													testmode
													)
		# Runs the analysis
		Analysis.runMacro()
		# Closes the channels and the original image
		for Channel in Channels:
			Channel.close()
		Image.close()
		# Adds the results to the output dictionary
		try:
			OutputDict[Image.getTitle() + " RAD51"] = Analysis.RAD51_PointList
			OutputDict[Image.getTitle() + " yH2AX"] = Analysis.yH2AX_PointList
		# Except will catch if the analysis has not been run
		except AttributeError:
			continue	
	if not testmode:
		LineList = ["Nuclei_rollingball=" + str(Nuclei_rollingball),
						"Nuclei_Size_Setting=" + size_setting,
						"Nuclei_Circularity_Setting=" + circularity_setting,
						"Nuclei_Chan=" + str(nuclei_channel),
						"RAD51_Chan=" + str(RAD_channel),
						"yH2AX_Chan=" + str(yH2AX_channel),
						"RAD51_RollingBallSize=" + str(RAD_foci_rollingball),
						"RAD51_Prominence=" + str(RAD_foci_prominence),
						"yH2AX_RollingBallSize=" + str(yH2AX_foci_rollingball),
						"yH2AX_Prominence=" + str(yH2AX_foci_prominence),
						"KernelFile=" + kernel_file]
		# Checks if the output path has a csv extension and adds it if not
		if not re.search(r"\.csv$", outputpath, re.IGNORECASE):
			outputpath += ".csv"
		# Opens the csv file in write mode
		csvfile = open(outputpath, "w")
		# Writes the settings to the first line of the csv file
		csvfile.write(",".join(LineList) + "\n")
		# Writes the results to the csv file
		saveResults(OutputDict, csvfile)
		# Closes the csv file
		csvfile.close()


if __name__ == "__main__":
	main(InputFile.getPath(), 
	  	 OutputFile.getPath(), 
		 Nuceli_RollingBall,
		 Nuclei_Size_Setting,
		 Nuclei_Circularity_Setting,
		 Nuclei_Chan,
		 RAD_Chan,
		 yH2AX_Chan,
		 RAD_Foci_RollingBall,
		 RAD_Foci_Prominence,
		 yH2AX_Foci_RollingBall,
		 yH2AX_Foci_Prominence,
		 KernelFile.getPath(),
		 TestMode
		)