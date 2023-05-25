## Authors: Dr James Grimshaw | Newcastle University | james.grimshaw@newcastle.ac.uk
## This Fiji macro runs in Jython and allows the user to quantify mean fluorescence intensity of bacterial cells, segmented using phase contrast
## This macro takes TIF files with channels labelled _w1 for phase contrast and _w2/w3/w4 for other channels
## The user can input size filters for the analyse particles function as well as seperate out cells on the binary image using the pencil tool 

from ij import IJ, ImagePlus, WindowManager
from ij.plugin import RoiEnlarger
from ij.plugin.frame import RoiManager
from ij.plugin.filter import Analyzer
from ij.measure import ResultsTable
from ij.gui import GenericDialog,NonBlockingGenericDialog
from ij.io import DirectoryChooser,FileSaver,SaveDialog
from fiji.util.gui import GenericDialogPlus
import sys,os,re

##Gets original standard output to can restore to normal
NormOut = sys.stdout

##Gets the original settings for measurements
original_setting = Analyzer().getMeasurements()

##Opens a dialog that lets user choose the folder containing images they want to analyse-v
image_dir = DirectoryChooser("Choose Folder Containing Images").getDirectory()
##Will escape if Cancel is hit and no file is chosen
if image_dir==None:
	sys.exit('Image Not Chosen')
##Opens a dialog that lets user choose the folder containing images they want to analyse-^

##Opens a dialog that lets user choose a folder where they want to save their ROI-v
roi_dir = DirectoryChooser("Choose Where to Save ROI").getDirectory()
##Will escape if Cancel is hit and no file is chosen
if roi_dir == None:
	sys.exit('Directory Not Chosen')
##Opens a dialog that lets user choose a folder where they want to save their ROI-^

##Asks user what to save data as and where to save it
SD1 = SaveDialog('Save data as...','','.csv')
##Gets name user chose
name1 = SD1.getFileName()
##Will escape if Cancel is hit and no file is chosen
if name1 == None:
	sys.exit('Save Location Not Chosen')
##Gets path for where to save data
savepath = SD1.getDirectory()+name1

##Makes a results file based upon the users chosen savepath
ResultsFile = open(savepath,'w')
##Sets standard output to be that results file
sys.stdout = ResultsFile

file_list = os.listdir(image_dir)
image_dict = {}

WaveList = []
for CheckFilename in file_list:
	WaveObj = re.search('_w[1-9]', CheckFilename, flags=re.IGNORECASE)
	if WaveObj:
		WavelengthStr = WaveObj.group(0)[1:]
		if WavelengthStr not in WaveList:
			WaveList.append(WavelengthStr)

WaveList.sort()

##Allows user to input size restrictions for Particle analysis
settings_dialog = GenericDialog("Input Size Restrictions")
settings_dialog.addMessage("Input size constraints for particle analysis (pixels^2)")
settings_dialog.addStringField("Minimum", "0")
settings_dialog.addStringField("Maximum", "Infinity")
settings_dialog.addCheckbox("Subtract Background", True)
settings_dialog.addRadioButtonGroup("Choose Segmentation Wavelength", WaveList, 1, len(WaveList), WaveList[0])
settings_dialog.addRadioButtonGroup("Segmentation Type", ["Phase Contrast", "Fluorescence"], 1, 2, "Phase Contrast")
settings_dialog.showDialog()
minsize = settings_dialog.getNextString()
maxsize = settings_dialog.getNextString()
SubBackground = settings_dialog.getNextBoolean()
BrightWave = settings_dialog.getNextRadioButton()
SegmentationType = settings_dialog.getNextRadioButton()
if settings_dialog.wasCanceled():
	sys.exit('Cancelled')


##This loop pulls out all the TIF files and uses re to determine if its wavelength 1 (phase contrast) or any other (fluorescence) and adds it to a dictionary-----------v
for image_filename in file_list:
	## This checks that the file is a tif/tiff file		
	if re.search('\.tif{1,2}$', image_filename, flags=re.IGNORECASE):
		WavelengthIndex = None
		## Splits by underscore to find the wavelength
		get_wavelength = image_filename.split('_')
		## Iterates through split filename to get wavelength list item
		for w in range(0, len(get_wavelength)):
			if re.match('w[1-9]', get_wavelength[w], flags=re.IGNORECASE):
				WavelengthIndex = w
				break
		## Checks that it has actually found a wavelength for this file
		if WavelengthIndex:
			## Gets the list item for determining wavelength
			Wavelength = get_wavelength[WavelengthIndex]
			## Deletes the item with the wavelength info so can generate common filename
			get_wavelength.pop(WavelengthIndex)
			## Common filename will act as the dictionary key in image_dict
			common_filename = '_'.join(get_wavelength)
			## Adds the dictionary item if it does not exist
			if common_filename not in image_dict:
				## Each dictionary item consists of a string containing the filename of the brightfield image and then a list containing filenames for fluorescent images
				image_dict[common_filename] = ['',[]]
			## Assigns the brightfield wavelength
			if re.match(BrightWave, Wavelength, flags=re.IGNORECASE):
				image_dict[common_filename][0] = image_filename
			## Assigns the fluorescence wavelength
			elif re.match('w[1-9]',Wavelength, flags=re.IGNORECASE):
				image_dict[common_filename][1].append(image_filename)
##This loop pulls out all the TIF files and uses re to determine if its wavelength 1 (phase contrast) or any other (fluorescence) and adds it to a dictionary-----------^

ConfirmAll = False

##Sorts the dictionary keys so will do images in reasonable order
DictKeys = image_dict.keys()
DictKeys.sort()

for image_set in DictKeys:
	##Creates path for getting to phase contrast image
	phase_path = image_dir+image_dict[image_set][0]
	phase_img = ImagePlus(phase_path)
	if SegmentationType == "Phase Contrast":
		##Runs the Threshold command setting it to having a white background
		IJ.run(phase_img, "Threshold...","BlackBackground=False")
	else:
		##Runs the Threshold command setting it to having a dark background
		IJ.run(phase_img, "Threshold...","BlackBackground=True")
	IJ.setAutoThreshold(phase_img, "Default")
	Analysis_done = False
	skipcheck = False
	while Analysis_done == False:
		##Creates options for Analyze particles function using user input for min and max size.
		options = "size=" + str(minsize) + "-" + str(maxsize) + " exclude clear include add pixel"
		##Runs the Analyze particles function
		IJ().run(phase_img,"Analyze Particles...", options)
		##Gets access to the ROI manager
		RM = RoiManager.getInstance()
		try:
			##Gets indexes of ROIs in the ROI manager
			Ind2 = RM.getIndexes()
			RM.select(Ind2[0])
		except:
			pass
		##Creates dialog that allows users to confirm ROI generated, or repeat the analysis
		gd = NonBlockingGenericDialog('Confirm?')
		gd.enableYesNoCancel("Confirm","Repeat Analyze Particles")
		gd.addMessage("Size constraints for particle analysis (pixels^2)")
		gd.addStringField("Minimum", minsize)
		gd.addStringField("Maximum", maxsize)
		gd.addRadioButtonGroup("",["Apply to this Image","Skip this Image","Automatically Confirm All"],3,1,"Apply to this Image")
		##Skips over UI elements if user confirmed all
		if ConfirmAll != True:
			phase_img.show()
			gd.showDialog()
			##Escapes from the macro if user hits cancel
			if gd.wasCanceled():
				imagewindow = WindowManager.getCurrentWindow()
				WindowManager.setCurrentWindow(imagewindow)
				IJ.run("Close")
				IJ.selectWindow("ROI Manager")
				IJ.run("Close")
				IJ.selectWindow("Threshold")
				IJ.run("Close")
				sys.exit('Cancelled')
			elif gd.wasOKed():
				SkipOrConfirm = gd.getNextRadioButton()
				if SkipOrConfirm == "Skip this Image":
					skipcheck = True
				if SkipOrConfirm == "Automatically Confirm All":
					ConfirmAll = True
				Analysis_done = True
			else:
				RM.reset()
				IJ.run("Select None")
				minsize = gd.getNextString()
				maxsize = gd.getNextString()
				Analysis_done = False
		else:
			Analysis_done = True
	##Closes image used and threshold image to let user confirm ROIs generated
	##Selects the Threshold Window
	IJ.selectWindow("Threshold")
	IJ.run("Close")
	IJ.run(phase_img,"Close","")
	##This checks if the file should be skipped
	if skipcheck == True:
		continue
		
	##This saves the ROIs to the directory chosen
	ROI_path = roi_dir+image_set+".zip"	
	rm = RoiManager.getInstance()
	rm.runCommand('Save',ROI_path)
		
	##This loop goes through all the fluorescence images and gets the mean values-------------------v
	for fluor_image_filename in image_dict[image_set][1]:
		##Opens fluor_img (but not to user)
		fluor_image_path = image_dir+fluor_image_filename
		fluor_img = ImagePlus(fluor_image_path)
		##Gets indexes of ROI and selects all of them
		RM.deselect()
		Ind = RM.getIndexes()
		RM.setSelectedIndexes(Ind)
		##Instance of Analyzer which will be used
		An = Analyzer(fluor_img)
		##Sets measurements taken to mean only
		An.setMeasurements(2)
		##Measures mean for all ROIs
		measurement = RM.multiMeasure(fluor_img)
		##Gets mean out of results table and adds it to a list-v
		x = 0
		mean_list = []
		while measurement.columnExists(x) == True:
			mean = measurement.getColumn(x)
			mean_list.append(mean[0])
			x+=1
		##Gets mean out of results table and adds it to a list-^
		if SubBackground:
			##Combines ROI
			RM.runCommand(fluor_img,"Combine")
			##enlarges combined ROI to avoid fluorescence around cell
			cur_roi = fluor_img.getRoi()
			enlarged_roi = RoiEnlarger().enlarge(cur_roi,25)
			##Inverts the ROI so selecting Background not the cells
			fluor_img.setRoi(enlarged_roi)
			IJ().run(fluor_img,"Make Inverse","")
			##Measures the mean of background
			measured = Analyzer(fluor_img).measure()
			##Pulls mean value out
			bgresults = Analyzer.getResultsTable()
			bgmean = bgresults.getValue(1,0)
			##Goes through the list of cells and prints the mean fluorescence minus the background-v
			print fluor_image_filename,",","Subtracted Background:"+str(bgmean),",",
			for value in mean_list:
				print value-bgmean,",",
			print ""
			##Goes through the list of cells and prints the mean fluorescence minus the background-^
		else:
			print fluor_image_filename,",",
			for value in mean_list:
				print value,",",
			print ""
	##This loop goes through all the fluorescence images and gets the mean values-------------------^

## Closes the fluorescence image to release memory
fluor_img.close()
##Restores original settings for measurements
Analyzer().setMeasurements(original_setting)
##Closes the ROI Manager
RM.close()
##Restores standard output to normal
sys.stdout = NormOut
##Closes the results file
ResultsFile.close()
##Creates a message indicating process is finished
gd = GenericDialog('Done')
gd.addMessage('Done')
gd.hideCancelButton()
gd.showDialog()