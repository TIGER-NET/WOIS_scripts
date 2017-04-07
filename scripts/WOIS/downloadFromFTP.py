#Definition of inputs and outputs
#==================================
##Download from FTP=name
##Tools=group
##ParameterString|host|FTP server address|
##ParameterString|username|Username|
##ParameterString|password|Password|
##ParameterString|remoteDir|Remote Directory|
##ParameterFile|localDir|Local Directory|True|False
##*ParameterExtent|newExtent|Extent to subset after downloading|0,1,0,1
##ParameterString|timestamp|Download files modified since (date in YYYYMMDDhhmmss format)|
##ParameterBoolean|overwrite|Overwrite existing files|True
 
#Algorithm body
#==================================
import os
from processing.core.ProcessingLog import ProcessingLog
import sys
if not os.path.dirname(scriptDescriptionFile) in sys.path:
    sys.path.append(os.path.join(os.path.dirname(scriptDescriptionFile), "ancillary"))
# imported from ancillary folder
import ftpDownload

loglines = []
loglines.append('Download from FTP script console output')
loglines.append('')

# create the local directory if it doesn't exist
if not os.path.isdir(localDir):
    try:
        os.makedirs(localDir)
        progress.setText('Created local directory %s' % localDir)
        loglines.append('Created local directory %s' % localDir)
    except:
        progress.setText('Can not create local directory %s' % localDir)
        loglines.append('Can not create local directory %s' % localDir)
    
if os.path.isdir(localDir):
    ftpDownload.ftpDownload(host, username, password, remoteDir, localDir, newExtent, timestamp, overwrite, loglines, progress)
    #ftpDownload(loglines)
    
ProcessingLog.addToLog(ProcessingLog.LOG_INFO, loglines)
