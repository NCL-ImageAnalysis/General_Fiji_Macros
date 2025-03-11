from ij import IJ, ImagePlus
from ij.plugin import ZProjector

def analyzeParticles(
		Binary_Image, 
		Size_Setting, 
		Circularity_Setting):
	"""Runs analyze particles on the binary image, returning the ROI

	Args:
		Binary_Image (ij.ImagePlus): Segmented binary image
		Size_Setting (str): Min/Max size settings for analyse particles
		Circularity_Setting (str): Min/Max circularity settings for analyse particles

	Returns:
		[PolygonRoi]: Outputted Rois
	"""	

	# Defines analyse particles settings
	AnalyzeParticlesSettings = (
		"size=" 
		+ Size_Setting 
		+ " circularity=" 
		+ Circularity_Setting 
		+ " clear overlay exclude"
	)
	# Runs the analyze particles command to get ROI. 
	# Done by adding to the overlay in order to not have ROIManger shown to user
	IJ.run(Binary_Image, "Analyze Particles...", AnalyzeParticlesSettings)
	# Gets the Overlayed ROIs from analyze particles
	Overlayed_Rois = Binary_Image.getOverlay()
	# Takes the overlay and turns it into an array of ROI
	RoiList = Overlayed_Rois.toArray()
	# Removes this overlay to clean up the image
	IJ.run(Binary_Image, "Remove Overlay", "")
	return RoiList

imp = IJ.getImage()
projected = ZProjector.run(imp, "max")
projected.setC(3)
dapi = projected.crop("whole-slice")
IJ.run(dapi, "Gaussian Blur...", "sigma=40")
JustNuclei = dapi.duplicate()
IJ.setAutoThreshold(JustNuclei, "Yen dark")
IJ.run(JustNuclei, "Convert to Mask", "")
nucleirois = analyzeParticles(JustNuclei, "100-Infinity", "0-1.0")
for roi in nucleirois:
	projected.setRoi(roi)
	IJ.run(projected, "Clear", "stack")
JustNuclei.close()
dapi.setAutoThreshold("Otsu dark")
IJ.run(dapi, "Convert to Mask", "")
IJ.run(dapi, "Fill Holes", "")
IJ.run(dapi, "Create Selection", "")
CellRoi = dapi.getRoi()
dapi.close()

projected.setRoi(CellRoi)
IJ.run(projected, "Clear Outside", "stack")
BinaryPlus = ImagePlus(imp.getTitle() + "_mask", projected.createRoiMask())
BinaryPlus.setCalibration(projected.getCalibration())
for roi in nucleirois:
	BinaryPlus.setRoi(roi)
	IJ.run(BinaryPlus, "Clear", "stack")
BinaryPlus.deleteRoi()
projected.deleteRoi()
for chan in range(1, projected.getNChannels() + 1):
	projected.setC(chan)
	IJ.run(projected, "Enhance Contrast", "saturated=0.35")
projected.setC(1)
projected.show()
BinaryPlus.show()

