#@ File (label="Image Directory", style="directory") ImageDir
#@ File (label="Roi Directory", style="directory") RoiDir
#@ File (label="Save CSV", style="file") OutputFile
#@ String (choices={".tif", ".nd2", ".czi"}, style="listBox") Extension

from ij import IJ
from ij.measure import ResultsTable
from ij.plugin.filter import Analyzer
from ij.plugin.frame import RoiManager

import os, re

def main(image_dir, roi_dir, output_file, extension):
	if extension == ".tif":
		image_pattern = re.compile(r"\.tif{1,2}$", re.IGNORECASE)
	elif extension == ".nd2":
		image_pattern = re.compile(r"\.nd2$", re.IGNORECASE)
	elif extension == ".czi":
		image_pattern = re.compile(r"\.czi$", re.IGNORECASE)
	image_list = [f for f in os.listdir(image_dir) if image_pattern.search(f)]
	rm = RoiManager(False)
	rt = ResultsTable()
	for image_filename in image_list:
		image_path = os.path.join(image_dir, image_filename)
		roi_path = os.path.join(roi_dir, os.path.splitext(image_filename)[0] + ".zip")
		if os.path.exists(roi_path):
			imp = IJ.openImage(image_path)
			rm.reset()
			rm.open(roi_path)
			rois = rm.getRoisAsArray()
			an = Analyzer(imp, rt)
			for roi in rois:
				imp.setRoi(roi)
				an.measure()
				rt.addValue("Image", image_filename)
			imp.close()
		else:
			print("No ROI found for "+image_filename+", skipping.")
	rt.saveAs(output_file)
	rm.close()

if __name__ == "__main__":
	main(ImageDir.getAbsolutePath(), RoiDir.getAbsolutePath(), OutputFile.getAbsolutePath(), Extension)