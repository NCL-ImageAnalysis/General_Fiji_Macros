from ij.plugin.frame import RoiManager
from ij import ImagePlus, IJ, ImageStack
from ij.io import DirectoryChooser
from ij.gui import NonBlockingGenericDialog
import sys, os, re

# Dialog where user chooses where their images should be kept
ImagesChooser = DirectoryChooser('Choose where to find your images')
ImagesDir = ImagesChooser.getDirectory()
if ImagesDir == None:
	sys.exit('No Directory Selected')

# Dialog where user chooses where to save their ROI
ImagesChooser = DirectoryChooser('Choose where to save your ROI')
ROIDir = ImagesChooser.getDirectory()
if ROIDir == None:
	sys.exit('No Directory Selected')

# Gets any open ROI manager, gets the ROI contained and closes it before starting the macro
Manager = RoiManager().getInstance()
if Manager != None:
	OldRoi = Manager.getRoisAsArray()
	Manager.reset()
else:
	Manager = RoiManager()

# Defines the pattern for searching for tif/tiff files
Extension_Pattern = r'\.tif$|\.tiff$'

image_dict = {}

for FileName in os.listdir(ImagesDir):
	# Uses regular expressions to find tif/tiff extensions
	if re.search(Extension_Pattern, FileName, flags=re.IGNORECASE):
		# Splits the filename from extension to label the data
		Split_Filename = re.split(Extension_Pattern, FileName, flags=re.IGNORECASE)
		# Gets the wavelength by splitting up the filename at the _
		get_wavelength = Split_Filename[0].split('_')
		# Gets the common filename without the wavelength by joining everything bar the wavelength back together
		common_filename = '_'.join(get_wavelength[0:-1])
		if common_filename not in image_dict:
			image_dict[common_filename]={}
		if re.match('w[1-9]', get_wavelength[-1], flags=re.IGNORECASE): #  Figure out way to put in order using W2, 3, 4 for list.
			image_dict[common_filename][get_wavelength[-1]] = os.path.join(ImagesDir, FileName)
		else:
			sys.exit('Unknown File Detected')
Prog = 0
NumFiles = len(image_dict.keys())

for Common in image_dict:
	WaveList = image_dict[Common].keys()
	WaveList.sort()
	Prog += 1
	Stack = 'NaN'
	for Wavelength in WaveList:
		Imp = ImagePlus(image_dict[Common][Wavelength])
		if Stack == 'NaN':
			Imp_Dimensions = Imp.getDimensions()
			Stack = ImageStack(Imp_Dimensions[0], Imp_Dimensions[1])
		IP = Imp.getProcessor()
		Stack.addSlice(IP)
	PlusStack = ImagePlus(Common, Stack)
	PlusStack.show()
	NB = NonBlockingGenericDialog('Save ROI?')
	NB.addMessage('Image '+str(Prog)+' of '+str(NumFiles))
	NB.enableYesNoCancel('Save ROI and Continue', 'Skip')
	NB.showDialog()
	if NB.wasOKed() == True:
		Manager.runCommand('Save', os.path.join(ROIDir, Common+'.zip'))
		Manager.reset()
		PlusStack.close()
	elif NB.wasCanceled() == True:
		sys.exit('Cancelled')
	else:
		Manager.reset()
		PlusStack.close()
		continue

