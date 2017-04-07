#Definition of inputs and outputs
#==================================
##Sentinel tools=group
##Unzip Sentinel-2 data=name
##ParameterFile|inFile|zipped file|False|False|zip
##OutputDirectory|processingDir|Directory to unzip data to

import os
import glob
import zipfile

def unzip(src_file, dst_dir):
    with zipfile.ZipFile(src_file) as zf:
        zf.extractall(u'\\\\?\\' + dst_dir)

progress.setConsoleInfo('Starting unzip')
unzip(inFile, processingDir)
progress.setConsoleInfo('Unzip finished...')
