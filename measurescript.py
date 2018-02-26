import os
from csv import writer as csvwriter
from math import hypot

import numpy as np
import skimage.measure
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import label2rgb
from skimage.draw import line
from skimage.feature import peak_local_max
from skimage.filters import threshold_li, threshold_otsu
from skimage.filters.rank import maximum
from skimage.morphology import watershed, remove_small_holes, remove_small_objects, disk
from skimage.segmentation import clear_border, find_boundaries

# Global Variables
currplane = 1
indexnum = 0
cellnum = 0
savedir = ""
previewdir = ""
imgfile = ""


# Preview generator for debugging
def genpreview(tgt, name):
    preview = Image.fromarray(tgt)
    savetgt = previewdir + name + ".tif"
    preview.save(savetgt)
    print("Preview saved to " + savetgt)


# Generate mini preview files as RGB overlays
def betterpreview(regioninput, spotinput, centcoord, perimcoord, spotcoord, name, multiplier):
    global previewdir
    p, q = line(perimcoord[0], perimcoord[1], centcoord[0], centcoord[1])
    green = np.zeros_like(regioninput)
    green[p, q] = 255
    rgb = np.zeros((regioninput.shape[0], regioninput.shape[1], 3), 'uint8')
    rgb[..., 1] = spotinput / multiplier
    rgb[..., 0] = green
    rgb[..., 2] = regioninput / multiplier
    rgb[centcoord[0], centcoord[1]] = 255
    rgb[perimcoord[0], perimcoord[1]] = 255
    rgb[spotcoord[0], spotcoord[1]] = 255
    preview = Image.fromarray(rgb)
    savetgt = previewdir + str(name) + ".tif"
    preview.save(savetgt)


def seg_preview(imagearray, automatic, threshold, smoothing, minsize, imgtype):
    multiplier, absolute_min = bit_depth_update(imagearray)
    imagearray2 = imagearray.copy()
    if imgtype == "spots":
        absolute_min *= 2
    if imgtype == "regions" and automatic:
        threshold = threshold_li(imagearray2)  # li > otsu for finding threshold
        # threshold = threshold_otsu(imagearray2)  # li > otsu for finding threshold
    elif imgtype == "spots" and automatic:
        imgmax = maximum(imagearray2 // multiplier, disk(10))  # Enlarge spots to assist thresholding
        threshold = (threshold_otsu(imgmax) * multiplier)  # Generate otsu threshold for peaks.
    if absolute_min > threshold:
        threshold = absolute_min  # Set a minimum threshold in case an image is blank.
    mask = imagearray2 < threshold
    imagearray2[mask] = 0  # Remove background
    binary = imagearray2 > 0
    binary = remove_small_holes(binary, min_size=1000)  # Clear up any holes
    distance = ndi.distance_transform_edt(binary)  # Use smoothed distance transform to find the midpoints.
    blurred = ndi.gaussian_filter(distance, sigma=smoothing)
    local_maxi = peak_local_max(blurred, indices=False)
    markers = ndi.label(local_maxi)[0]  # Apply labels to each peak
    labels = watershed(-distance, markers, mask=binary)  # Watershed segment
    segmentation = clear_border(labels)  # Remove segments touching borders
    segmentation = remove_small_objects(segmentation, min_size=minsize)
    labelled = label2rgb(segmentation, image=imagearray2, bg_label=0, bg_color=(0, 0, 0), kind='overlay')
    labelled = (labelled * 256).astype('uint8')
    return labelled


def getseg(imagearray, settings, imgtype):
    automatic, threshold, smoothing, minsize = settings
    multiplier, absolute_min = bit_depth_update(imagearray)
    if imgtype == "spot":
        absolute_min *= 2
    imagearray2 = imagearray.copy()
    if automatic:
        if imgtype == "region":
            threshold = threshold_li(imagearray2)  # li > otsu for finding threshold
        else:
            imgmax = maximum(imagearray2 // multiplier, disk(10))  # Enlarge spots to assist thresholding
            threshold = (threshold_otsu(imgmax) * multiplier)  # Generate otsu threshold for peaks.
        if absolute_min > threshold:
            threshold = absolute_min  # Set a minimum threshold in case an image is blank.
    mask = imagearray2 < threshold
    imagearray2[mask] = 0  # Remove background
    binary = imagearray2 > 0
    binary = remove_small_holes(binary, min_size=1000)  # Clear up any holes
    distance = ndi.distance_transform_edt(binary)  # Use smoothed distance transform to find the midpoints.
    blurred = ndi.gaussian_filter(distance, sigma=smoothing)
    local_maxi = peak_local_max(blurred, indices=False)
    markers = ndi.label(local_maxi)[0]  # Apply labels to each peak
    labels = watershed(-distance, markers, mask=binary)  # Watershed segment
    segmentation = clear_border(labels)  # Remove segments touching borders
    segmentation = remove_small_objects(segmentation, min_size=minsize)
    properties = skimage.measure.regionprops(segmentation)
    centroids = [[int(point) for point in pair] for pair in [item.centroid for item in properties]]
    labels = np.unique(segmentation)[1:]
    return segmentation, properties, centroids, labels


def makesubsets(roilabel, regionseg, regionprops, regionc, spotc, origregion, origspot):
    labellist = np.ndarray.tolist(np.unique(regionseg))
    # Need to find index of correct label
    indexid = labellist.index(roilabel)
    a, b, c, d = regionprops[indexid - 1].bbox
    # Add a border just to ease visualisation
    a -= 1
    b -= 1
    c += 1
    d += 1
    roiregion = regionseg.copy()[a:c, b:d]
    roiregionraw = origregion.copy()[a:c, b:d]
    roispotraw = origspot.copy()[a:c, b:d]
    # Generate filtespot mask
    regioncentroid = regionc[indexid - 1]
    # Remove other regions from the image
    roiregion = np.where(roiregion == roilabel, 65000, 0)
    roiregionlist = np.transpose(np.nonzero(roiregion))
    # Create list of points within region
    roiregionlist = np.ndarray.tolist(roiregionlist)
    roiregioncentroid = [regioncentroid[0] - a, regioncentroid[1] - b]
    # Filter spot centroid list for tgt region & correct for subsetting.
    roispotcentroids = [[x[0] - a, x[1] - b] for x in spotc if (c > x[0] > a) and (d > x[1] > b)]
    # Check the centroids are within the nuclei
    roispotcentroids = [x for x in roispotcentroids if x in roiregionlist]
    return roiregion, roiregioncentroid, roispotcentroids, roiregionraw, roispotraw


def find_perim(roiregion):
    edges = find_boundaries(roiregion)
    perim = np.transpose(np.nonzero(edges))
    perim = np.ndarray.tolist(perim)
    return perim  # Return list of coordinates in the perimeter.


# Returns list of coordinates in the line which intersects centroid and spot.
def get_line_points(center, spot, inputimage):
    points = [center, spot]
    xcoords, ycoords = zip(*points)
    eqinput = np.vstack([xcoords, np.ones(len(xcoords))]).T
    if os.name == 'nt':
        m, g = np.linalg.lstsq(eqinput, ycoords, rcond=None)[0]
    else:
        m, g = np.linalg.lstsq(eqinput, ycoords)[0]
    maxhor = inputimage.shape[1]
    maxver = inputimage.shape[0]
    ver2 = (maxhor - g) / m  # Maximum vertical
    hor2 = (m * maxver) + g  # Maximum horizontal
    ver1 = (0 - g) / m  # Horizontal = 0
    hor1 = g  # Vertical = 0
    plotpoints = []
    # Select coordinates within the bounds of the image.
    # Might want to add some validation to check if everything works
    if 0 < ver1 < maxver:
        plotpoints += [int(ver1), 0]
    if 0 < hor1 < maxhor:
        plotpoints += [0, int(hor1)]
    if 0 < ver2 < maxver:
        plotpoints += [int(ver2), maxhor]
    if 0 < hor2 < maxhor:
        plotpoints += [maxver, int(hor2)]
    draw_line = line(plotpoints[0], plotpoints[1], plotpoints[2], plotpoints[3])
    linepoints = np.transpose(draw_line)
    linepoints = np.ndarray.tolist(linepoints)
    return linepoints


# Finding the correct perimeter spot.
def find_perim_intersect(perim, linepoints, intspotspot):
    # Find all perimeter pixels touched by the line
    both = [x for x in perim if x in linepoints]
    tgtpoint = tuple(intspotspot)  # Get tuple of spot coordinate
    tgtlist = [tuple(item) for item in both]
    tgtlist = np.asarray(tgtlist)
    deltas = tgtlist - tgtpoint
    # Calculate how far each pixel is from the spot.
    dist = np.einsum('ij,ij->i', deltas, deltas)
    # Get ID of the perimeter pixel closest to the spot and choose that point.
    perimpoint = tgtlist[np.argmin(dist)]
    return perimpoint


# Calculate distances
def gennumbers(centpoint, perimpoint, tgtpoint):
    # Calc distance from middle to perim
    dx = abs(centpoint[0] - perimpoint[0])
    dy = abs(centpoint[1] - perimpoint[1])
    totaldist = hypot(dx, dy)
    # Calc distance from middle to spot
    dx2 = abs(centpoint[0] - tgtpoint[0])
    dy2 = abs(centpoint[1] - tgtpoint[1])
    spottocenter = hypot(dx2, dy2)
    # Calc percent transmigration. For completion's sake.
    dx3 = abs(perimpoint[0] - tgtpoint[0])
    dy3 = abs(perimpoint[1] - tgtpoint[1])
    spottoperim = hypot(dx3, dy3)
    percentmigration = spottoperim / totaldist * 100
    return totaldist, spottoperim, spottocenter, percentmigration


def cyclecells(im, im2, region_settings, spot_settings, wantpreview, one_per_cell, stopper, multiplier):
    regionseg, regionproperties, regioncentroids, regionlabels = getseg(im, region_settings, 'region')
    spotseg, spotcentroids, spotcentroids, spotlabels = getseg(im2, spot_settings, 'spot')
    global indexnum
    global cellnum
    spots = 0
    update_progress("plane", len(regionlabels))
    for cell in regionlabels:
        if stopper.wait():
            update_progress("cell", 0)
            roiregion, regioncent, spotcents, braw, rraw = makesubsets(cell, regionseg, regionproperties,
                                                                       regioncentroids, spotcentroids, im, im2)
            perim = find_perim(roiregion)
            if len(spotcents) > 0:
                cellnum += 1
            if (len(spotcents) == 1 and one_per_cell is True) or one_per_cell is False:
                for spot in spotcents:
                    linepoints = get_line_points(regioncent, spot, roiregion)
                    perimpoint = find_perim_intersect(perim, linepoints, spot)
                    dist, spotcenter, spotperim, pctmig = gennumbers(regioncent, perimpoint, spot)
                    global imgfile
                    datawriter(imgfile, (dist, spotcenter, spotperim, pctmig))
                    spots += 1
                    indexnum += 1
                    if wantpreview is True:
                        betterpreview(braw, rraw, regioncent, perimpoint, spot, indexnum, multiplier)
    logevent("Analysed " + str(spots) + " spots in " + str(len(regionlabels)) + " cells.")
    return


def cycleplanes(regionimg, spotimg, region_settings, spot_settings, wantpreview, one_per_cell, stopper):
    img = Image.open(regionimg)
    img2 = Image.open(spotimg)
    if img.mode != 'I;8' and img.mode != 'I;16' and img.mode != 'L':
        logevent("Invalid region file type, skipping")
        update_progress("file", 0)
    elif img2.mode != 'I;8' and img2.mode != 'I;16' and img2.mode != 'L':
        logevent("Invalid spot file type, skipping")
        update_progress("file", 0)
    else:
        numframes = img.n_frames
        update_progress("file", numframes)
        for i in range(numframes):
            if stopper.wait():
                img.seek(i)
                img2.seek(i)
                im = np.array(img)
                im2 = np.array(img2)
                multiplier, absolute_min = bit_depth_update(im)
                global currplane
                currplane = i
                cyclecells(im, im2, region_settings, spot_settings, wantpreview, one_per_cell, stopper, multiplier)


def cyclefiles(regioninput, spotinput, region_settings, spot_settings, wantpreview, logfile, prevdir, one_per_cell,
               stopper):
    global savedir, previewdir, indexnum, imgfile
    indexnum = 0
    savedir = logfile
    previewdir = prevdir
    headers()
    update_progress("starting", len(regioninput))
    for i in range(len(regioninput)):
        logevent(f"Analysing {regioninput[i]}")
        imgfile = regioninput[i]
        if stopper.wait():
            cycleplanes(regioninput[i], spotinput[i], region_settings, spot_settings, wantpreview, one_per_cell,
                        stopper)
    update_progress("finished", 1)
    logevent("Analysis complete!")


# Writes headers in output file
def headers():
    global savedir
    headings = ('File', 'Plane', 'Cell ID', 'Spot ID', 'Perimeter - Centroid', 'Perimeter - Spot', 'Spot - Centroid',
                'Percent Migration')
    try:
        with open(savedir, 'w', newline="\n", encoding="utf-8") as f:
            headerwriter = csvwriter(f)
            headerwriter.writerow(headings)
        f.close()
    except AttributeError:
        print("Directory appears to be invalid")
    except PermissionError:
        print("Unable to write to save file. Please check write permissions.")
    except OSError:
        logevent("OSError, failed to write to save file.")


# Write data to CSV file
def datawriter(exportpath, exportdata):
    global currplane
    writeme = tuple([exportpath]) + tuple([currplane + 1]) + tuple([cellnum]) + tuple([indexnum + 1]) + exportdata
    try:
        with open(savedir, 'a', newline="\n", encoding="utf-8") as f:
            mainwriter = csvwriter(f)
            mainwriter.writerow(writeme)
        f.close()
    except AttributeError:
        logevent("Directory appears to be invalid")
    except PermissionError:
        logevent("Unable to write to save file. Please check write permissions.")
    except OSError:
        logevent("OSError, failed to write to save file.")


# File List Generator
def genfilelist(tgtdirectory, subdirectories, regionkwd, spotkwd, mode):
    regionfiles = [os.path.normpath(os.path.join(root, f)) for root, dirs, files in os.walk(tgtdirectory) for f in
                   files if f.lower().endswith(".tif") and regionkwd in
                   (f if mode == 0 else (os.path.join((os.path.relpath(root, tgtdirectory)), f) if mode == 1 else
                                         (os.path.join(root, f)))) and (root == tgtdirectory or subdirectories)]
    spotfiles = [os.path.normpath(os.path.join(root, f)) for root, dirs, files in os.walk(tgtdirectory) for f in
                 files if f.lower().endswith(".tif") and spotkwd in
                 (f if mode == 0 else (os.path.join((os.path.relpath(root, tgtdirectory)), f) if mode == 1 else
                                       (os.path.join(root, f)))) and (root == tgtdirectory or subdirectories)]
    regionshortnames = [(".." + (os.path.join((os.path.relpath(root, tgtdirectory)), f))[-50:]) for
                        root, dirs, files in os.walk(tgtdirectory) for f in files if
                        f.lower().endswith(".tif") and regionkwd in (f if mode == 0 else (
                            os.path.join((os.path.relpath(root, tgtdirectory)), f) if mode == 1 else (
                                os.path.join(root, f)))) and (root == tgtdirectory or subdirectories)]
    spotshortnames = [(".." + (os.path.join((os.path.relpath(root, tgtdirectory)), f))[-50:]) for root, dirs, files
                      in os.walk(tgtdirectory) for f in files if f.lower().endswith(".tif") and spotkwd in (
                          f if mode == 0 else (
                              os.path.join((os.path.relpath(root, tgtdirectory)), f) if mode == 1 else (
                                  os.path.join(root, f)))) and (root == tgtdirectory or subdirectories)]
    return regionfiles, spotfiles, regionshortnames, spotshortnames
