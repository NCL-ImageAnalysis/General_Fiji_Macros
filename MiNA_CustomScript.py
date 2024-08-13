#@ File(label="Input Images Folder:", value = "", style="directory") InputFolder
#@ File(label="Roi Folder:", value = "", style="directory") RoiFolder
#@ File(label="Output Folder:", value ="", style="directory") OutputFolder

#@ String(label = "Thresholding Op:", value="otsu", choices={"huang", "ij1", "intermodes", "isoData", "li", "maxEntropy", "maxLikelihood", "mean", "minError", "minimum", "moments", "otsu", "percentile", "renyiEntropy", "rosin", "shanbhag", "triangle", "yen"}) threshold_method

#@ OpService ops
#@ ScriptService scripts
#@ StatusService status
#@ UIService ui


import mina.statistics 
import mina.tables 
import mina.filters 
from mina import mina_view

import warnings
import os
import traceback

from collections import OrderedDict

from ij import IJ
from ij import WindowManager
from ij.gui import Overlay
from ij.measure import Measurements
from ij.plugin import Duplicator
from ij.plugin.frame import RoiManager
from ij.io import FileSaver

from net.imglib2.img.display.imagej import ImageJFunctions

from sc.fiji.analyzeSkeleton import AnalyzeSkeleton_;

# Bioformats Imports
from loci.plugins import BF
from loci.plugins.in import ImporterOptions

def threshold_image(imp):
    # Create and ImgPlus copy of the ImagePlus for thresholding with ops...
    status.showStatus("Determining threshold level...")
    slices = imp.getNSlices()
    frames = imp.getNFrames()
    if imp.getRoi() != None:
        ROI_pos = (imp.getRoi().getBounds().x, imp.getRoi().getBounds().y)
    else:
        ROI_pos = (0, 0)

    imp_calibration = imp.getCalibration()
    imp_channel = Duplicator().run(imp, imp.getChannel(), imp.getChannel(), 1, slices, 1, frames)
    img = ImageJFunctions.wrap(imp_channel)

    # Determine the threshold value if not manual...
    binary_img = ops.run("threshold.%s"%threshold_method, img)
    binary = ImageJFunctions.wrap(binary_img, 'binary')
    binary.setCalibration(imp_calibration)
    binary.setDimensions(1, slices, 1)
    return binary

# The run function..............................................................
def run(imp_original, threshold_method, roiname):
    imp = Duplicator().run(imp_original, imp_original.getChannel(), imp_original.getChannel(), 1, imp_original.getNSlices(), 1, imp_original.getNFrames())

    output_parameters = OrderedDict([("image title", ""),
                                     ("roi name", ""),
                                     ("thresholding op", float),
                                     ("mitochondrial footprint", float),
                                     ("branch length mean", float),
                                     ("branch length median", float),
                                     ("branch length stdev", float),
                                     ("summed branch lengths mean", float),
                                     ("summed branch lengths median", float),
                                     ("summed branch lengths stdev", float),
                                     ("network branches mean", float),
                                     ("network branches median", float),
                                     ("network branches stdev", float),
                                     ("donuts", int)])

    # Perform any preprocessing steps...
    status.showStatus("Preprocessing image...")

    output_parameters["thresholding op"] = threshold_method

    imp_title = imp.getTitle()
    output_parameters["image title"] = imp_title
    output_parameters["roi name"] = roiname
    
    # Determine the threshold value if not manual...
    binary = threshold_image(imp)

    imp_calibration = imp.getCalibration()
    # Get the total_area
    if binary.getNSlices() == 1:
        area = binary.getStatistics(Measurements.AREA).area
        area_fraction = binary.getStatistics(Measurements.AREA_FRACTION).areaFraction
        output_parameters["mitochondrial footprint"] =  area * area_fraction / 100.0
    else:
        mito_footprint = 0.0
        for slice in range(1, binary.getNSlices()+1):
            binary.setSliceWithoutUpdate(slice)
            area = binary.getStatistics(Measurements.AREA).area
            area_fraction = binary.getStatistics(Measurements.AREA_FRACTION).areaFraction
            mito_footprint += area * area_fraction / 100.0
        output_parameters["mitochondrial footprint"] = mito_footprint * imp_calibration.pixelDepth

    # Generate skeleton from masked binary otherwise
    skeleton = Duplicator().run(binary)
    IJ.run(skeleton, "Skeletonize (2D/3D)", "")

    # Analyze the skeleton...
    status.showStatus("Setting up skeleton analysis...")
    skel = AnalyzeSkeleton_()
    skel.setup("", skeleton)
    status.showStatus("Analyzing skeleton...")
    skel_result = skel.run()

    status.showStatus("Computing graph based parameters...")
    branch_lengths = []
    summed_lengths = []
    graphs = skel_result.getGraph()

    num_donuts = 0
    for graph in graphs:
        summed_length = 0.0
        edges = graph.getEdges()
        vertices = {}
        for edge in edges:
            length = edge.getLength()
            branch_lengths.append(length)
            summed_length += length

            # keep track of the number of times a vertex appears in edges in a given graph
            for vertex in [edge.getV1(), edge.getV2()]:
                if vertex in vertices:
                    vertices[vertex] += 1
                else:
                    vertices[vertex] = 1

        is_donut = True
        # donut_arms = 0
        for k in vertices:
            # if a vertex appeared less than twice
            if vertices[k] <= 1:
                # donut_arms += 1
                # if donut_arms > 1:
                is_donut = False
                break

        if is_donut and len(edges) >= 1:
            num_donuts += 1

        summed_lengths.append(summed_length)
    output_parameters["donuts"] = num_donuts

    output_parameters["branch length mean"] = mina.statistics.mean(branch_lengths)
    output_parameters["branch length median"] = mina.statistics.median(branch_lengths)
    output_parameters["branch length stdev"] = mina.statistics.stdev(branch_lengths)

    output_parameters["summed branch lengths mean"] = mina.statistics.mean(summed_lengths)
    output_parameters["summed branch lengths median"] = mina.statistics.median(summed_lengths)
    output_parameters["summed branch lengths stdev"] = mina.statistics.stdev(summed_lengths)

    branches = list(skel_result.getBranches())
    output_parameters["network branches mean"] = mina.statistics.mean(branches)
    output_parameters["network branches median"] = mina.statistics.median(branches)
    output_parameters["network branches stdev"] = mina.statistics.stdev(branches)

    # Create/append results to a ResultsTable...
    morphology_tbl = mina.tables.SimpleSheet("Mito Morphology")
    morphology_tbl.writeRow(output_parameters)
    morphology_tbl.updateDisplay()

    status.showStatus("Done analysis!")
    return binary, skeleton

# Run the script...
if (__name__=="__main__") or (__name__=="__builtin__"):
    RM = RoiManager(True)
    for ImageFile in InputFolder.listFiles():
        try:
            Options = ImporterOptions()
            Options.setId(ImageFile.getPath())
            Options.setSplitChannels(True)
            Import = BF.openImagePlus(Options)
            ImageFilename = ImageFile.getName()
            RoiPath = os.path.join(RoiFolder.getPath(), ".".join(ImageFilename.split('.')[:-1]) + ".zip")
            OutputImageFolder = os.path.join(OutputFolder.getPath(), "Cropped", ImageFilename)
            if not os.path.exists(OutputImageFolder):
                os.makedirs(OutputImageFolder)
            OutputMaskFolder = os.path.join(OutputFolder.getPath(), "Mask", ImageFilename)
            if not os.path.exists(OutputMaskFolder):
                os.makedirs(OutputMaskFolder)
            OutputSkeletonFolder = os.path.join(OutputFolder.getPath(), "Skeleton", ImageFilename)
            if not os.path.exists(OutputSkeletonFolder):
                os.makedirs(OutputSkeletonFolder)
            RM.reset()
            RM.open(RoiPath)
            RoiList = RM.getRoisAsArray()
            for roi in RoiList:
                Import[0].setRoi(roi)
                IJ.run(Import[0], "Remove Overlay", "")
                IJ.run(Import[0], "Add Selection...", "")
                croppedImp = Import[0].crop("stack")
                croppedroi = croppedImp.getOverlay().toArray()[0]
                croppedImp.setRoi(croppedroi)
                IJ.run(croppedImp, "Clear Outside", "stack")
                IJ.run(croppedImp, "Remove Overlay", "")
                binaryout, skeletonout = run(croppedImp, threshold_method, roi.getName())
                FileSaver(croppedImp).saveAsTiff(os.path.join(OutputImageFolder, roi.getName() + ".tif"))
                FileSaver(binaryout).saveAsTiff(os.path.join(OutputMaskFolder, roi.getName() + ".tif"))
                FileSaver(skeletonout).saveAsTiff(os.path.join(OutputSkeletonFolder, roi.getName() + ".tif"))
        except Exception:
            print("Could not process:", ImageFile.getPath(), "\n Error:")
            traceback.print_exc()
            
