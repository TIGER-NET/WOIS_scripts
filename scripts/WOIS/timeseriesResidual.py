#Definition of inputs and outputs
#==================================
##Timeseries=group
##Timeseries residual=name
##ParameterRaster|dataDir1|im1 - An image located in the time-series 1 (independent variable) directory|False
##ParameterString|filenameFormat1|im1 filename, with date string replaced by Y,M and D (e.g. NDVI_YYYYMMDD_africa.tif)|
##ParameterRaster|dataDir2|im2 - An image located in the time-series 2 (dependent variable) directory|False
##ParameterString|filenameFormat2|im2 filename, with date string replaced by Y,M and D (e.g. NDVI_YYYYMMDD_africa.tif)|
##ParameterFile|outputDir|Output directory where residuals will be saved|True
##ParameterString|outputFileFormat|Output images filename, with YMD where the date string is supposed to be (eg. NDVI_YMD_africa.tif)|
 
#Algorithm body
#==================================

import os
import re
import gdal
import gdalconst
import numpy as np
from processing.core.ProcessingLog import ProcessingLog
from processing.core.GeoAlgorithmExecutionException import GeoAlgorithmExecutionException

class timeseriesResidualUtil():

    def __init__(self):
        None

    def getInputFiles(self, dataDir1, filenameFormat1, dataDir2, filenameFormat2):
        
        # Get a list of all files matching the filename format in the input directories
        fileList1 = list()
        fileList2 = list()
        dates = list()
        inputFiles1 = ""
        inputFiles2 = ""
             
        # regular expression to match the date string in the first filename format
        if dataDir1:
            match1 = self.matchFiles(dataDir1, filenameFormat1, fileList1)
            if match1:
                startDateString = match1.start(0)
                lengthDateString = match1.end(0)-match1.start(0)
                dateRegex1 = "(?<=^.{"+str(startDateString)+"})\d{"+str(lengthDateString)+"}"
                fileList1.sort()
        
        # regular expression to match the date in the second filename format
        if dataDir2:
            match2 = self.matchFiles(dataDir2, filenameFormat2, fileList2) 
            if match2:
                startDateString = match2.start(0)
                lengthDateString = match2.end(0)-match2.start(0)
                dateRegex2 = "(?<=^.{"+str(startDateString)+"})\d{"+str(lengthDateString)+"}" 
                fileList2.sort()
        

        # regular expression to match the full date in the first filename format
        # this will be the datestring of the output files
        #startDateString = match1.start()
        #lengthDateString = match1.end()-match1.start()
        #fullDateRegex = "(?<=^.{"+str(startDateString)+"})\d{"+str(lengthDateString)+"}"         
        
        # now group the files from the two lists according to the datestring
        for filename1 in fileList1:
            match1 = re.search(dateRegex1,filename1)
            if not match1:
                continue
            groupByDate1 = match1.group()
            for filename2 in fileList2:
                match2 = re.search(dateRegex2, filename2)
                if not match2:
                    continue
                groupByDate2 = match2.group()
                if groupByDate2 == groupByDate1:
                    inputFiles1 = inputFiles1 + dataDir1+os.sep+filename1 +";"
                    inputFiles2 = inputFiles2 + dataDir2+os.sep+filename2 +";"
                    dates.append(groupByDate1)
                    break
        # remove last ;
        inputFiles1 = inputFiles1[0:-1]
        inputFiles2 = inputFiles2[0:-1]
        return inputFiles1, inputFiles2, dates           
    
    def matchFiles(self, dataDir, filenameFormat, matchingFiles):
        
        # group by the whole date
        regex = '[YMD]{2,8}'
        
        # first find where the date string is located in the filename and construct a 
        # regex to match it
        match = re.search(regex, filenameFormat)
        if not match:
            ProcessingLog.addToLog(ProcessingLog.LOG_INFO, "No match for date string in filename format!")
            raise GeoAlgorithmExecutionException("No match for date string in filename format!")
        matchLength = match.end()-match.start()
        matchingFormat = re.sub(regex, "\d{"+str(matchLength)+"}", filenameFormat)
        matchingFormat += "$"
        
        # find all the matching files in the data dir
        os.chdir(dataDir)
        for filename in os.listdir("."):
            if re.search(matchingFormat, filename):
                matchingFiles.append(filename)
        return match
       

dataPath1 = None
dataPath2 = None

oldDir = os.getcwd()

utils = timeseriesResidualUtil()
# pair the files from the two input dirs based on the datestring
progress.setText("Looking for matching files.")
if dataDir1:
    dataPath1 = os.path.dirname(dataDir1)
if dataDir2:
    dataPath2 = os.path.dirname(dataDir2)

inputFiles1, inputFiles2, dates = utils.getInputFiles(dataPath1, filenameFormat1, dataPath2, filenameFormat2)
os.chdir(oldDir)

if len(dates) == 0:
    ProcessingLog.addToLog(ProcessingLog.LOG_INFO, "No matching files found! Algorithm will not be executed.")
    raise GeoAlgorithmExecutionException("No matching files found! Algorithm will not be executed.")

# create temporary GDAL VRT file for each list to make it easier to handle later
progress.setText("Creating virtual timeseries rasters.")
vrtFile1 = os.path.join(processing.tools.system.tempFolder(), "list1.vrt")
vrtFile2 = os.path.join(processing.tools.system.tempFolder(), "list2.vrt")
try:
    os.remove(vrtFile1)
    os.remove(vrtFile2)
except:
        pass
processing.runalg("gdalogr:buildvirtualraster", {'INPUT': inputFiles1, 'SEPARATE':True, 'OUTPUT':vrtFile1}) 
processing.runalg("gdalogr:buildvirtualraster", {'INPUT': inputFiles2, 'SEPARATE':True, 'OUTPUT':vrtFile2}) 

# Now use the VRT's to calculate the residuals
vrt1 = gdal.Open(vrtFile1, gdalconst.GA_ReadOnly)
vrt2 = gdal.Open(vrtFile2, gdalconst.GA_ReadOnly)

progress.setText("Calculating residuals for time series with X:"+str(vrt1.RasterXSize)+" Y:"+str(vrt1.RasterYSize)+" Z:"+str(vrt1.RasterCount))
if vrt1.RasterXSize == vrt2.RasterXSize and vrt1.RasterYSize == vrt2.RasterYSize and vrt1.RasterCount == vrt2.RasterCount and vrt1.RasterCount == len(dates):
    xsize = vrt1.RasterXSize
    ysize = vrt1.RasterYSize
    bands = vrt1.RasterCount
    
    # Prepare output file list since each band (date) will be saved in a separate output file
    outDriver = gdal.GetDriverByName("GTiff")
    outDss = list()
    for date in dates:
        outputFile = re.sub('YMD', str(date), outputFileFormat)
        outputFile = re.sub("\..{2,4}$", ".tif", outputFile) # make sure it's a tiff
        outputFile = os.path.join(outputDir, outputFile)
        outDs = outDriver.Create(outputFile, xsize, ysize, 1, gdalconst.GDT_Float32)
        outDs.SetProjection(vrt1.GetProjection())
        outDs.SetGeoTransform(vrt1.GetGeoTransform())
        outDss.append(outDs)
    
    # read the files in in blocks (in case there is long timeseries with large extent) 
    band = vrt1.GetRasterBand(1)  
  
    block_sizes = band.GetBlockSize()  
    x_block_size = block_sizes[0]  
    y_block_size = block_sizes[1] 
    
    for j in range(0, ysize, y_block_size):  
        if j + y_block_size < ysize:  
            rows = y_block_size  
        else:  
            rows = ysize - j 
        for i in range(0, xsize, x_block_size):  
            if i + x_block_size < xsize:  
                cols = x_block_size  
            else:  
                cols = xsize - i
            
            progress.setText("X: "+str(i)+" Y:"+str(j))
            progress.setPercentage( 100.0 * ((float(xsize)/float(x_block_size))*float(j)/float(y_block_size) + float(i)/float(x_block_size)) / ((float(ysize)/float(y_block_size))*(float(xsize)/float(x_block_size))) )
            
            data1 = np.zeros((rows, cols, bands))
            data2 = np.zeros((rows, cols, bands))
            m = np.zeros((rows, cols, bands)) 
            c = np.zeros((rows, cols, bands)) 
            for k in range(1, bands+1):
                bandData1 = vrt1.GetRasterBand(k)
                bandData2 = vrt2.GetRasterBand(k)
                data1[:,:,k-1] = bandData1.ReadAsArray(i, j, cols, rows)
                data2[:,:,k-1] = bandData2.ReadAsArray(i, j, cols, rows)
            
            # calculate residual
            for x in range(data1.shape[1]):
                for y in range(data1.shape[0]):
                    xData = data1[y,x,:]
                    yData = data2[y,x,:]
                    fit = np.linalg.lstsq(np.vstack([xData, np.ones(len(xData))]).T, yData)[0]
                    m[y,x,:] = fit[0]
                    c[y,x,:] = fit[1]      
            residuals = data2 - (m*data1 + c)
                
            #save the data to files
            for band in range(len(outDss)):       
                outDss[band].GetRasterBand(1).WriteArray(residuals[:,:,band], i, j)
                
    vrt1 = None
    vrt2 = None
    for num in range(len(outDss)):
        outDs = outDss.pop()
        outDs = None
    progress.setText("Done!")

else:
        
    vrt1 = None
    vrt2 = None
    raise GeoAlgorithmExecutionException('The rasters in the two lists must have the same size')
    