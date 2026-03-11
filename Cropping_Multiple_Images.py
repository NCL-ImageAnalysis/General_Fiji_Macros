#@ File(label="Input Folder:", value = "", style="directory") InputFolder
#@ File(label="Output Folder:", value = "", style="directory") OutputFolder

## Authors: Dr James Grimshaw | Newcastle University | james.grimshaw@newcastle.ac.uk
## This Fiji macro runs in Jython and allows the user to batch crop images in a folder

import os

from ij import IJ, ImagePlus, WindowManager
from ij.io import FileSaver
from ij.gui import GenericDialog

from loci.formats import ImageReader

def main(image_dir, save_dir):
	file_list = os.listdir(image_dir)

	inpaths = [os.path.join(image_dir, f) for f in file_list]
	reader = ImageReader()
	inpaths = [f for f in inpaths if reader.isThisType(f, True)]
	save_path_list = [os.path.join(save_dir, ".".join(os.path.basename(f).split('.')[:-1])+'.tif') for f in inpaths]

	cont = False
	progress = 0
	for image_path in inpaths:
		## Accesses image to be cropped
		img = ImagePlus(image_path)
		## Gets height and width of image in pixels
		height = img.getHeight()
		width = img.getWidth()
		## Will loop through untill user selects desired settings
		while cont == False:
			## Shows image to user
			img.show()
			## Dialog to enter settings
			Settings_Dialog = GenericDialog("Area to Select")
			Settings_Dialog.addNumericField("Height",height,6,10,"Pixels")
			Settings_Dialog.addNumericField("Width",width,6,10,"Pixels")
			Settings_Dialog.showDialog()
			## Exits macro if cancel hit
			if Settings_Dialog.wasCanceled():
				return
			## Pulls inputted height and width from dialog
			crop_height = Settings_Dialog.getNextNumber()
			crop_width = Settings_Dialog.getNextNumber()
			## creates string for settings for specify command
			settings = "width="+str(crop_width)+" height="+str(crop_height)+" x="+str(width/2)+" y="+str(height/2)+" centered"
			## Runs specify command to create ROI
			IJ.run("Specify...",settings)
			## Prompts user to either accept settings or enter new settings
			gd = GenericDialog('Confirm?')
			gd.enableYesNoCancel("Confirm","Enter New Settings")
			gd.showDialog()
			if gd.wasCanceled():
				imagewindow = WindowManager.getCurrentWindow()
				WindowManager.setCurrentWindow(imagewindow)
				IJ.run("Close")
				return
			elif gd.wasOKed():
				cont = True
			else:
				pass
		
		## Runs specify command to create ROI
		IJ.run(img, "Specify...", settings)
		## Runs crop command to crop the image
		Cropped = img.crop()
		## Closes the full size image
		img.close()
		save_path = os.path.join(save_dir, ".".join(os.path.basename(image_path).split('.')[:-1])+'.tif')
		## Saves cropped image
		FileSaver(Cropped).saveAsTiff(save_path)

		## Closes the cropped image
		Cropped.close()
		## Shows progress to user
		progress += 1
		IJ.showProgress(progress,len(inpaths))

if __name__ == "__main__":
	main(InputFolder.getPath(), OutputFolder.getPath())