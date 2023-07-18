## Authors: Dr James Grimshaw | Newcastle University | james.grimshaw@newcastle.ac.uk
## This Fiji macro runs in Jython and allows the user to select random fields within an image

import os, re, random
from ij import IJ
from ij.gui import GenericDialog
from ij.io import FileSaver
from loci.plugins import BF
from loci.plugins.in import ImporterOptions
from loci.formats import ImageReader

def getRandomField(Image, CropSize, ImageScale):
	ImageWidth = Image.getWidth()
	ImageHeight = Image.getHeight()
	ScaledWidth = round(ImageWidth * ImageScale)
	ScaledHeight = round(ImageHeight * ImageScale)
	# Creates a random number between 0 and the width/height minus the size of the crop
	rand_x = random.randrange(0, ScaledWidth - CropSize)
	rand_y = random.randrange(0, ScaledHeight - CropSize)
	# Creates the string for the settings for the specify command
	settings = "width="+str(CropSize)+" height="+str(CropSize)+" x="+str(rand_x)+" y="+str(rand_y)+" scaled"
	return settings


# Defines the pattern for searching for nd2 files
Extension_Pattern = r'\.nd2$'

# Creates dialog that will get input/output folders and settings for splitting channels and timepoints
GD = GenericDialog("Random Area Crop")
GD.addDirectoryField("Input:", '')
GD.addDirectoryField("Output:", '')
GD.addNumericField("Size (um):", 20)
GD.addNumericField("Pixel Size (um):", 0.065)
GD.showDialog()

# Gets the directory paths for input/output folders
ImagesDir = GD.getNextString()
SaveDirPath = GD.getNextString()
Size = GD.getNextNumber()
Scale = GD.getNextNumber()

if os.path.exists(ImagesDir) and os.path.exists(SaveDirPath):
	FileList = []
	for FileName in os.listdir(ImagesDir):
		# Uses regular expressions to find tif/tiff extensions
		if re.search(Extension_Pattern, FileName, flags=re.IGNORECASE):		
			# Splits the filename from extension to label the data
			Split_Filename = re.split(Extension_Pattern, FileName, flags=re.IGNORECASE)
			FileList.append([FileName, Split_Filename[0]])

	if len(FileList) > 0:
		for FoundFile in FileList:
			FilePath = os.path.join(ImagesDir, FoundFile[0])
			# BioFormats ImporterOptions constructor
			Options = ImporterOptions()
			# Selects the files path to be imported
			Options.setId(FilePath)
			# ImageReader constructor to get metadata
			reader = ImageReader()
			# Trys to select the file to pull out the metadata
			reader.setId(FilePath)
			# Gets the SeriesCount so can generate range to iterate though series
			SeriesCount = reader.getSeriesCount()
			# Iterates though all series in image (will only do one if there isnt a series)
			for series in range(0, SeriesCount):
				# Will show progress though series of images
				if SeriesCount > 1:
					IJ.showProgress(series, SeriesCount)
				reader.setSeries(series)
				# Gets the name of the series
				SeriesName = reader.getSeriesMetadataValue('Image name')
				# Selects the series for import
				Options.setSeriesOn(series, True)
				# Opens the images with BioFormats
				Import = BF.openImagePlus(Options)
				for Imp in Import:
					Settings = getRandomField(Imp, Size, Scale)
					## Runs specify command to create ROI
					IJ.run(Imp, "Specify...",Settings)
					## Runs crop command to crop the image
					Cropped = Imp.crop("stack")
					## Closes the full size image
					Imp.close()
					SaveObj = FileSaver(Cropped)
					# Saves the image as a Tiff
					FinalSavePath = os.path.join(SaveDirPath, FoundFile[1]+".TIF")
					SaveObj.saveAsTiff(FinalSavePath)
				## Will remove existing series so wont just save the first file over and over again
				Options.clearSeries()
		IJ.error("Done")
	else:
		IJ.error("No files in target directory")
else:
	IJ.error("Valid directory not selected")
