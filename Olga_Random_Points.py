#@ Integer (label="Number of random points per set") maxpoints
#@ Integer (label="Number of sets of random points") maxsets

from ij import IJ
from ij.measure import ResultsTable
from ij.plugin.filter import ThresholdToSelection

import random

imp = IJ.getImage()
IJ.setThreshold(imp, 255, 255)
# Get the ROI from the binary mask
roi = ThresholdToSelection.run(imp)
IJ.resetThreshold(imp)
# Get bounding box of ROI for range random points will be generated in
rect = roi.getBounds()

# Get the scale of the image for converting to scaled coordinates
xscale = imp.getCalibration().pixelWidth
yscale = imp.getCalibration().pixelHeight

outdict = {}
for set in range(maxsets):
	outdict[set] = []
	numpoints = 0
	while numpoints < maxpoints:
		# Gets random float points within bounding box
		x = random.uniform(rect.x, rect.x + rect.width)
		y = random.uniform(rect.y, rect.y + rect.height)
		# If falls within the roi will scale and add to the dictionary
		if roi.containsPoint(x, y):
			scaledx = x * xscale
			scaledy = y * yscale
			outdict[set].append((scaledx, scaledy))
			numpoints += 1

# Outputs the results to a results table-------------------v
rt = ResultsTable()
rt.showRowNumbers(True)
for i in range(maxpoints):
	for set in range(maxsets):
		rt.addValue("X" + str(set + 1), outdict[set][i][0])
		rt.addValue("Y" + str(set + 1), outdict[set][i][1])
	# Need to increment counter but not for the last point so dont get an empty row
	if i < maxpoints - 1:
		rt.incrementCounter()
rt.show("Random Points")
#----------------------------------------------------------^
		
	


