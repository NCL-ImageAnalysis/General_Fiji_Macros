import os, re, sys
from ij.io import FileSaver
from ij.io import DirectoryChooser
from loci.plugins import BF
from loci.plugins.in import ImporterOptions
from loci.formats import ImageReader, MetadataTools

# Dialog where user chooses where their images should be kept
ImagesChooser = DirectoryChooser('Choose where to find your images')
ImagesDir = ImagesChooser.getDirectory()
if ImagesDir == None:
	sys.exit('No Directory Selected')

# Dialog where user chooses where to save their data
SaveGUI = DirectoryChooser('Choose where to save your data')
SaveDirPath = SaveGUI.getDirectory()
if SaveDirPath == None:
	sys.exit('No Directory Selected')

# Defines the pattern for searching for nd2 files
Extension_Pattern = r'\.nd2$'

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
			Options.setSplitChannels(True)
			# Opens the images with BioFormats
			Import = BF.openImagePlus(Options)
			for Imp in Import:
				ImpTitle = Imp.getTitle()
				ChannelObj = re.split(r' - C=', ImpTitle, flags=re.IGNORECASE)
				Channel = str(int(ChannelObj[1])+1)
				if SeriesCount > 1:
					FinalSaveName = FoundFile[1] + '_' + SeriesName+'_w' + Channel + ".TIF"
				else:
					FinalSaveName = FoundFile[1] + '_w' + Channel + ".TIF"
				SaveObj = FileSaver(Imp)
				# Saves the image as a Tiff
				FinalSavePath = os.path.join(SaveDirPath, FinalSaveName)
				SaveObj.saveAsTiff(FinalSavePath)

