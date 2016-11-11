# server_stats
## What is it ?
This repository will contain an ensemble of services monitoring and logging information about a system.
### disk_stats
disk_stats is a service logging the use of physical disks and the size of specific folders.

Before using it, a few settings must be changed :
* DATABASE_PATH must be a path to the sqlite3 database file to use. If the file does not exist, it will be created.

To enable the emails :
* SEND_ALERTS must be set to True if you wish to receive disk usage alerts
* SEND_REPORTS must be set to True if you wish to receive the reports
* all the EMAIL_* settings must be set to valid values
* EMAIL_USER_NAME and EMAIL_PASSWORD can be None if there is no authentication on the server


## Dependancies
* python 3 (developed and tested with python 3.5)
* peewee
* psutil

## License
This work is licensed under [Creative Commons Attribution-NonCommercial 4.0 International](https://creativecommons.org/licenses/by-nc/4.0/legalcode)

You are free to share and adapt it as long as you give appropriate credit, provide a link to the license and indicate if changes were made.

You may use it as you want as long as it is not for commercial purposes.

# Authors
* Thomas Coeffic (Eusmilis)
* JP Coeffic for gipkomail
