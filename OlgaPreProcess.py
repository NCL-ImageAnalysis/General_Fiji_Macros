#@ Integer (label="DAPI Channel") dapichannel
#@ String (label="Projection type", choices={"max", "sum"}) projectiontype
#@ Float (label="Nuclei Size Threshold") nuclei_size

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

# Z Project the image
projected = ZProjector.run(imp, projectiontype)

# Segmentation of cell + Nuclei----------------------------------------------------v
# Selects the dapi channel
projected.setC(dapichannel)
# Get just the dapi channel
dapi = projected.crop("whole-slice")
IJ.run(dapi, "Gaussian Blur...", "sigma=40")
# Gets the nuclei-----------------------------------------------------------------v
JustNuclei = dapi.duplicate()
IJ.setAutoThreshold(JustNuclei, "Yen dark")
IJ.run(JustNuclei, "Convert to Mask", "")
nucleirois = analyzeParticles(JustNuclei, str(nuclei_size) + "-Infinity", "0-1.0")
#---------------------------------------------------------------------------------^
# Delete the pixels within the nuclei
for roi in nucleirois:
	projected.setRoi(roi)
	IJ.run(projected, "Clear", "stack")
JustNuclei.close()

# Gets the cell-------------------------------------------------------------------v
dapi.setAutoThreshold("Otsu dark")
IJ.run(dapi, "Convert to Mask", "")
IJ.run(dapi, "Fill Holes", "")
IJ.run(dapi, "Create Selection", "")
CellRoi = dapi.getRoi()
#---------------------------------------------------------------------------------^
dapi.close()
# Delete the pixels outside the cell
projected.setRoi(CellRoi)
IJ.run(projected, "Clear Outside", "stack")
#----------------------------------------------------------------------------------^

# Gets a binary mask of the cell
BinaryPlus = ImagePlus(imp.getTitle() + "_mask", projected.createRoiMask())
BinaryPlus.setCalibration(projected.getCalibration())
# Remove the nuclei from the binary mask
for roi in nucleirois:
	BinaryPlus.setRoi(roi)
	IJ.run(BinaryPlus, "Clear", "stack")
BinaryPlus.deleteRoi()
projected.deleteRoi()
# Auto contrast on slices
for chan in range(1, projected.getNChannels() + 1):
	projected.setC(chan)
	IJ.run(projected, "Enhance Contrast", "saturated=0.35")
projected.setC(1)

# Display projected image and binary mask
projected.show()
BinaryPlus.show()

