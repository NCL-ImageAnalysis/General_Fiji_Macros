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
NormOut=sys.stdout

##Gets the original settings for measurements
original_setting=Analyzer().getMeasurements()

##Opens a dialog that lets user choose the folder containing images they want to analyse-v
image_dir=DirectoryChooser("Choose Folder Containing Images").getDirectory()
##Will escape if Cancel is hit and no file is chosen
if image_dir==None:
	sys.exit('Image Not Chosen')
##Opens a dialog that lets user choose the folder containing images they want to analyse-^

##Opens a dialog that lets user choose a folder where they want to save their ROI-v
roi_dir=DirectoryChooser("Choose Where to Save ROI").getDirectory()
##Will escape if Cancel is hit and no file is chosen
if roi_dir==None:
	sys.exit('Directory Not Chosen')
##Opens a dialog that lets user choose a folder where they want to save their ROI-^

##Asks user what to save data as and where to save it
SD1=SaveDialog('Save data as...','','.csv')
##Gets name user chose
name1=SD1.getFileName()
##Will escape if Cancel is hit and no file is chosen
if name1==None:
	sys.exit('Save Location Not Chosen')
##Gets path for where to save data
savepath=SD1.getDirectory()+name1

##Makes a results file based upon the users chosen savepath
ResultsFile = open(savepath,'w')
##Sets standard output to be that results file
sys.stdout = ResultsFile

file_list=os.listdir(image_dir)
image_dict={}

##This loop pulls out all the TIF files and uses re to determine if its wavelength 1 (phase contrast) or any other (fluorescence) and adds it to a dictionary-v
for image_filename in file_list:
	get_extension=image_filename.split('.')
	if re.search('\.tif{1,2}$', image_filename, flags=re.IGNORECASE):
			get_wavelength=image_filename.split('_')
			common_filename='_'.join(get_wavelength[0:-1])
			if common_filename not in image_dict:
				image_dict[common_filename]=['',[]]
			if re.match('w1',get_wavelength[-1],\A):
				image_dict[common_filename][0]=image_filename
			elif re.match('w[2-9]',get_wavelength[-1],\A):
				image_dict[common_filename][1].append(image_filename)
			else:
				sys.exit('Unknown File Detected')
##This loop pulls out all the TIF files and uses re to determine if its wavelength 1 (phase contrast) or any other (fluorescence) and adds it to a dictionary-^

##Allows user to input size restrictions for Particle analysis
settings_dialog=GenericDialog("Input Size Restrictions")
settings_dialog.addMessage("Input size constraints for particle analysis (pixels^2)")
settings_dialog.addStringField("Minimum", "0")
settings_dialog.addStringField("Maximum", "Infinity")
settings_dialog.showDialog()
minsize=settings_dialog.getNextString()
maxsize=settings_dialog.getNextString()
if settings_dialog.wasCanceled():
	sys.exit('Cancelled')

ConfirmAll=False
for image_set in image_dict:
	##Creates path for getting to phase contrast image
	phase_path=image_dir+image_dict[image_set][0]
	phase_img=ImagePlus(phase_path)
	##Runs the Threshold command setting it to having a white background
	IJ().run(phase_img,"Threshold...","BlackBackground=False")
	Analysis_done=False
	skipcheck=False
	while Analysis_done==False:
		##Creates options for Analyze particles function using user input for min and max size.
		options="size="+str(minsize)+"-Infinity exclude clear include add pixel"
		##Runs the Analyze particles function
		IJ().run(phase_img,"Analyze Particles...", options)
		##Gets access to the ROI manager
		RM=RoiManager.getInstance()
		##Selects all ROI in ROI manager
		Ind2=RM.getIndexes()
		RM.select(Ind2[0])
		##Creates dialog that allows users to confirm ROI generated, or repeat the analysis
		gd=NonBlockingGenericDialog('Confirm?')
		gd.enableYesNoCancel("Confirm","Repeat Analyze Particles")
		gd.addMessage("Size constraints for particle analysis (pixels^2)")
		gd.addStringField("Minimum", minsize)
		gd.addStringField("Maximum", maxsize)
		gd.addRadioButtonGroup("",["Apply to this Image","Skip this Image","Automatically Confirm All"],3,1,"Apply to this Image")
		##Skips over UI elements if user confirmed all
		if ConfirmAll!=True:
			phase_img.show()
			gd.showDialog()
			##Escapes from the macro if user hits cancel
			if gd.wasCanceled():
				imagewindow=WindowManager.getCurrentWindow()
				WindowManager.setCurrentWindow(imagewindow)
				IJ.run("Close")
				IJ.selectWindow("ROI Manager")
				IJ.run("Close")
				IJ.selectWindow("Threshold")
				IJ.run("Close")
				sys.exit('Cancelled')
			elif gd.wasOKed():
				SkipOrConfirm=gd.getNextRadioButton()
				if SkipOrConfirm=="Skip this Image":
					skipcheck=True
				if SkipOrConfirm=="Automatically Confirm All":
					ConfirmAll=True
				Analysis_done=True
			else:
				RM.reset()
				IJ.run("Select None")
				minsize=gd.getNextString()
				maxsize=gd.getNextString()
				Analysis_done=False
		else:
			Analysis_done=True
	##Closes image used and threshold image to let user confirm ROIs generated
	##Selects the Threshold Window
	IJ.selectWindow("Threshold")
	IJ.run("Close")
	IJ.run(phase_img,"Close","")
	##This checks if the file should be skipped
	if skipcheck==True:
		continue
		
	##This saves the ROIs to the directory chosen
	ROI_path=roi_dir+image_set+".zip"	
	rm=RoiManager.getInstance()
	rm.runCommand('Save',ROI_path)
		
	##This loop goes through all the fluorescence images and gets the mean values-------------------v
	for fluor_image_filename in image_dict[image_set][1]:
		##Opens fluor_img (but not to user)
		fluor_image_path=image_dir+fluor_image_filename
		fluor_img=ImagePlus(fluor_image_path)
		##Gets indexes of ROI and selects all of them
		RM.deselect()
		Ind=RM.getIndexes()
		RM.setSelectedIndexes(Ind)
		##Instance of Analyzer which will be used
		An=Analyzer(fluor_img)
		##Sets measurements taken to mean only
		An.setMeasurements(2)
		##Measures mean for all ROIs
		measurement=RM.multiMeasure(fluor_img)
		##Gets mean out of results table and adds it to a list-v
		x=0
		mean_list=[]
		while measurement.columnExists(x)==True:
			mean=measurement.getColumn(x)
			mean_list.append(mean[0])
			x+=1
		##Gets mean out of results table and adds it to a list-^
		##Combines ROI
		RM.runCommand(fluor_img,"Combine")
		##enlarges combined ROI to avoid fluorescence around cell
		cur_roi=fluor_img.getRoi()
		enlarged_roi=RoiEnlarger().enlarge(cur_roi,25)
		##Inverts the ROI so selecting Background not the cells
		fluor_img.setRoi(enlarged_roi)
		IJ().run(fluor_img,"Make Inverse","")
		##Measures the mean of background
		measured=Analyzer(fluor_img).measure()
		##Pulls mean value out
		bgresults=Analyzer.getResultsTable()
		bgmean=bgresults.getValue(1,0)
		##Goes through the list of cells and prints the mean fluorescence minus the background-v
		print fluor_image_filename,",","Subtracted Background:"+str(bgmean),",",
		for value in mean_list:
			print value-bgmean,",",
		print ""
		##Goes through the list of cells and prints the mean fluorescence minus the background-^
	##This loop goes through all the fluorescence images and gets the mean values-------------------^

## Closes the fluorescence image to release memory
fluor_img.close()
##Restores original settings for measurements
Analyzer().setMeasurements(original_setting)
##Closes the ROI Manager
RM.close()
##Restores standard output to normal
sys.stdout=NormOut
##Closes the results file
ResultsFile.close()
##Creates a message indicating process is finished
gd=GenericDialog('Done')
gd.addMessage('Done')
gd.hideCancelButton()
gd.showDialog()
