# SpotMeasure

SpotMeasure is an image analysis program designed to measure how far into a region of interest fluorescent spots are located.

Sample uses: Analysis of retroviral integration sites. Evaluation of gene localisation within the nucleus.

[Img]

## Download

[Available for Download Here](https://github.com/DavidStirling/SpotMeasure/releases/)
[Link to releases page and latest release]

## Referencing

[Ref details will go here]

## Compatibility

Releases of this program are supported on **Windows 7** or newer and **Mac OS X 10.12 “Sierra”** or newer.
Releases are standalone applications which include all necessary dependencies.

For other operating systems the source code is freely available on GitHub. This software was written in Python 3.6, key dependencies are the NumPy, SciPy, Scikit-Image and PIL libraries. Compatibility on other systems is untested but feedback is welcome.

# Using SpotMeasure

SpotMeasure makes use of a tabbed interface which can be followed to setup and complete an analysis run.

## Input

This program reads greyscale **.tif** files which can be exported from most microscopes. The current software version is capable of handling image stacks (a single file containing multiple fields or z-planes).

To setup an analysis you need to generate two lists of files which will be displayed on this screen. "Region" images should contain the regions of interest (e.g. nuclei) while "Spot" images feature the objects within each region which you'd like to evaluate. File lists are populated as follows:

1) Select the directory containing the images to be analysed.
2) Choose a keyword unique to each type of image. If your files don't contain the channel name, you can manually specify this using a custom keyword (e.g. "DAPI"). Keyword searching is **case-sensitive.**
3) Click "Generate File List" to populate the two lists.
4) Adjust, add and remove files using the central controls to ensure that images in the region and spot file lists are correctly paired.

Additional options:

- Specify whether to search for images in subdirectories - folders within the chosen directory.
- Manually specify the bit depth of the files you're loading. This will normally be automatic.
- Choose whether to search for a keyword within just the file name, the name & subdirectory within the chosen folder or the entire path to the file.

Once file lists are populated, move on to the "Region Detection" and "Spot Detection" tabs.

## Region/Spot Detection

[Img]

The next two tabs allow you to configure detection of regions and spots respectively.

If images were successfully detected in the input tab the first image will be loaded for previewing, otherwise you can manually choose an image using the "select file" button.

#### File Controls

This section allows you to cycle through images in the file list and any planes within each image in a stack.

**Display mode** indicates the detected bit depth of the currently loaded image. Different cameras have different dynamic ranges of possible intensity values for each pixel which can be saved in the .tif format.
This software tries to automatically detect what depth your images have and scale the brightness for display, but this can trip up if you have a lot of blank images at the start of the file list (background may appear very high). To resolve this, either scroll through to an image with positive staining and the bit depth will update itself, or manually specify the display mode on the Input tab.

#### Previewing Pane

Any currently loaded image will be displayed here. You can hover the mouse over a specific pixel and it's intensity value will be displayed in the section below.

#### Detection Options

To perform the analysis the images have to be segmented to identify each cell. Pressing "Refresh Preview" or "Show/Hide Overlay" will attempt to detect the objects in the image. Once complete the preview image will be overlaid with colours which represent individual objects. Each object is given a unique colour to help separate touching regions.

You should expect to see each object detected as a solid mass of each colour. Cells touching the border of the image are excluded from analysis. If detection is not perfect you can adjust the following parameters:

##### Automatic Thresholding

SpotMeasure includes two automatic algorithms for determining a threshold intensity which separates cells from the background:
- **Method 1** is best for finding objects with sharp borders (e.g. nuclei)
- **Method 2** is optimised for objects which have smooth borders (e.g. fluorescent spots with fading intensity towards the edges)
- **Manual** mode can be used to specify a threshold using the slider below. Use the intensity value displayed when hovering over the image to determine the background of the image to assist in setting this.

The automated thresholding algorithms operate based on a histogram of pixel intensities. As such they can be tripped up by images with very high background or very few objects. These methods therefore include a minimum threshold intensity to avoid false positives in blank images.

During a run the software will also attempt to identify images where segmentation has failed, producing spot objects which are excessively large. If too many large objects are detected in the "Spots" image analysis of that field will be abandoned and a note will appear in the log.

##### Smoothing

The smoothing parameter helps to avoid over-segmentation of large objects. Try increasing this if you see single objects being divided into multiple detected regions.

##### Minimum Object Size

The software is optimised for detection at 40x magnification. Objects smaller than the specific size limit will be ignored. Adjust this if you want to restrict analysis based on object size.


---


Once you're comfortable with the detection settings, proceed to the "Output" tab.

## Output

[Img]

#### Output Settings

In this dialog you can create a **log file** in which data will be exported. This will be a .csv file which contains the result measurements performed by the program.

It is also possible to specify a directory where **result images** will be saved to. Result images are smaller image overlays displaying the detected spot (green), measurement line (red) and points used for measurement (white), with a single file for each cell named with the identifying number of each spot in the log file (e.g. Image 2 will be the second spot analysed). This feature can be disabled by unchecking "**Save Result Images**".

[img]

There are also additional options on this tab. **"Restrict analysis to cells with 1 spot"** will prevent the program from analysing any cell which has more than 1 object detected within it. It is also possible to **restrict analysis to a single plane** which can be specified by typing in the relevant text box (useful for working with z stacks).

Once all setup is complete, press the "**Run!**" button to begin analysis. Progress bars will show what the system is currently doing, while additional information will appear in the log box. A run can be interrupted by clicking the "**Stop**" button.

Once complete a message is displayed in the log. It is now safe to open the log file and check your results. Please note that if the log file is opened in another program during the run the software will be unable to add data to it.

---

If you have any questions, problems or suggestions, contact the developer either here or on Twitter - [@DavidRStirling](https://www.twitter.com/DavidRStirling)