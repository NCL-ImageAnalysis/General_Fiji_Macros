#@ File (label="Input:", style="directory") InputFolder

# Python Imports
import os
# ImageJ Imports
from ij import IJ
from ij.plugin import ImagesToStack
# Bioformats Imports
from loci.plugins import BF
from loci.plugins.in import ImporterOptions


mainpath = InputFolder.getPath()
# Get the list of files in the input directory
files = os.listdir(mainpath)
listlist = []
# Loop over the files
for file in files:
	# BioFormats ImporterOptions constructor
	Options = ImporterOptions()
	# Selects the files path to be imported
	Options.setId(os.path.join(mainpath, file))
	# Sets BioFormats to split channels
	Options.setSplitChannels(True)
	# Imports the image as an array of ImagePlus objects
	Import = BF.openImagePlus(Options)

	for i, image in enumerate(Import):
		try:
			listlist[i].append(image)
		except IndexError:
			listlist.append([image])
for listobj in listlist:
	Stack = ImagesToStack.run(listobj)
	Stack.show()
	IJ.resetMinAndMax(Stack)



