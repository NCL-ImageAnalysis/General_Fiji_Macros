#@ File(label="Input Folder:", value = "", style="directory") InputFolder
#@ File(label="Output Folder:", value = "", style="directory") OutputFolder
#@ String(label="Fusion Method", choices=["Linear Blending", "Average", "Median", "Max. Intensity", "Min. Intensity", "Intensity of random input tile"], value="Linear Blending", style="listBox") FusionMethod
#@ Float(label="Regression threshold", value=0.30, style="format:#####.#####") RegressionThreshold
#@ Float(label="Max/Avg displacement threshold", value=2.50, style="format:#####.#####") MaxAvgDisplacementThreshold
#@ Float(label="Absolute displacement threshold", value=3.50, style="format:#####.#####") AbsoluteDisplacementThreshold
#@ Boolean(label="Subpixel accuracy", value=True) SubpixelAccuracy
#@ Boolean(label="Ignore Z position", value=True) IgnoreZPosition
#@ String(label="Computation parameters", choices=["Save computation time (but use more RAM)", "Save memory (but be slower)"], value="Save computation time (but use more RAM)", style="listBox") CompParameters

import os, re, shutil

from ij import IJ, ImagePlus
from ij.io import FileSaver
from ij.plugin import RGBStackMerge

from loci.formats import ImageReader
from loci.formats.services import OMEXMLServiceImpl

inpath = InputFolder.getPath()
outpath = OutputFolder.getPath()

def getFileDict(root, files, regexpattern):
	regexitem = re.compile(regexpattern, re.IGNORECASE)
	celldict = {}
	for file in files:
		matchobj = regexitem.match(file)
		if matchobj:
			try:
				celldict[matchobj.group(1)].append(os.path.join(root, file))
			except KeyError:
				celldict[matchobj.group(1)] = [os.path.join(root, file)]
	return celldict

def createTileConfig(folder, regexpattern=None):
	base = "Information|Image|S|Scene|Position|"
	filedict = {}
	xlist = []
	ylist = []
	zlist = []
	filenames = os.listdir(folder)
	if regexpattern:
		filenames = [f for f in filenames if re.search(regexpattern, f, re.IGNORECASE)]
	for fn in filenames:
		fp = os.path.join(folder, fn)
		MetaReader = ImageReader()
		Metadata = OMEXMLServiceImpl().createOMEXMLMetadata()
		MetaReader.setMetadataStore(Metadata)
		MetaReader.setId(fp)
		sizeX = Metadata.getPixelsPhysicalSizeX(0).value()
		sizeY = Metadata.getPixelsPhysicalSizeY(0).value()
		sizeZ = Metadata.getPixelsPhysicalSizeZ(0).value()
		GlobalMetadata = MetaReader.getGlobalMetadata()
		posX = GlobalMetadata[base + "X"]
		posY = GlobalMetadata[base + "Y"]
		posZ = GlobalMetadata[base + "Z"]
		MetaReader.close()
		posX = float(posX)
		posY = -float(posY)
		posZ = float(posZ)
		xlist.append(posX)
		ylist.append(posY)
		zlist.append(posZ)
		filedict[fn] = {"pos_x": posX, "pos_y": posY, "pos_z": posZ}
	minx = min(xlist)
	miny = min(ylist)
	minz = min(zlist)

	with open(os.path.join(folder, "TileConfiguration.txt"), "w") as f:
		f.write("# Define the number of dimensions we are working on\n")
		f.write("dim = 3\n\n")
		f.write("# Define the image coordinates\n")
		for fn in filenames:
			adjusted_pos_x = (filedict[fn]["pos_x"] - minx) / sizeX
			adjusted_pos_y = (filedict[fn]["pos_y"] - miny) / sizeY
			adjusted_pos_z = (filedict[fn]["pos_z"] - minz) / sizeZ
			f.write(fn + "; ; ("+str(adjusted_pos_x)+", "+str(adjusted_pos_y)+", "+str(adjusted_pos_z)+")\n")

def createImageStackFromFolder(folder, regexpattern=None):
	if not os.path.exists(folder):
		raise FileNotFoundError("The folder does not exist: " + folder)
	files = os.listdir(folder)
	if regexpattern:
		regexitem = re.compile(regexpattern, re.IGNORECASE)
		files = [f for f in files if regexitem.match(f)]
	channelregex = re.compile(r"_c(\d)")
	channeldict = {}
	for filename in files:
		match = channelregex.search(filename)
		if match:
			channel = match.group(1)
		else:
			channel = "0"  # Default channel if none found
		try:
			channeldict[channel].append(filename)
		except KeyError:
			channeldict[channel] = [filename]
	StackedList = []
	for imagechannel in sorted(channeldict.keys()):
		Stack = None
		for filename in channeldict[imagechannel]:
			imp = ImagePlus(os.path.join(folder, filename))
			if Stack == None:
				Stack = imp.createEmptyStack()
			Stack.addSlice(imp.getProcessor())
			imp.close()
		StackedList.append(ImagePlus("StackedImage", Stack))
	if len(StackedList) == 1:
		return StackedList[0]
	else:
		return RGBStackMerge.mergeChannels(StackedList, False)

def main(InputPath, 
		 OutputPath, 
		 fusion_method="Linear Blending", 
		 regression_threshold=0.30,
		 max_avg_displacement_threshold=2.50,
		 absolute_displacement_threshold=3.50,
		 subpixel_accuracy=True,
		 ignore_z_position=True,
		 computation_parameters="Save computation time (but use more RAM)"
		 ):
	regexpattern = r"(.*) pt(\d*)\.czi$"
	if not os.path.exists(InputPath):
		IJ.error("Input folder does not exist: " + InputPath)
		return
	# Gets the stitching settings that will be used for all images
	StitchingSetttings = str("layout_file=TileConfiguration.txt" + 
				" fusion_method=[" + fusion_method + 
				"] regression_threshold=" + str(regression_threshold) + 
				" max/avg_displacement_threshold=" + str(max_avg_displacement_threshold) +
				" absolute_displacement_threshold=" + str(absolute_displacement_threshold) +
				" compute_overlap" +
				" computation_parameters=[" + computation_parameters + "]")
	if subpixel_accuracy:
		StitchingSetttings += " subpixel_accuracy"
	if ignore_z_position:
		StitchingSetttings += " ignore_z_stage"

	for root, dirs, files in os.walk(InputPath):
		celldict = getFileDict(root, files, regexpattern)
		for cell in celldict:
			# If it is only a single file, copy it directly
			if len(celldict[cell]) < 2:
				newpath = celldict[cell][0].replace(InputPath, OutputPath)
				if os.path.exists(newpath):
					continue  # Skip if the file already exists
				if not os.path.exists(os.path.dirname(newpath)):
					os.makedirs(newpath)
				shutil.copy(celldict[cell][0], newpath)
			# If it is more than one file, stitch them together
			else:
				# Create a new path for the stitched image
				newpath = os.path.join(os.path.split(celldict[cell][0])[0], cell).replace(InputPath, OutputPath)
				if os.path.exists(newpath + ".tif"):
					continue # Skip if the stitched file already exists
				if not os.path.exists(newpath):
					os.makedirs(newpath)
				CalibrationObject = ImagePlus(celldict[cell][0]).getCalibration()
				for file in celldict[cell]:
					splitfile = os.path.split(file)
					tempdir = os.path.join(splitfile[0], cell)
					if not os.path.exists(tempdir):
						os.makedirs(tempdir)
					shutil.move(file, os.path.join(tempdir, splitfile[1]))
				createTileConfig(tempdir, regexpattern=r"\.czi$")
				try:
					# This section runs the stitching command-v
					IJ.run("Grid/Collection stitching", 
					"type=[Positions from file] order=[Defined by TileConfiguration] directory=[" +
					tempdir + "] " +
					StitchingSetttings +
					" image_output=[Write to disk] output_directory=["+
					newpath + "]")
					#-----------------------------------------^

					# Create a stack from the stitched images
					StackedStitchedImage = createImageStackFromFolder(newpath)
					# Sets the scaling of the stitched image
					StackedStitchedImage.setCalibration(CalibrationObject)
					# Saves the stitched image
					FileSaver(StackedStitchedImage).saveAsTiff(newpath + ".tif")
					# Clean up the temporary directorys
					shutil.rmtree(newpath)
				except Exception as e:
					print("Error during stitching for cell {}: {}".format(cell, e))
				# Moving the files back to their original directorys
				for file in os.listdir(tempdir):
					shutil.move(os.path.join(tempdir, file), os.path.join(splitfile[0], file))
				shutil.rmtree(tempdir)
		
				

if __name__ == "__main__":
	main(inpath, 
	  outpath,
	  fusion_method=FusionMethod,
	  regression_threshold=RegressionThreshold,
	  max_avg_displacement_threshold=MaxAvgDisplacementThreshold,
	  absolute_displacement_threshold=AbsoluteDisplacementThreshold,
	  subpixel_accuracy=SubpixelAccuracy,
	  ignore_z_position=IgnoreZPosition,
	  computation_parameters=CompParameters
	)