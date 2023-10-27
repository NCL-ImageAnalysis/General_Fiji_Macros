## Author: Dr James Grimshaw | Newcastle University | james.grimshaw@newcastle.ac.uk
# Need to make sure to register and crop images before they go out of focus before inputing into this macro

#@ File (label="Input:", style="directory") InputFolder
#@ File (label="Output:", style="directory") OutputFolder

import os, re, time
from ij import IJ, ImagePlus
from ij.plugin.frame import RoiManager
from ij.measure import Measurements, ResultsTable
from java.lang import IllegalArgumentException


def getFilteredFileList(Directory, extension_pattern):
	"""Returns files in the folder that match the extension pattern

	Args:
		Directory (str): Path to the directory
		extension_pattern (str): regex pattern to match the extension

	Returns:
		[str]: File names that match the extension pattern
	"""	
	# Gets a list of filenames in the directory
	UnfilteredList = os.listdir(Directory)
	# Creates a regex object to search for matching extensions
	regexObj = re.compile(extension_pattern, flags=re.IGNORECASE)
	# Filters the list of files to only include matching files
	FilteredList = filter(regexObj.search, UnfilteredList)
	# Checks that one or more matching files are present in the folder
	if len(FilteredList) == 0:
		IJ.error("No matching files were detected")
		return False
	return FilteredList

# Gets any open ROI manager, gets the ROI contained and closes it before starting the macro
OldManager = RoiManager(False).getInstance()
if OldManager != None:
	OldRoi = OldManager.getRoisAsArray()
	OldManager.close()

# Defines Settings for measurement of images
Settings = Measurements.AREA | Measurements.ELLIPSE | Measurements.MEAN 

# Gets the directory paths for input/output folders
ImagesDir = InputFolder.getPath()
SaveDirPath = OutputFolder.getPath()

# Gets the data and time 
LocalTime = time.localtime()
# Creates a string with the data and time to add to filename
TimeAddition = time.strftime("%Y-%m-%d_%H-%M-%S_", LocalTime) 
# Adds the date and time to the filepath for saving the data
SaveTimePath = os.path.join(SaveDirPath, TimeAddition)

# Defines the pattern for searching for tif/tiff files
Extension_Pattern = r'\.tif{1,2}$'
FilteredFiles = getFilteredFileList(ImagesDir, Extension_Pattern)

# Defines a new Roi Manager instance for use by the Analyse particles function
CurrentManager = RoiManager()
# Hides the manager
CurrentManager.hide()

# List of tables used. Corresponds to Length, Width, Area, Intensity
TableList = (ResultsTable(), ResultsTable(), ResultsTable(), ResultsTable())

# Iterates though images in the path list
for ImagePath in FilteredFiles:
	# Gets the Image as an ImagePlus
	imp = ImagePlus(ImagePath)
	# Gets the Number of Slices
	Num_Slices = imp.getStackSize()
	# Duplicates the image for thresholding
	Thresh_imp = imp.duplicate()
	# Thresholds the image
	IJ.run(Thresh_imp, "Convert to Mask", "method=Default background=Light calculate black")
	# Runs analyze particles to get cell ROI
	IJ.run(Thresh_imp, "Analyze Particles...", "size=200-Infinity exclude clear include add stack pixel")
	# Closes the thresholding image (not needed once have ROIs)
	Thresh_imp.close() 
	# Gets the indexes in the Roi Manager to all created ROIs
	ROI_Indexes = CurrentManager.getIndexes()
	# Gets the number of ROIs
	Num_ROI = len(ROI_Indexes)
	# Increases the Rows in the results tables untill they match the number of ROIs
	while Num_Slices > TableList[3].size():
		for Table in TableList:
			Table.incrementCounter()
	# Iterates through ROI indexes
	for Index in ROI_Indexes:
		# Gets the Name of the ROI (Needed for certain functions)
		ROI_Name = CurrentManager.getName(Index)
		# Gets the slice the ROI was assigned to
		SliceNumber = CurrentManager.getSliceNumber(ROI_Name)
		# Sets the image to the Slice of the ROI
		imp.setZ(SliceNumber)
		# Selects the current ROI to the image
		CurrentManager.select(imp, Index)
		
		# Essentially runs the measure command
		Roi_Stats = imp.getStatistics(Settings)
		
		# Measures the intensity (mean gray value) of the selected cell
		Roi_Intensity = Roi_Stats.mean
		# Deselects and removes the ROI selecting the cell
		imp.deleteRoi()
		# Gets the intensity of the overall image
		Overall_Intensity = imp.getStatistics(Measurements.MEAN).mean
		# Gets the difference in intensity values from the overall image to the selected cell
		Intensity_Difference = abs(Overall_Intensity-Roi_Intensity)

		# Creates a list of data points to be added to the tables.
		# Corresponds to Length, Width, Area, Intensity
		Data_List = [Roi_Stats.major, Roi_Stats.minor, Roi_Stats.area, Intensity_Difference]

		# Goes though the tables in the Table List
		for Table in range(0, 4):
			# Adds the slice number to the table
			TableList[Table].setValue('Slice', SliceNumber-1, SliceNumber)

			# Try except clause is here in case the column does not yet exist
			try:
				# Gets the current value of the row to be modified. Should be 0.0
				PrexistingVal = (TableList[Table].getValue(ImagePath, SliceNumber-1))
			except IllegalArgumentException:
				PrexistingVal = 0.0

			# Checks that the Prexisting value was 0. If not then there are multiple ROI assigned to a single slice
			if PrexistingVal == 0:
				TableList[Table].setValue(ImagePath, SliceNumber-1, Data_List[Table])

			# If there are multiple ROI assigned to a single slice then will set the value to NaN
			else:
				TableList[Table].setValue(ImagePath, SliceNumber-1, 'NaN')

	# Resets the ROI manager between Images
	CurrentManager.reset()

# Closes the ROI Manager
CurrentManager.close()

# Saves the Results Tables
TableList[0].save(SaveTimePath+'Length.csv')
TableList[1].save(SaveTimePath+'Width.csv')
TableList[2].save(SaveTimePath+'Area.csv')
TableList[3].save(SaveTimePath+'Intensity.csv')

# If there was an open ROI Manager when the macro was run, this section will Re-open it
if OldManager != None:
	NewOldManger = RoiManager()
	for R in OldRoi:
		NewOldManger.addRoi(R)