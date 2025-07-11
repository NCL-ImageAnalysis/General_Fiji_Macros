import sys, os, re, time
from ij import IJ, ImagePlus
from ij.io import DirectoryChooser
from ij.gui import Overlay, GenericDialog, NonBlockingGenericDialog
from ij.measure import Measurements, ResultsTable
from ij.plugin import Duplicator, RoiRotator, RoiScaler, ImageCalculator
from ij.plugin.frame import RoiManager

# Gets any open ROI manager, gets the ROI contained and closes it before starting the macro
OldManager = RoiManager(False).getInstance()
if OldManager != None:
	OldRoi = OldManager.getRoisAsArray()
	OldManager.close()

Settings = Measurements.AREA | Measurements.MEAN

# Dialog where user chooses where their images should be kept
ImagesChooser = DirectoryChooser('Choose where to find your images')
ImagesDir = ImagesChooser.getDirectory()
if ImagesDir == None:
	sys.exit('No Directory Selected')

# Dialog where user chooses where their ROI are kept
ImagesChooser = DirectoryChooser('Choose where to find your ROI')
ROIDir = ImagesChooser.getDirectory()
if ROIDir == None:
	sys.exit('No Directory Selected')
# Dialog where user chooses where to save their data
SaveGUI = DirectoryChooser('Choose where to save your data')
SaveDirPath = SaveGUI.getDirectory()
if SaveDirPath == None:
	sys.exit('No Directory Selected')

# Gets the data and time 
LocalTime = time.localtime()
# Creates a string with the data and time to add to filename
TimeAddition = time.strftime("%Y-%m-%d_%H-%M-%S_", LocalTime) 
# Adds the date and time to the filepath for saving the data
SaveTimePath = os.path.join(SaveDirPath, TimeAddition)

# Defines the pattern for searching for tif/tiff files
Extension_Pattern = r'\.tif$|\.tiff$'

# Searches through files in the chosen directory for tif files and their paths to a list-v

image_dict = {}

for FileName in os.listdir(ImagesDir):
	# Uses regular expressions to find tif/tiff extensions
	if re.search(Extension_Pattern, FileName, flags=re.IGNORECASE):
		# Splits the filename from extension to label the data
		Split_Filename = re.split(Extension_Pattern, FileName, flags=re.IGNORECASE)
		# Gets the wavelength by splitting up the filename at the _
		get_wavelength = Split_Filename[0].split('_')
		# Gets the common filename without the wavelength by joining everything bar the wavelength back together
		common_filename = '_'.join(get_wavelength[0:-1])
		if common_filename not in image_dict:
			image_dict[common_filename]={}
		if re.match('w[1-9]', get_wavelength[-1], flags=re.IGNORECASE): #  Figure out way to put in order using W2, 3, 4 for list.
			image_dict[common_filename][str(get_wavelength[-1])] = os.path.join(ImagesDir, FileName)
		else:
			sys.exit('Unknown File Detected')

Manager = RoiManager()

ApplyAll = False

Failed_List = []

TableDict = {}


for Common in image_dict:
	if ApplyAll != True:
		Wavelength_list = image_dict[Common].keys()
		Wavelength_list.sort(key=str.lower)
		Wavelength_GUI = GenericDialog('Select Phase contrast and DAPI wavelengths')
		Wavelength_GUI.addRadioButtonGroup('Choose phase contrast wavelength', Wavelength_list, len(Wavelength_list), 1, Wavelength_list[0])
		Wavelength_GUI.addRadioButtonGroup('Choose DAPI wavelength', Wavelength_list, len(Wavelength_list), 1, Wavelength_list[-1])
		Wavelength_GUI.addCheckbox('Apply to all?', True)
		Wavelength_GUI.showDialog()
		if Wavelength_GUI.wasOKed() != True:
			sys.exit()
		Phase_Wave = Wavelength_GUI.getNextRadioButton()
		DAPI_Wave = Wavelength_GUI.getNextRadioButton()
		ApplyAll = Wavelength_GUI.getNextBoolean()
	Plus_Dict = {}
	for Wavelength in image_dict[Common]:
		Plus_Dict[Wavelength] = (ImagePlus(image_dict[Common][Wavelength]))
	# Resets the ROI Manager
	Manager.reset()
	Zip_File = os.path.join(ROIDir, Common + '.zip')
	if os.path.exists(Zip_File) != True:
		continue
	Manager.runCommand('Open', Zip_File)
	ROI_List = Manager.getSelectedRoisAsArray()

	NumRoi = len(ROI_List)

	for ROI_Index in range(0,len(ROI_List)):
		Cropped_Plus_Dict = {}
		for Channel in Plus_Dict:
			imp = Plus_Dict[Channel]
			# Sets Roi to overlay (Won't transfer to cropped image properly otherwise)
			PolyOverlay = Overlay(ROI_List[ROI_Index])
			imp.setOverlay(PolyOverlay) 
			# Doubles size of area to be cropped (otherwise will have black edges to cropped image)
			EnlargedROI = RoiScaler().scale(ROI_List[ROI_Index], 2, 2, True)
			# Sets the enlarged Roi to the image for duplication
			imp.setRoi(EnlargedROI)
			# Duplicates cropped section of the image based on 
			Cropped = Duplicator().run(imp)
			CroppedOverlay = Cropped.getOverlay()
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
			# This will loop through 1-360 degrees of rotation
			for Degree in range(1, 361):
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
			IJ.run(Cropped, "Rotate... ", "angle=" + str(LowestArea[2]) + " grid=1 interpolation=Bilinear stack")
			# Selects the rotated Roi on the rotated image
			Cropped.setRoi(LowestArea[1])
			# Crops the image using the rotated Roi (Will actually use its bounding box)
			TightCrop = Duplicator().run(Cropped)
			

			if Channel == Phase_Wave:
				Phase_Imp = TightCrop
			elif Channel == DAPI_Wave:
				DAPI_Imp = TightCrop
				Cropped_Plus_Dict[Channel] = TightCrop
			else:
				Cropped_Plus_Dict[Channel] = TightCrop
		# Resets the ROI Manager
		Manager.reset()

		Measure_Rois = []
		# Duplicates the Phase contrast image for thresholding
		Phase_Thresh_imp = Phase_Imp.duplicate()
		# Thresholds the image
		IJ.setAutoThreshold(Phase_Thresh_imp, "Intermodes light")
		IJ.run(Phase_Thresh_imp, "Convert to Mask", "method=Intermodes background=Light calculate black")
		# Runs analyze particles to get cell ROI
		IJ.run(Phase_Thresh_imp, "Analyze Particles...", "size=200-Infinity exclude clear include add") 
		# Gets all ROIs in the Roi Manager as a list
		
		Phase_ROI_List = Manager.getSelectedRoisAsArray()
		# Resets the ROI Manager
		Manager.reset()		
		# If there is more than one ROI in the ROI manager then will skip this image
		if len(Phase_ROI_List) > 1:
			Manager.runCommand(Phase_Thresh_imp, "Combine")
			# Gets the combined roi
			Phase_ROI = Phase_Thresh_imp.getRoi()
		elif len(Phase_ROI_List) == 1:
			# If it is the only ROI will add it to the List
			Phase_ROI = Phase_ROI_List[0]
		else:	
			ROI_Crop_Name = ROI_List[ROI_Index].getName()
			Failed_List.append(Common+' | '+ROI_Crop_Name+' | Phase')
			continue
		
		# Adds ROI to List for measurements
		Measure_Rois.append(Phase_ROI)
		# Duplicates the DAPI image for thresholding
		DAPI_Thresh_Imp = DAPI_Imp.duplicate()
		# Thresholds the image
		IJ.setAutoThreshold(DAPI_Thresh_Imp, "Intermodes dark")
		IJ.run(DAPI_Thresh_Imp, "Convert to Mask", "method=Intermodes background=Dark calculate black")
		# Runs analyze particles to get Nucleoid ROI
		IJ.run(DAPI_Thresh_Imp, "Analyze Particles...", "size=20-Infinity exclude clear include add")
		# Gets the ROI's from the Analyze Particles function
		DAPI_ROI_List = Manager.getSelectedRoisAsArray()
		# If there are multiple seperate particles they will be combined 
		if len(DAPI_ROI_List) > 1:
			Manager.runCommand(DAPI_Thresh_Imp, "Combine")
			# Gets the combined roi
			DAPI_ROI = DAPI_Thresh_Imp.getRoi()
		elif len(DAPI_ROI_List) == 1:
			DAPI_ROI = DAPI_ROI_List[0]
		else:
			ROI_Crop_Name = ROI_List[ROI_Index].getName()
			Failed_List.append(Common+' | '+ROI_Crop_Name+' | DAPI')
			continue
		# Adds ROI to List for measurements
		Measure_Rois.append(DAPI_ROI)
		# Resets the ROI Manager
		Manager.reset()
		Manager.addRoi(Phase_ROI)
		Manager.addRoi(DAPI_ROI)
		Manager.runCommand(DAPI_Thresh_Imp, "XOR")
		Subtracted_ROI = DAPI_Thresh_Imp.getRoi()
		Measure_Rois.append(Subtracted_ROI)
		Manager.reset()

		for Data_Channel in Cropped_Plus_Dict:
			Stats_List = []
			if Data_Channel not in TableDict:
				TableDict[Data_Channel] = []
				for NumTables in range(0, 11):
					TableDict[Data_Channel].append(ResultsTable())

			while NumRoi > TableDict[Data_Channel][9].size():
				for Table in TableDict[Data_Channel]:
					Table.incrementCounter()
			
			Cropped_Imp = Cropped_Plus_Dict[Data_Channel]
			for MRoi in Measure_Rois:
				Cropped_Imp.setRoi(MRoi)
				Stats = Cropped_Imp.getStatistics()
				Stats_List.append(Stats)

			Cell_Mean = Stats_List[0].mean
			Cell_Area = Stats_List[0].area
			Nucleoid_Mean = Stats_List[1].mean
			Nucleoid_Area = Stats_List[1].area
			Excluded_Mean = Stats_List[2].mean
			Excluded_Area = Stats_List[2].area
			Nucleoid_Fraction = Nucleoid_Area/Cell_Area
			Nucleoid_Excluded_Fraction = Nucleoid_Area/Excluded_Area
			Nucleoid_Excluded_Diff = Excluded_Mean-Nucleoid_Mean
			Normalised_Nucleoid_Excluded_Diff = Nucleoid_Excluded_Diff/Cell_Mean
			Nucleoid_Compaction = Cell_Area/Nucleoid_Area			

			Output_List = [Cell_Mean, Cell_Area, Nucleoid_Mean, Nucleoid_Area, Excluded_Mean, Excluded_Area, Nucleoid_Fraction, 
						   Nucleoid_Excluded_Fraction, Nucleoid_Excluded_Diff, Normalised_Nucleoid_Excluded_Diff, Nucleoid_Compaction]

			for List_Index in range(0, 11):
				TableDict[Data_Channel][List_Index].setValue('Cell', ROI_Index, ROI_Index + 1)
				TableDict[Data_Channel][List_Index].setValue(Common, ROI_Index, Output_List[List_Index])
			Cropped_Imp.close()


SaveList = ['Cell-Mean', 'Cell-Area', 'Nucleoid-Mean', 'Nucleoid-Area', 'Excluded-Mean', 'Excluded-Area', 'Nucleoid-Fraction', 
			'Nucleoid-Excluded-Fraction', 'Nucleoid-Excluded-Difference', 'Nucleoid-Excluded-Difference-Normalised', "Nucleoid-Compaction"]
for Key in TableDict:
	for Index in range(0, 11):
		TableDict[Key][Index].save(SaveTimePath + Key + '_' + SaveList[Index] + '.csv')

Manager.show()
if len(Failed_List) > 0:
	ErrorFile = open(SaveTimePath+'_Errors.txt', 'w')
	GUI_of_Failure = NonBlockingGenericDialog('Failed Files')
	GUI_of_Failure.hideCancelButton()
	for Failure in Failed_List:
		GUI_of_Failure.addMessage(Failure)
		ErrorFile.write(Failure+'\n')
	ErrorFile.close()
	GUI_of_Failure.showDialog()

# If there was an open ROI Manager when the macro was run, this section will Re-open it
if OldManager != None:
	for R in OldRoi:
		Manager.addRoi(R)
