## Authors: Dr James Grimshaw | Newcastle University | james.grimshaw@newcastle.ac.uk
## This Fiji macro runs in Jython and allows the user to subtract the background fluorescence of a field of view, segmented using phase contrast
## This macro takes TIF files with channels labelled _w1 for phase contrast and _w2/w3/w4 for other channels

from ij import IJ, ImagePlus, WindowManager
from ij.plugin import RoiEnlarger
from ij.plugin.frame import RoiManager
from ij.plugin.filter import Analyzer
from ij.measure import ResultsTable
from ij.gui import GenericDialog, NonBlockingGenericDialog
from ij.io import DirectoryChooser, FileSaver
import sys, os, re

## This function pulls out all the TIF files and uses re to determine if its wavelength 1 (phase contrast) or any other (fluorescence) and adds it to a dictionary
## Key is the filename without the channel info and contains a list with the phase contrast filename in the first position and a list of other wavelengths in the second position
def getWavelengthDict(List_of_Files):
	WavelengthDict = {}
	for image_filename in List_of_Files:
		if re.search('\.tif{1,2}$', image_filename, flags = re.IGNORECASE):
				get_wavelength = image_filename.split('_')
				common_filename = '_'.join(get_wavelength[0:-1])
				if common_filename not in WavelengthDict:
					WavelengthDict[common_filename] = ['', []]
				if re.match('w1', get_wavelength[-1], \A):			 
					WavelengthDict[common_filename][0] = image_filename
				elif re.match('w[2-9]', get_wavelength[-1], \A):
					WavelengthDict[common_filename][1].append(image_filename)
				else:
					sys.exit('Unknown File Detected')
	return WavelengthDict

## Gets the original settings for measurements
original_setting = Analyzer().getMeasurements()
## Sets measurements taken to mean only
Analyzer().setMeasurements(2)

## Opens a dialog that lets user choose the folder containing images they want to analyse-v
Dialogue_1 = DirectoryChooser("Choose Folder Containing Images")
image_dir = Dialogue_1.getDirectory()
## Will escape if Cancel is hit and no file is chosen
if image_dir == None:
	sys.exit('Image Not Chosen')
## Opens a dialog that lets user choose the folder containing images they want to analyse-^

## Opens dialog that lets user choose where to save their image
save_dir = DirectoryChooser("Choose Save Location").getDirectory()
## Will escape if Cancel is hit and no file is chosen
if save_dir == None:
	sys.exit('Save Location Not Chosen')
## Will escape if save location matches original image location
if save_dir == image_dir:
	sys.exit('Choose Different Save Location to Original Image Location')

file_list = os.listdir(image_dir)

image_dict = getWavelengthDict(file_list)


## Allows user to input size restrictions for Particle analysis
settings_dialog = GenericDialog("Input Size Restrictions")
settings_dialog.addMessage("Input size constraints for particle analysis (pixels^2)")
settings_dialog.addStringField("Minimum", "0")
settings_dialog.addStringField("Maximum", "Infinity")
settings_dialog.showDialog()
minsize = settings_dialog.getNextString()
maxsize = settings_dialog.getNextString()
if settings_dialog.wasCanceled():
	sys.exit('Cancelled')

ConfirmAll = False
for image_set in image_dict:
	## Creates path for getting to phase contrast image
	phase_path = image_dir+image_dict[image_set][0]
	phase_img = ImagePlus(phase_path)
	## Runs the Threshold command setting it to having a white background
	IJ().run(phase_img, "Threshold...", "BlackBackground=False")
	## Uses default settings for Threshold
	IJ().setAutoThreshold(phase_img, "Default")
	## Selects the Threshold Window
	IJ.selectWindow("Threshold")
	## Runs the make binary function
	IJ().run(phase_img, "Convert to Mask", "")
	## Closes the Threshold window
	IJ.run("Close")
	## Creates options for Analyze particles function using user input for min and max size. Clear will remove prexisting ROI,  Add will add new ROI to ROI manager
	options = "size="+str(minsize)+"-Infinity clear include add pixel"
	## Runs the Analyze particles function
	IJ().run(phase_img, "Analyze Particles...", options)
	## Gets access to the ROI manager
	RM = RoiManager.getInstance()
	RM.deselect()
	## Combines ROI
	RM.runCommand(phase_img, "Combine")
	## enlarges combined ROI to avoid fluorescence around cell
	cur_roi = phase_img.getRoi()
	enlarged_roi = RoiEnlarger().enlarge(cur_roi, 25)
	## Inverts the ROI so selecting Background not the cells
	phase_img.setRoi(enlarged_roi)
	IJ().run(phase_img, "Make Inverse", "")
	## Clears ROI manager
	RM.reset()
	## Adds the inverted ROI to the manager
	RM.runCommand(phase_img, "Add")
	## This loop goes through all the fluorescence images and gets the mean values-------------------v
	for fluor_image_filename in image_dict[image_set][1]:
		## Opens fluor_img (but not to user)
		fluor_image_path = image_dir+fluor_image_filename
		fluor_img = ImagePlus(fluor_image_path)
		Ind2 = RM.getIndexes()
		RM.select(Ind2[0])
		RM.moveRoisToOverlay(fluor_img)
		## Creates dialog that allows users to confirm ROI generated, or repeat the analysis
		gd = NonBlockingGenericDialog('Confirm?')
		gd.enableYesNoCancel("Confirm", "Skip this Image")
		gd.addCheckbox('Automatically Confirm All', False)
		## Skips over UI elements if user confirmed all
		if ConfirmAll != True:
			fluor_img.show()
			gd.showDialog()
			## Escapes from the macro if user hits cancel
			if gd.wasCanceled():
				imagewindow = WindowManager.getCurrentWindow()
				WindowManager.setCurrentWindow(imagewindow)
				IJ.run("Close")
				IJ.selectWindow("ROI Manager")
				IJ.run("Close")
				sys.exit('Cancelled')
			elif gd.wasOKed():
				if gd.getNextBoolean() == True:
					ConfirmAll = True
			else:
				continue
		## Measures the mean of background
		measured = Analyzer(fluor_img).measure()
		## Pulls mean value out
		bgresults = Analyzer.getResultsTable()
		bgmean = bgresults.getValue(1, 0)
		## Creates setting for subtract command
		subvalue = "value="+str(bgmean)
		## Runs Subtract Command
		IJ().run(fluor_img, "Subtract...", subvalue)
		# Runs the "Remove Overlay" Command. Last item is options of which there are none
		IJ.run(fluor_img, "Remove Overlay","")
		FileSaver(fluor_img).saveAsTiff(os.path.join(save_dir, fluor_image_filename))
		fluor_img.close()

## Restores original settings for measurements
Analyzer().setMeasurements(original_setting)
## Closes the ROI Manager
IJ.selectWindow("ROI Manager")
IJ.run("Close")
## Creates a message indicating process is finished
gd = NonBlockingGenericDialog('Done')
gd.addMessage('Done')
gd.hideCancelButton()
gd.showDialog()