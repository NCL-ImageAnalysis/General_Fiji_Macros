#@ Integer (label="Number of random points per set") maxpoints
#@ Integer (label="Number of sets of random points") maxsets

from ij import IJ
from ij.plugin.filter import ThresholdToSelection
from ij.measure import ResultsTable

import random

imp = IJ.getImage()
IJ.setThreshold(imp, 255, 255)
roi = ThresholdToSelection.run(imp)
IJ.resetThreshold(imp)
rect = roi.getBounds()
xscale = imp.getCalibration().pixelWidth
yscale = imp.getCalibration().pixelHeight

outdict = {}
for set in range(maxsets):
	outdict[set] = []
	numpoints = 0
	while numpoints < maxpoints:
		x = random.uniform(rect.x, rect.x + rect.width)
		y = random.uniform(rect.y, rect.y + rect.height)
		if roi.containsPoint(x, y):
			scaledx = x * xscale
			scaledy = y * yscale
			outdict[set].append((scaledx, scaledy))
			numpoints += 1

rt = ResultsTable()
rt.showRowNumbers(True)
for i in range(maxpoints):
	for set in range(maxsets):
		rt.addValue("X" + str(set + 1), outdict[set][i][0])
		rt.addValue("Y" + str(set + 1), outdict[set][i][1])
	if i < maxpoints - 1:
		rt.incrementCounter()
rt.show("Random Points")
		
	


