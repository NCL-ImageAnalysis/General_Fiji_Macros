## Authors: Dr James Grimshaw | Newcastle University | james.grimshaw@newcastle.ac.uk
## This Macro takes a polygon or freehand Roi, and rotates it untill it has the smallest bounding box
## It will then rotate the image this much and duplicate the image to show a cropped field of view

from ij import IJ
from ij.gui import Overlay
from ij.plugin import Duplicator, RoiRotator, RoiScaler

def Rotate_and_Crop_Roi(Image, ROI):
	# Gets the X/Y coordinates of the ROI
	X = ROI.getXBase()
	Y = ROI.getYBase()
	# Gets the image dimensions so can scale the image
	Width = Image.getWidth()
	Height = Image.getHeight()
	# Scales up the canvas size in case the Roi is near the edge of the image
	IJ.run(Image, "Canvas Size...", "width="+str(Width*2)+" height="+str(Height*2)+" position=Center")
	# Sets the location of the ROI adding the additional pixels for the new canvas size
	ROI.setLocation(X+Width/2, Y+Height/2)
	# Sets Roi to overlay (Won't transfer to cropped image properly otherwise)
	PolyOverlay = Overlay(ROI)
	Image.setOverlay(PolyOverlay) 
	# Doubles size of area to be cropped (otherwise will have black edges to cropped image)
	EnlargedROI = RoiScaler().scale(ROI, 2, 2, True)
	# Sets the enlarged Roi to the image for duplication
	Image.setRoi(EnlargedROI)
	# Duplicates cropped section of the image based on enlarged Roi
	Cropped = Duplicator().run(Image)
	CroppedOverlay = Cropped.getOverlay()
	# Restores Image to its original size
	IJ.run(Image, "Canvas Size...", "width="+str(Width)+" height="+str(Height)+" position=Center")
	# Gets the ROI from the overlay (Index of 0)
	InitialROI = CroppedOverlay.get(0)
	# Gets rid of the overlays
	PolyOverlay.clear()
	CroppedOverlay.clear()
	# Gets bounding rectangle of the drawn ROI
	InitialBounds = InitialROI.getBounds()
	# Adds area of bounding rectangle to list, along with the ROI and degrees rotated (0)
	LowestArea = [(InitialBounds.height * InitialBounds.width), InitialROI, 0]
	# Defines RoiRotator for later use
	RR = RoiRotator()
	# This will loop through 0-360 degrees of rotation
	for Degree in range(0, 361):
		# Rotates the Roi by listed No. degrees
		RotatedROI = RR.rotate(InitialROI, Degree)
		# Gets the bounding box of the Roi
		BoundingBox = RotatedROI.getBounds()
		# Gets area of the bounding box
		BoundingArea = BoundingBox.height * BoundingBox.width
		# If the bounding area is lower than the previous lowest bounding area then will replace Lowest area list
		if BoundingArea < LowestArea[0]:
			LowestArea = [BoundingArea, RotatedROI, Degree]
	# Rotates the image by the same number of degrees as the lowest area roi rotation
	IJ.run(Cropped, "Rotate... ", "angle="+str(LowestArea[2])+" grid=1 interpolation=Bilinear stack")
	# Selects the rotated Roi on the rotated image
	Cropped.setRoi(LowestArea[1])
	# Crops the image using the rotated Roi (Will actually use its bounding box)
	TightCrop = Duplicator().run(Cropped)
	return TightCrop



# Accesses current image
imp = IJ.getImage()
# Gets currently selected Roi
PolyROI = imp.getRoi()

# Calls the function getting the rotated and cropped image
CroppedImage = Rotate_and_Crop_Roi(imp, PolyROI)

# Shows the cropped image
CroppedImage.show()