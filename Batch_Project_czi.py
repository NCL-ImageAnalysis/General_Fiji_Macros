#@ File(label="Input Folder:", value = "", style="directory") InputFolder
#@ File(label="Output Folder:", value = "", style="directory") OutputFolder
#@ String(label="Projection Method", choices=["max", "avg", "min", "sum", "sd", "median"], value="max", style="listBox") ProjectionMethod

import os, re
from ij import ImagePlus
from ij.plugin import ZProjector
from ij.io import FileSaver

inpath = InputFolder.getPath()
outpath = OutputFolder.getPath()

def main(InFolder,
		 OutFolder,
		 Method):
	for root, dirs, files in os.walk(InFolder):
		for f in files:
			if re.search(r'\.czi$', f, re.IGNORECASE):
				imp = ImagePlus(os.path.join(root, f))
				zproj = ZProjector.run(imp, Method)
				outfilename = ".".join(f.split(".")[:-1]) + "_" + Method + "_projection.tif"
				out_folder = root.replace(InFolder, OutFolder)
				if not os.path.exists(out_folder):
					os.makedirs(out_folder)
				saver = FileSaver(zproj)
				saver.saveAsTiff(os.path.join(out_folder, outfilename))
	imp.close()
	zproj.close()
if __name__ == "__main__":
	main(inpath,
		 outpath,
		 ProjectionMethod)