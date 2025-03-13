from java.lang import Double
from ij.gui import ProfilePlot
from ij import IJ
from ij.plugin.frame import RoiManager
from ij.measure import ResultsTable

def getLineProfile(Image, LineRoi):
	"""Gets the fluorescence intensity profile of a line roi

	Args:
		Image (ij.ImagePlus): Image to be measured
		LineRoi (ij.gui.Line): Line to be used for intensity profile

	Returns:
		[float]: X values of the profile
		[float]: Y values of the profile
	"""
	
	# Adds the line roi to the image
	Image.setRoi(LineRoi)
	# Generates the fluorescence intesnsity profile
	Fluor_Profile = ProfilePlot(Image)
	# Gets the Plot obj 
	Fluor_Plot = Fluor_Profile.getPlot()
	# Pulls the values for X from the plot (as float array)
	X_Values = Fluor_Plot.getXValues()
	# Pulls the values for Y straight from 
	# the ProfilePlot (as a double array)
	Y_Values = Fluor_Profile.getProfile()
	# Converts the float array of X values into a 
	# double array (needed for the curve fitting)
	X_Double = []
	for Value in X_Values:
		X_Double.append(Double(Value))
	return X_Double, Y_Values

def main():
	# Get the active image
	Image = IJ.getImage()
	# Get the active RoiManager
	RoiMan = RoiManager.getInstance()
	# Get the selected roi
	RoiMan.deselect()
	LineRoiList = RoiMan.getRoisAsArray()
	outdict = {}
	maxlength = 0
	i = 1
	for line in LineRoiList:
		if line.isLine():
			X, Y = getLineProfile(Image, line)
			outdict["Y"+str(i)] = Y
			if len(X) > maxlength:
				outdict["X"] = X
				maxlength = len(X)
			i += 1
	
	# Create a ResultsTable
	Results = ResultsTable()
	# Add the data to the ResultsTable
	for l in range(maxlength):
		for ii in range(1, i):
			if ii == 1:
				Results.addValue("X", outdict["X"][l])
			try:
				Results.addValue("Y"+str(ii), outdict["Y"+str(ii)][l])
			except IndexError:
				Results.addValue("Y"+str(ii), "NaN")
		if l < maxlength - 1:
			Results.incrementCounter()
	Results.show("Results")

if __name__ == '__main__':
	main()
	
