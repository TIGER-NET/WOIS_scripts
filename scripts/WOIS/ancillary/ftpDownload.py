import ftplib
import os
import re
import socket
import time
from datetime import datetime, timedelta
from osgeo import gdal
from gdalconst import *
import sys
import traceback

regex='\d{14}'
SUBSET = 1
DONOTSUBSET = 2
FTPRECONNECT = -1

tmpFileList = list();

def downloadFile(filename, f, localDir, timestamp, overwrite, loglines, progress):
    
    # check if the file already exists and if we want to overwrite
    localFile = localDir + os.sep + filename
    if os.path.isfile(localFile) and not overwrite:
        return DONOTSUBSET
    
    # check that the file not a directory
    try:
        nlst = f.nlst('"'+filename + os.sep+'"')
        if len(nlst) > 0:
            return DONOTSUBSET
    except Exception:
        pass
    #else:
    #    setProgressText(progress,"dupa")
        
    
    # check if timestamp is given and if the remote file has a later date then timestamp
    if timestamp.strip():
        cmd = 'MDTM %s' % filename
        try:
            timeStr = f.sendcmd(cmd)
        except ftplib.all_errors:
            setProgressText(progress,'ERROR: cannot obtain timestamp for file %s' % filename)
            appendToLogLine(loglines,'ERROR: cannot obtain timestamp for file %s' % filename)
            return FTPRECONNECT
        try:
            match = re.search(regex, timeStr)
            if match:
                if len(timestamp) > len(match.group(0)):
                    setProgressText(progress,'ERROR: invalid user specified timestamp')
                    appendToLogLine(loglines,'ERROR: invalid user specified timestamp')
                    return DONOTSUBSET
                else:
                    timeRemote = int(match.group(0)[0:len(timestamp)])
                    timeLocal = int(timestamp)
        except ValueError:
            setProgressText(progress,'ERROR: invalid user specified or remote timestamp for %s' % filename)
            appendToLogLine(loglines,'ERROR: invalid user specified or remote timestamp for %s' % filename)
            return DONOTSUBSET
        if timeRemote < timeLocal:
            return DONOTSUBSET
        
    # download the file
    try:
        setProgressText(progress,'Downloading file %s ...' %filename)
        f.retrbinary('RETR %s' % filename, open(localFile, 'wb').write)
    except ftplib.all_errors:
        setProgressText(progress,'ERROR: cannot read file "%s"' % filename)
        appendToLogLine(loglines,'ERROR: cannot read file "%s"' % filename)
        return FTPRECONNECT
    else:
        setProgressText(progress,'Downloaded "%s" to %s' % (filename, localDir))
        appendToLogLine(loglines,'Downloaded "%s" to %s' % (filename, localDir))
    
    return SUBSET


def subsetToExtent(newExtent, localDir, filename, logline, progress):
    import processing
    # if no extent is specified do not subset
    if newExtent == "0,1,0,1":
        return
    
    # otherwise get the subset extent coordinates
    extents = newExtent.split(",")
    try:
        [nxmin, nxmax, nymin, nymax] = [float(i) for i in extents]
    except ValueError:
        setProgressText(progress,'Invalid subset extent !')
        return    
    
    # rename the downloaded file to a temp filename
    tmpFilename = localDir + os.sep + "tmp_" + filename
    localFilename = localDir + os.sep + filename
    try:
        if os.path.exists(tmpFilename):
            os.remove(tmpFilename)
        os.rename(localFilename,tmpFilename)
    except:
        e = sys.exc_info()[0]
        print(e)
        traceback.print_exc()
    
    # It would be easier to get the raster extents using QgsRasterLayer and not GDAL but
    # there is a bug in QgsRasterLayer that crashes QGIS "randomly" when opening a layer.
    # Maybe it's fixed in QGIS 2.0
    #layer = QGisLayers.getObjectFromUri(tmpFilename)
    #xmin = max(xmin, layer.extent().xMinimum())
    #xmax = min(xmax, layer.extent().xMaximum())
    #ymin = max(ymin, layer.extent().yMinimum())
    #ymax = min(ymax, layer.extent().yMaximum())
    
    # get the minimum extent of the subset extent and the file extent  
    try:
        inlayer = gdal.Open(tmpFilename, GA_ReadOnly)   
    except:
        setProgressText(progress,'Cannot get layer info ! Not subsetting.')
        return
            
    if not inlayer:
        setProgressText(progress,'Cannot get layer info !! Not subsetting.')
        return
            
        
    # get the raster extent coordinates using GDAL
    geoinformation = inlayer.GetGeoTransform(can_return_null = True)

    if geoinformation:
        cols = inlayer.RasterXSize
        rows = inlayer.RasterYSize
        tlX = geoinformation[0] # top left X
        tlY = geoinformation[3] # top left Y
        brX = geoinformation[0] + geoinformation[1] * cols + geoinformation[2] * rows # bottom right X
        brY = geoinformation[3] + geoinformation[4] * cols + geoinformation[5] * rows # bottom right Y

        xmin = min(tlX, brX)
        xmax = max(tlX, brX)
        ymin = min(tlY, brY)
        ymax = max(tlY, brY)
    else:
        setProgressText(progress,'Cannot get layer info !!! Not subsetting.')
        inlayer = None
        return  
    inlayer = None
    
    xmin = max(nxmin, xmin)
    xmax = min(nxmax, xmax)
    ymin = max(nymin, ymin)
    ymax = min(nymax, ymax)
        
    # call gdal_translate to perform the subsetting
    setProgressText(progress,'Subsetting')
    subsetExtent = str(xmin)+","+str(xmax)+","+str(ymin)+","+str(ymax)
    param = {'INPUT':tmpFilename, 'OUTSIZE':100, 'OUTSIZE_PERC':True, 'NO_DATA':"none", 'EXPAND':0, 'SRS':'', 'PROJWIN':subsetExtent, 'EXTRA':'-co "COMPRESS=LZW"', 'SDS':False, 'OUTPUT':localFilename}
    if not processing.runalg("gdalogr:translate",param):
        setProgressText(progress,'Problems with subsetting "%s"' % filename)
        appendToLogLine(loglines,'Problems with subsetting "%s"' % filename)      
    for filename in tmpFileList:
        try:
            os.remove(filename)
            tmpFileList.remove(filename)
        except:
            None;
    tmpFileList.append(tmpFilename)
    setProgressText(progress,'Subsetting finished!')  
            
            
def ftpConnect(host, username, password, remoteDir, loglines, progress):
    setProgressText(progress,'Connecting to FTP!') 
    appendToLogLine(loglines,'Connecting to FTP!')
    if bool(re.match('ftp://', host, re.I)):
        server = host[len('ftp://'):]
    else:
        server = host
    try:
        f = ftplib.FTP(server, timeout = 10)
    except (socket.error, socket.gaierror), e:
        setProgressText(progress,'ERROR: cannot reach "%s"' % server)
        appendToLogLine(loglines,'ERROR: cannot reach "%s"' % server)
        return None
    setProgressText(progress,'Connected to host "%s"' % server)
    appendToLogLine(loglines,'Connected to host "%s"' % server)
    
    if username == "":
        user = 'anonymous'
    else:
        user = username  
    try:
        f.login(user, password)
    except ftplib.error_perm:
        setProgressText(progress,'ERROR: cannot login with provided username and password')
        appendToLogLine(loglines,'ERROR: cannot login with provided username and password')
        f.close()
        return None
    setProgressText(progress,'Logged in as %s' % user)
    appendToLogLine(loglines,'Logged in as %s' % user)
    
    try:
        f.cwd(remoteDir)
    except ftplib.error_perm:
        setProgressText(progress,'ERROR: cannot CD to "%s"' % remoteDir)
        appendToLogLine(loglines,'ERROR: cannot CD to "%s"' % remoteDir)
        f.close()
        return None
    setProgressText(progress,'Changed to "%s" folder' % remoteDir)
    appendToLogLine(loglines,'Changed to "%s" folder' % remoteDir)
    
    return f

# If script is executed as a subprocess in a Python shell then progress in stdout
# Otherwise it is the QGIS Processing progress
def setProgressText(progress, text):
    if not progress:
        print(text)
    else:
        progress.setText(text)

# If script is executed as a subprocess in a Python shell then logline is
# just a string and nothing should be done
# Otherwise it is a QGIS Processing logline
def appendToLogLine(loglines, text):
    try:
        loglines.append(text)
    except:
        pass

            
def ftpDownload(host, username, password, remoteDir, localDir, newExtent, timestamp, overwrite, loglines, progress):
    from processing.tools import dataobjects
    
    f = ftpConnect(host, username, password, remoteDir, loglines, progress)
    if not f:
        return

    try:
        files = f.nlst()
    except ftplib.error_perm:
        try:
            f.set_pasv(False)
            files = f.nlst() 
        except:
            setProgressText(progress,'ERROR: can not retrieve file listing from FTP server.')
            appendToLogLine(loglines,'ERROR: can not retrieve file listing from FTP server.')
            f.close()
            return
    
    for filename in files:
        for count in range(1,3): 
            if f:
                res = downloadFile(filename, f, localDir, timestamp, overwrite, loglines, progress)
            else:
                res = FTPRECONNECT
            if res == FTPRECONNECT:
                try:
                    f.close()
                except:
                    None
                f = ftpConnect(host, username, password, remoteDir, loglines, progress)
            else:
                break
        if count == 3:
            setProgressText(progress,'ERROR: can not establish connection with the server!')
            appendToLogLine(loglines,'ERROR: can not establish connection with the server!') 
        if res == SUBSET:
            subsetToExtent(newExtent, localDir, filename, loglines, progress) 
                
    
    setProgressText(progress,'Finished!')
    appendToLogLine(loglines,'Finished!')
    f.close()
    
    # Clean up
    dataobjects.resetLoadedLayers()
    for tmpFile in tmpFileList:
        try:
            os.remove(tmpFile)
        except:
            setProgressText(progress,'WARNING: can not delete temporary file "%s"' %tmpFile)
            appendToLogLine(loglines,'WARNING: can not delete temporary file "%s"' %tmpFile)
        if os.path.isfile(tmpFile+".aux.xml"):
            try:
                os.remove(tmpFile+".aux.xml")
            except:
                pass
    
    return


def scheduledFtpDownload(host, username, password, remoteDir, localDir, newExtent, timestamp, startHour, startMinute, overwrite, loglines, progress):
    
    # Set the time to download
    downloadTime = datetime.now()
    if downloadTime.hour >= int(startHour) and downloadTime.minute >= int(startMinute):
        downloadTime = downloadTime + timedelta(days=1)
    downloadTime = downloadTime.replace(hour = int(startHour), minute = int(startMinute), second = 0)
    
    # Wait until the right time
    now = datetime.now()
    minute = now.minute
    dif = downloadTime - now
    setProgressText(progress,"Download starting in " + str(dif.days * 1440 + dif.seconds / 60) + " minutes...")
    while now < downloadTime:
        if minute != now.minute:
            minute = now.minute
            dif = downloadTime - now
            setProgressText(progress,"Download starting in " + str(dif.days * 1440 + dif.seconds / 60) + " minutes...")
        time.sleep(2)
        now = datetime.now()
   
    # Start the download
    ftpDownload(host, username, password, remoteDir, localDir, newExtent, timestamp, overwrite, loglines, progress) 
    

if __name__ == "__main__":
    try:
        # Initialize QGIS and Processing if running as a subprocess
        # First find paths of QGIS Python libraries and of Processing 
        # Assumes OsGeo4W installation
        qgisPath = sys.executable
        qgisPath = os.path.dirname(os.path.dirname(qgisPath))
        qgisPath = os.path.join(qgisPath, "apps", "qgis", "python")
        sys.path.append(qgisPath)
        # Assumes processing plugin is in the user directory
        processingPath = os.path.join(os.path.expanduser("~"), ".qgis2", "python", "plugins")
        sys.path.append(processingPath)
        # Initialise QGIS
        from qgis.core import *
        app = QgsApplication([], True)
        app.setPrefixPath(os.path.dirname(qgisPath))
        app.initQgis()
        # Initialise Processing
        import processing
        from processing.core.Processing import Processing
        Processing.initialize()
        
        print(sys.argv[1:])
        scheduledFtpDownload(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7],
                             sys.argv[8], sys.argv[9], sys.argv[10] == "True", sys.argv[11], sys.argv[12])
    except :
        e = sys.exc_info()[0]
        print(e)
        traceback.print_exc()
    print("Press Enter...")
    raw_input()
        