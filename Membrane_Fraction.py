import sys, os, re, time
from ij import IJ, ImagePlus
from ij.io import DirectoryChooser
from ij.gui import Overlay, GenericDialog, NonBlockingGenericDialog
from ij.measure import Measurements, ResultsTable
from ij.plugin import Duplicator, RoiRotator, RoiScaler, ImageCalculator, RoiEnlarger
from ij.plugin.frame import RoiManager
from ij.plugin.filter import Analyzer

# Gets any open ROI manager, gets the ROI contained and closes it before starting the macro
OldManager = RoiManager(False).getInstance()
if OldManager != None:
	OldRoi = OldManager.getRoisAsArray()
	OldManager.close()

Old_Settings = Analyzer.getMeasurements()
Settings = Measurements.AREA | Measurements.MEAN | Measurements.ELLIPSE | Measurements.INTEGRATED_DENSITY 
Analyzer.setMeasurements(Settings)

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
		Wavelength_GUI = GenericDialog('Select Phase contrast and Membrane wavelengths')
		Wavelength_GUI.addRadioButtonGroup('Choose phase contrast wavelength', Wavelength_list, len(Wavelength_list), 1, Wavelength_list[0])
		Wavelength_GUI.addRadioButtonGroup('Choose Membrane wavelength', Wavelength_list, len(Wavelength_list), 1, Wavelength_list[1])
		Wavelength_GUI.addCheckbox('Apply to all?', True)
		Wavelength_GUI.showDialog()
		if Wavelength_GUI.wasOKed() != True:
			sys.exit()
		Phase_Wave = Wavelength_GUI.getNextRadioButton()
		Membrane_Wave = Wavelength_GUI.getNextRadioButton()
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
			elif Channel == Membrane_Wave:
				Membrane_Imp = TightCrop
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
		IJ.run(Phase_Thresh_imp, "Analyze Particles...", "size=200-Infinity exclude clear include add pixel") 
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
		
		WholeRoi = RoiEnlarger().enlarge(Phase_ROI, 1)
		CytoplasmRoi = RoiEnlarger().enlarge(Phase_ROI, -1)
        
		# Adds ROI to List for measurements
		Measure_Rois.append(Phase_ROI)
		Measure_Rois.append(WholeRoi)
		Measure_Rois.append(CytoplasmRoi)
		# Resets the ROI Manager
		Manager.reset()
		Manager.addRoi(WholeRoi)
		Manager.addRoi(CytoplasmRoi)
		Manager.runCommand(Phase_Thresh_imp, "XOR")
		MembraneRoi = Phase_Thresh_imp.getRoi()
		Measure_Rois.append(MembraneRoi)
		

		for Data_Channel in Cropped_Plus_Dict:
			if Data_Channel not in TableDict:
				TableDict[Data_Channel] = []
				for NumTables in range(0, 20):
					TableDict[Data_Channel].append(ResultsTable())

			while NumRoi > TableDict[Data_Channel][19].size():
				for Table in TableDict[Data_Channel]:
					Table.incrementCounter()
			
			Cropped_Imp = Cropped_Plus_Dict[Data_Channel]
			TableList = []
			for MRoi in Measure_Rois:
				Manager.addRoi(MRoi)
				TableList.append(Manager.multiMeasure(Cropped_Imp))
				Manager.reset()

			Cell_Mean = TableList[0].getValue("Mean1", 0)
			Cell_Area = TableList[0].getValue("Area1", 0)
			Cell_IntDen = TableList[0].getValue("IntDen1", 0) 
			Cell_Length = TableList[0].getValue("Major1", 0)
			Cell_Width = TableList[0].getValue("Minor1", 0)
			Whole_Mean = TableList[1].getValue("Mean1", 0)
			Whole_Area = TableList[1].getValue("Area1", 0)
			Whole_IntDen = TableList[1].getValue("IntDen1", 0)
			Whole_Length = TableList[1].getValue("Major1", 0)
			Whole_Width = TableList[1].getValue("Minor1", 0)
			Cytoplasm_Mean = TableList[2].getValue("Mean1", 0)
			Cytoplasm_Area = TableList[2].getValue("Area1", 0)
			Cytoplasm_IntDen = TableList[2].getValue("IntDen1", 0) 
			Membrane_Mean = TableList[3].getValue("Mean1", 0)
			Membrane_Area = TableList[3].getValue("Area1", 0)
			Membrane_IntDen = TableList[3].getValue("IntDen1", 0) 
			Membrane_Mean_Fraction = Membrane_Mean/Whole_Mean
			Cytoplasm_Mean_Fraction = Cytoplasm_Mean/Whole_Mean
			Membrane_Integrated_Fraction = float(Membrane_IntDen)/float(Whole_IntDen)
			Cytoplasm_Integrated_Fraction = float(Cytoplasm_IntDen)/float(Whole_IntDen)	

			Output_List = [Cell_Mean, Cell_Area, Cell_IntDen, Cell_Length, Cell_Width, Whole_Mean, Whole_Area, Whole_IntDen, 
							Whole_Length, Whole_Width, Cytoplasm_Mean, Cytoplasm_Area, Cytoplasm_IntDen, Membrane_Mean, 
							Membrane_Area, Membrane_IntDen, Membrane_Mean_Fraction, Cytoplasm_Mean_Fraction,
							Membrane_Integrated_Fraction, Cytoplasm_Integrated_Fraction]

			for List_Index in range(0, 20):
				TableDict[Data_Channel][List_Index].setValue('Cell', ROI_Index, ROI_Index + 1)
				TableDict[Data_Channel][List_Index].setValue(Common, ROI_Index, Output_List[List_Index])
			Cropped_Imp.close()

SaveList = ["Cell-Mean", "Cell-Area", "Cell-IntDen", "Cell-Length", "Cell-Width", "Whole-Mean", "Whole-Area", "Whole-IntDen",
			"Whole-Length", "Whole-Width", "Cytoplasm-Mean", "Cytoplasm-Area", "Cytoplasm-IntDen", "Membrane-Mean",
			"Membrane-Area", "Membrane-IntDen", "Membrane-Mean-Fraction", "Cytoplasm-Mean-Fraction", 
			"Membrane-Integrated-Fraction", "Cytoplasm-Integrated-Fraction"]
for Key in TableDict:
	for Index in range(0, 20):
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
Analyzer.setMeasurements(Old_Settings)