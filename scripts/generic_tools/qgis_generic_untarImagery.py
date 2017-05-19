#Definition of inputs and outputs
#==================================
##Generic Tools=group
##Untar Imagery=name
##ParameterFile|inFile|tar.gz file|False|False|gz
##OutputDirectory|processingDir|Directory to untar data to

import glob
import os
import tarfile
    
def untar(inFile, processingDir):
    
    tar = tarfile.open(inFile)
    
    tar.extractall(processingDir)
    tar.close()
    
progress.setConsoleInfo('Starting untar')
untar(inFile, processingDir)
progress.setConsoleInfo('Untar finished...')
       