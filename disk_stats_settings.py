import os
import datetime
import logging

#-------------- Logging settings --------------
LOGGING_LEVEL = logging.INFO
LOG_FILE_PATH = os.path.join('/', 'var', 'log', 'disk_stats.log')

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

#-------------- Alerts and reports settings --------------
USED_PERCENTAGE_FOR_ALERT = 80
SEND_ALERTS               = False
ALERTS_INTERVAL           = datetime.timedelta(days = 1)
SEND_REPORTS              = False
REPORTS_INTERVAL          = datetime.timedelta(days = 1)

#-------------- Email settings --------------
EMAIL_SERVER    = 'server.tld'
EMAIL_FROM      = 'server_stats@domain.tld'
EMAIL_TO        = 'some.email@domain.tld'
EMAIL_USER_NAME = 'user@domain.tld'
EMAIL_PASSWORD  = 'passwd'

#-------------- Reports settings --------------
DISK_ALERT_STRING           = "The device {device} (on {mount_point}) is used at {use_percentage}%"
DISK_ALERT_SUBJECT          = "Disk usage alerts"
DISK_REPORT_ERROR_STRING    = "disk_stats failed with error {error}"
FOLDER_REPORT_ERRROR_STRING = "folder_stats failed with error {error}"
REPORT_SUBJECT              = "Disk stats report"
