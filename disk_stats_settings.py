import os
import datetime
import logging

#-------------- Logging settings --------------
LOGGING_LEVEL = logging.INFO
LOG_FILE_PATH = os.path.join('/', 'var', 'log')

#-------------- Database settings --------------
DATABASE_PATH = None

#-------------- Analyse settings --------------
ANALYSE_ALL_PARTITIONS = True
# The usage of those devices will not be monitored
EXCLUDED_DEVICES = {
                    }
# The size of these folders will be monitored
WATCHED_PATH = {
               }
# The to use to store the size of all files in a folder
FILE_VIRTUAL_FOLDER_NAME = '<files>'
