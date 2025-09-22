#@ File(label="Input Folder:", value = "", style="directory") InputFolder
#@ File(label="Output Folder:", value = "", style="directory") OutputFolder

import os, re, shutil

from ij import IJ, ImagePlus
from ij.io import RoiEncoder
from ij.gui import NonBlockingGenericDialog

inpath = InputFolder.getPath()
outpath = OutputFolder.getPath()


def main(InputPath, OutputPath):
	regexpattern = re.compile(r"\.tif{1,2}$|\.czi$", re.IGNORECASE)
	for root, dirs, files in os.walk(InputPath):
		files = [f for f in files if regexpattern.search(f)]
		files = [f for f in files if not f.startswith("._")]
		for f in files:
			roi_filename = ".".join(f.split(".")[:-1]) + ".roi"
			Outdir = root.replace(InputPath, OutputPath)
			roi_path = os.path.join(Outdir, roi_filename)
			if os.path.exists(roi_path):
				continue
			if not os.path.exists(Outdir):
				os.makedirs(Outdir)
			Image = ImagePlus(os.path.join(root, f))
			if Image is None:
				IJ.error("Could not open image: " + os.path.join(root, f))
				continue
			gd = NonBlockingGenericDialog("Save ROI?")
			gd.enableYesNoCancel()
			Image.show()
			gd.showDialog()
			if gd.wasCanceled():
				Image.close()
				return
			if gd.wasOKed():
				roi = Image.getRoi()
				RoiEncoder.save(roi, roi_path)

			Image.close()
			continue

if __name__ == "__main__":
	main(inpath, outpath)