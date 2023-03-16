## Authors: Dr James Grimshaw | Newcastle University | james.grimshaw@newcastle.ac.uk
## This Fiji macro runs in Jython and will take the mean intensity of rois in the roi manager and subtract that value from the image

from ij import IJ, ImagePlus
from ij.plugin.frame import RoiManager
from ij.plugin.filter import Analyzer,ImageMath
from ij.measure import ResultsTable
import sys

##Accesses last image
imp = IJ.getImage()  

##Accesses ROI manager open and closes plugin if none is open
RM=RoiManager.getInstance()
if RM==None:
	sys.exit('No ROIs Available')

##Gets indexes of ROI and selects all of them
Ind=RM.getIndexes()
RM.setSelectedIndexes(Ind)

##Instance of Analyzer which will be used
An=Analyzer(imp)

##Gets the original settings for measurements
original_setting=An.getMeasurements()

##Sets measurements taken to mean only
An.setMeasurements(2)

##Measures mean for all ROIs
measurement=RM.multiMeasure(imp)

##Gets mean out of results table and adds to list
x=0
meanlist=[]
while measurement.columnExists(x)==True:	
	mean=measurement.getColumn(x)
	meanlist.append(mean[0])
	x+=1

##Calculates mean of list of means from ROIs
meanmean=sum(meanlist)/len(meanlist)

##Restores original settings for measurements
An.setMeasurements(original_setting)

##Creates setting for subtract command
subvalue="value="+str(meanmean)

##Runs Subtract Command
IJ().run(imp,"Subtract...",subvalue)

##Resets ROI Manager
RM.reset()