## Authors: Dr James Grimshaw | Newcastle University | james.grimshaw@newcastle.ac.uk
## This Fiji macro runs in Jython and allows the user to batch crop images in a folder
## This macro takes TIF files with channels labelled _w1/w2/w3

from ij import IJ, ImagePlus, WindowManager
from ij.io import DirectoryChooser, FileSaver
from ij.gui import GenericDialog
import sys, os, re

## This function takes a list of Proposed Save Paths and checks if they exists.
## If they do then it will prompt to user to decide whether or not to overwrite them
def CheckForExistingSaves(PathList):
	## List that will be populated with images that will be processed
	todofiles = []
	## Tracks total number of files
	filenum = 0
	## Variable that determines if action chosen should be applied to all images
	ApplyBool = True

	## This loop iterates through paths given when calling function
	for path in PathList:
		if os.path.exists(path)==True:
			## If the file already exists, this creates a Yes/No/Cancel dialog to see if they want to replace the file-v
			Dialog_text = 'The file '+path+' already exists. Would you like to replace it?'
			gd = GenericDialog('Replace?')
			gd.addMessage(Dialog_text)
			gd.enableYesNoCancel()
			## Creates checkbox that asks user if they want to apply command to rest of samples
			gd.addCheckbox('Apply to Rest',ApplyBool)
			gd.showDialog()
			ApplyBool = gd.getNextBoolean()
			## If the file already exists, this creates a Yes/No/Cancel dialog to see if they want to replace the file-^

			## Will escape if Cancel is hit
			if gd.wasCanceled():
				sys.exit('Cancelled')

			## If apply to rest checkbox is ticked then this else statement will do this-v
			elif ApplyBool == True:
				if gd.wasOKed():
					todofiles += PathList[filenum:len(PathList)]
					break
				else:
					break
			## If apply to rest checkbox is ticked then this else statement will do this-^

			## If user approves it will be overwritten, otherwise that file will be skipped
			elif gd.wasOKed():
				todofiles.append(path)
			else:
				continue
		else:
			todofiles.append(path)
		filenum += 1
	return todofiles

## Opens a dialog that lets user choose the folder containing images they want to analyse-v
Dialogue_1=DirectoryChooser("Choose Folder Containing Images")
image_dir=Dialogue_1.getDirectory()
## Will escape if Cancel is hit and no file is chosen
if image_dir==None:
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
save_path_list=[]

## This loop pulls out all the TIF files and uses re to determine if its wavelength 1 or 2-v
for image_filename in file_list:
	get_extension = image_filename.split('.')
	if re.search('\.tif{1,2}$', image_filename, flags=re.IGNORECASE):
		save_path_list.append(save_dir + image_filename)

if save_path_list == []:
	sys.exit('Unknown File Detected')

## Checks if the file that it is going to be saved as already exists
todofiles=CheckForExistingSaves(save_path_list)

cont = False
progress = 0
for save_path in todofiles:
	## Gets the filename from the path
	split_path = save_path.split('\\')
	image_filename2 = split_path[-1]
	## Creates path for where to find image to be cropped
	image_path = image_dir+image_filename2
	## Accesses image to be cropped
	img = ImagePlus(image_path)
	## Shows image to user
	img.show()
	## Gets height and width of image in pixels
	height = img.getHeight()
	width = img.getWidth()
	## Will loop through untill user selects desired settings
	while cont == False:
		## Dialog to enter settings
		Settings_Dialog = GenericDialog("Area to Select")
		Settings_Dialog.addNumericField("Height",height,6,10,"Pixels")
		Settings_Dialog.addNumericField("Width",width,6,10,"Pixels")
		Settings_Dialog.showDialog()
		## Exits macro if cancel hit
		if Settings_Dialog.wasCanceled():
			sys.exit('Cancelled')
		## Pulls inputted height and width from dialog
		crop_height = Settings_Dialog.getNextNumber()
		crop_width = Settings_Dialog.getNextNumber()
		## creates string for settings for specify command
		settings = "width="+str(crop_width)+" height="+str(crop_height)+" x="+str(width/2)+" y="+str(height/2)+" centered"
		## Runs specify command to create ROI
		IJ().run("Specify...",settings)
		## Prompts user to either accept settings or enter new settings
		gd = GenericDialog('Confirm?')
		gd.enableYesNoCancel("Confirm","Enter New Settings")
		gd.showDialog()
		if gd.wasCanceled():
			imagewindow = WindowManager.getCurrentWindow()
			WindowManager.setCurrentWindow(imagewindow)
			IJ.run("Close")
			sys.exit('Cancelled')
		elif gd.wasOKed():
			cont = True
		else:
			pass
	
	## Runs specify command to create ROI
	IJ().run(img, "Specify...", settings)
	## Runs crop command to crop the image
	Cropped = img.crop()
	## Closes the full size image
	img.close()
	## Saves cropped image
	FileSaver(Cropped).saveAsTiff(save_path)

	## Closes the cropped image
	Cropped.close()
	## Shows progress to user
	progress += 1
	IJ.showProgress(progress,len(todofiles))
