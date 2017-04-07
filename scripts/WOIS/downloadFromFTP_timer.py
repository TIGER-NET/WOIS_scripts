#Definition of inputs and outputs
#==================================
##Scheduled download from FTP=name
##Tools=group
##ParameterString|host|FTP server address|
##ParameterString|username|Username|
##ParameterString|password|Password|
##ParameterString|remoteDir|Remote Directory|
##ParameterFile|localDir|Local Directory|True|False
##*ParameterExtent|newExtent|Extent to subset after downloading|0,1,0,1
##ParameterString|timestamp|Download files modified since (date in YYYYMMDDhhmmss format)|
##ParameterNumber|startHour|Start download at this hour|0|23|12
##ParameterNumber|startMinute|Start download at this minute|0|59|0
##ParameterBoolean|overwrite|Overwrite existing files|True
 
#Algorithm body
#==================================
import sys
import os
import subprocess
from processing.core.ProcessingLog import ProcessingLog
if not os.path.dirname(scriptDescriptionFile) in sys.path:
    sys.path.append(os.path.join(os.path.dirname(scriptDescriptionFile), "ancillary"))
import ftpDownload



loglines = []
loglines.append('Scheduled download from FTP started.')
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
    #ftpDownload.scheduledFtpDownload(host, username, password, remoteDir, localDir, newExtent, timestamp, startHour, startMinute, overwrite, loglines, progress)
    ftpDownloadPath = os.path.join(os.path.dirname(scriptDescriptionFile), "ancillary", "ftpDownload.py")
    subprocess.Popen(['python', ftpDownloadPath, str(host), str(username), str(password), str(remoteDir), str(localDir), str(newExtent), str(timestamp), str(startHour), str(startMinute), str(overwrite), str(loglines), str("")])
     
ProcessingLog.addToLog(ProcessingLog.LOG_INFO, loglines)
