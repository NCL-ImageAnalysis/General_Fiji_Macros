## Authors: Dr James Grimshaw | Newcastle University | james.grimshaw@newcastle.ac.uk
## This Fiji macro runs in Jython and will save all cropped images of Rois in the Roi manager for the selected image (useful for stacks)

import os, sys, re
from ij import IJ
from ij.plugin.frame import RoiManager
from ij.io import DirectoryChooser, FileSaver

# Accesses current image
imp = IJ.getImage()

# Dialog where user chooses where to save their Images
SaveGUI = DirectoryChooser('Choose where to save your Images')
SaveDirPath = SaveGUI.getDirectory()
if SaveDirPath == None:
	sys.exit('No Directory Selected')

# Gets the ROI Manager
RM = RoiManager.getInstance()
if RM == None:
	sys.exit('No ROIs Available')

# Gets indexes of ROI
RM.deselect()
Ind = RM.getIndexes()

# Goes through all the rois in the manager and saves the cropped image
for Index in Ind:
	# Selects roi based on current index
	RM.select(imp, Index)
	# Copys the image using the roi
	IJ.run(imp, "Duplicate...", "use")
	# Selects the new image
	Cropped = IJ.getImage()
	# Gets the title of the image to save it
	Title = Cropped.getTitle()
	CorrectedTitle = re.sub(r'[<>:"/\|?*]', "-", Title)
	# Defines the save path
	Savepath = os.path.join(SaveDirPath, CorrectedTitle+".tif")
	# Iterable for filename
	ii = 1
	# This loop will add a number
	while os.path.exists(Savepath):
		# Converts iterable into a string
		strii = str(ii)
		# Gets the length of the string iterable and if it is less than 3 digits will add leading "0" up to 3 digits 
		strii = "0" * (3 - len(strii)) + strii
		# Adds the iterable to the filename
		Savepath = os.path.join(SaveDirPath, CorrectedTitle + "_" + strii + ".tif")
		# Increments up the iterable
		ii += 1

	# Saves and closes the cropped image
	FileSaver(Cropped).saveAsTiff(Savepath)
	Cropped.close()

