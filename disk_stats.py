import psutil
import peewee
import os
import datetime
import logging
import logging.handlers
import pickle
import gipkomail
# Settings
import disk_stats_settings as dss
from collections import namedtuple

#================ Database info ================
db = peewee.SqliteDatabase(dss.DATABASE_PATH)
db.connect()

#================ Logging settings ================
logger = logging.getLogger()
logger.setLevel(dss.LOGGING_LEVEL)
formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')
file_handler = logging.handlers.WatchedFileHandler(dss.LOG_FILE_PATH)
file_handler.setFormatter(formatter)
file_handler.setLevel(dss.LOGGING_LEVEL)
logger.addHandler(file_handler)

#================ Other settings ================
date_now = datetime.datetime.now()
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DISK_REPORT_SEPARATOR = "+"+"-"*20+"+"+"-"*40+"+"+"-"*10+"+"+"-"*10+"+"
DISK_REPORT_STRING = "|{device: <20}|{mount_point: <40}|{used_space: >10}|{size: >10}|"
FOLDER_REPORT_SEPARATOR = "+"+"-"*60+"+"+"-"*10+"+"
FOLDER_REPORT_STRING = "|{folder: <60}|{size: >10}|"

#================ ORM classes ================
class FileSystem(peewee.Model):
    """Represents a linux file system in the database

    Attributes:
        name: The name of the file system
    """
    id = peewee.PrimaryKeyField(db_column='id')
    name = peewee.CharField(db_column='name', max_length=128, unique=True)

    class Meta:
        database = db
        db_table = 'server_stats_filesystem'

class MountPoint(peewee.Model):
    """Represents a mount point in the database

    Attributes:
        path: The absolute path to the mount point
    """
    id = peewee.PrimaryKeyField(db_column='id')
    path = peewee.CharField(db_column='path', max_length=128, unique=True)

    class Meta:
        database = db
        db_table = 'server_stats_mountpoint'

class DataPoint(peewee.Model):
    """Represents a data point containing the size, used space, and mount
    point of a file system in the database.

    Attributes:
        size: The size of the file system
        used_space: The space used on the file system
        file_system: The file system (Foreign key on FileSystem)
        mount_point: The mount point of the file system (Foreign key on
                     MountPoint)
    """
    id = peewee.PrimaryKeyField(db_column='id')
    size = peewee.BigIntegerField(db_column='size')
    used_space = peewee.BigIntegerField(db_column='used_space')
    file_system = peewee.ForeignKeyField(db_column='file_system_id', rel_model=FileSystem)
    mount_point = peewee.ForeignKeyField(db_column='mount_point_id', rel_model=MountPoint)
    date = peewee.DateTimeField()

    class Meta:
        database = db
        db_table = 'server_stats_datapoint'

class FolderSize(peewee.Model):
    """Stores the size of a folder

    Attributes:
        parent: The parent folder (Foreign key on FolderSize)
        path: The path of the folder
        size: The size of the folder
        date: The date of the last measurement
    """
    id = peewee.PrimaryKeyField(db_column='id')
    path = peewee.CharField(max_length=256, db_column='path')
    parent = peewee.ForeignKeyField('self', db_column='parent_id', null=True)
    size = peewee.BigIntegerField(db_column='size')
    date = peewee.DateTimeField(db_column='date')

    class Meta:
        database = db
        db_table = 'server_stats_foldersize'

class FolderSizeHistory(peewee.Model):
    """Stores the size of a folder

    Attributes:
        parent: The parent folder (Foreign key on FolderSize)
        path: The path of the folder
        size: The size of the folder
        date: The date of the last measurement
    """
    id = peewee.PrimaryKeyField(db_column='id')
    path = peewee.CharField(max_length=256, db_column='path')
    size = peewee.BigIntegerField(db_column='size')
    date = peewee.DateTimeField(db_column='date')

    class Meta:
        database = db
        db_table = 'server_stats_foldersizehistory'

Report = namedtuple('Report', ('data', 'errors'))

#================ Tool functions ================
def folder_stats(path, parent=None):
    """Computes the size of a folder and its children, recursivly.
    Updates the database.
    """
    folder_size = None
    # We want only one row by path
    try:
        folder_size = FolderSize.get(path=path)
    except FolderSize.DoesNotExist:
        folder_size = FolderSize.create(path=path, parent=parent,
                                        size=0, date=date_now)
    # Compute actual size
    path_size = 0
    base_path, folders, files = next(os.walk(path))
    path_size += sum(folder_stats(os.path.join(base_path, folder),
                                   folder_size) for folder in folders)
    file_size = sum(os.path.getsize(os.path.join(base_path, file_)) for
                                     file_ in files)

    path_size += file_size
    # Create model
    folder_size.size = path_size
    folder_size.save()
    # Create virtual folder for all the files at this level
    file_folder = None
    file_folder_path = os.path.join(base_path, dss.FILE_VIRTUAL_FOLDER_NAME)
    try:
        file_folder = FolderSize.get(path=file_folder_path)
    except FolderSize.DoesNotExist:
        file_folder = FolderSize.create(path=file_folder_path,
                                        parent=folder_size, size=file_size,
                                        date=date_now)
    file_folder.save()
    return path_size

SIZE_UNITS = ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']
def sizeof_fmt(size, suffix="o"):
    """Formats a file size to be readable by a bipede

    Arguments:
        size: The size to format, in bytes
        suffix: The unit suffix
    Returns:
        str
    """
    result = "{0}{1}".format(size, suffix)
    for unit in SIZE_UNITS:
        result = '{size:3.1f}{unit}{suffix}'.format(size=size, unit=unit,
                                                  suffix=suffix)
        if abs(size) < 1024:
            return result
        size /= 1024
    return result

def send_reports(disks_report, folders_report):
    reports_dict = {}
    reports_dict_file = os.path.join(BASE_DIR, 'reports_info.pkl')
    # Load reports dict
    try:
        with open(reports_dict_file, 'rb') as f:
            reports_dict = pickle.load(f)
    except FileNotFoundError:
        pass
    # Alerts
    if dss.SEND_ALERTS:
        alerts_lines = []
        devices_on_alert = []
        for disk in disks_report.data:
            use_percentage = 100*disk.used_space/disk.size
            # Get the date of the last alert sent, if no report were sent, make
            # it so we send one this time
            date_last_alert = reports_dict.get(disk.file_system.name,
                                               date_now-2*dss.ALERTS_INTERVAL)
            can_send = date_now-date_last_alert >= dss.ALERTS_INTERVAL
            if use_percentage >= dss.USED_PERCENTAGE_FOR_ALERT and can_send:
                devices_on_alert.append(disk.file_system.name)
                alerts_lines.append(dss.DISK_ALERT_STRING.format(device=disk.file_system.name,
                                                                  mount_point=disk.mount_point.path,
                                                                  use_percentage=int(use_percentage)))
        if alerts_lines:
            text = "\n".join(alerts_lines)
            try:
                gipkomail.EnvoyerMessage(dss.EMAIL_SERVER, dss.EMAIL_FROM,
                                         dss.EMAIL_TO, dss.DISK_ALERT_SUBJECT,
                                         text, dss.EMAIL_USER_NAME,
                                         dss.EMAIL_PASSWORD)
            except Exception as e:
                logger.error("Failed to send alert mail : {e}".format(e=e))
        # Update reports dictionary
        for device in devices_on_alert:
            reports_dict[device] = date_now
    # Report
    date_last_report = reports_dict.get("report", date_now-2*dss.REPORTS_INTERVAL)
    can_send_report = date_now-date_last_report > dss.REPORTS_INTERVAL
    if dss.SEND_REPORTS and can_send_report:
        reports_lines = []
        # Disks report
        if disks_report.data:
            # Table header
            reports_lines.append(DISK_REPORT_SEPARATOR)
            reports_lines.append(DISK_REPORT_STRING.format(device="device",
                                                           mount_point="mount point",
                                                           used_space="used space",
                                                           size="size"))
            reports_lines.append(DISK_REPORT_SEPARATOR)
            for disk in disks_report.data:
                reports_lines.append(DISK_REPORT_STRING.format(device=disk.file_system.name,
                                                              mount_point=disk.mount_point.path,
                                                              used_space=sizeof_fmt(disk.used_space),
                                                              size=sizeof_fmt(disk.size)))
            # Table footer and vertical space
            reports_lines.append(DISK_REPORT_SEPARATOR)
            reports_lines.append("")
        if disks_report.errors:
            reports_lines.append(dss.DISK_REPORT_ERROR_STRING.format(error=disks_report.errors[0]))
            reports_lines.append("")
        # Folders report
        if folders_report.data:
            # Table header
            reports_lines.append(FOLDER_REPORT_SEPARATOR)
            reports_lines.append(FOLDER_REPORT_STRING.format(folder="folder",
                                                             size="size"))
            reports_lines.append(FOLDER_REPORT_SEPARATOR)
            for folder in folders_report.data:
                reports_lines.append(FOLDER_REPORT_STRING.format(folder=folder.path,
                                                                 size=sizeof_fmt(folder.size)))
            # Table footer and vertical space
            reports_lines.append(FOLDER_REPORT_SEPARATOR)
            reports_lines.append("")
        if folders_report.errors:
            reports_lines.append(dss.FOLDER_REPORT_ERRROR_STRING.format(error=folders_report.errors[0]))
            reports_lines.append("")
        # Send report
        if reports_lines:
            # Update reports dictionary
            reports_dict["report"] = date_now
            text = "\n".join(reports_lines)
            try:
                gipkomail.EnvoyerMessage(dss.EMAIL_SERVER, dss.EMAIL_FROM,
                                         dss.EMAIL_TO, dss.REPORT_SUBJECT,
                                         text, dss.EMAIL_USER_NAME,
                                         dss.EMAIL_PASSWORD)
            except Exception as e:
                logger.error("Failed to send report mail : {e}".format(e=e))
    # Save reports dict
    try:
        with open(reports_dict_file, 'wb') as f:
            pickle.dump(reports_dict, f)
    except Exception as e:
        logger.error("Failed to save reports dictionary : {e}".format(e=e))

#================ Main functions ================
def folders_stats():
    logger.info("Starting folders_stats")
    folders_report = Report(data=[], errors=[])
    try:
        # Create tables if necessary
        FolderSize.create_table(fail_silently=True)
        FolderSizeHistory.create_table(fail_silently=True)
        # Use db.atomic for performances
        with db.atomic():
            for path in dss.WATCHED_PATH:
                size = folder_stats(path)
                # Create history for the base directory
                folder_size = FolderSizeHistory.create(path=path, size=size,
                                                       date=date_now)
                folder_size.save()
                folders_report.data.append(folder_size)
        logger.info("folders_stats ending")
    except Exception as e:
        logger.error("Failed to execute disk_stats : {0} ({1})".format(e, e.__class__))
        folders_report.errors.append(e)
    return folders_report

def disk_stats():
    """Reads disk stats and saves them in the database with a timestamp
    """
    logger.info("Starting disk_stats")
    disks_report = Report(data=[], errors=[])
    try:
        # Create tables if necessary
        FileSystem.create_table(fail_silently=True)
        MountPoint.create_table(fail_silently=True)
        DataPoint.create_table(fail_silently=True)
        # Main process
        partitions = psutil.disk_partitions(all=dss.ANALYSE_ALL_PARTITIONS)
        for partition in partitions:
            if partition.device not in dss.EXCLUDED_DEVICES:
                disk_info = psutil.disk_usage(partition.mountpoint)
                file_system = FileSystem.create_or_get(name=partition.device)[0]
                mount_point = MountPoint.create_or_get(path=partition.mountpoint)[0]
                file_system.save()
                mount_point.save()
                data_point = DataPoint.create(size=disk_info.total,
                                              used_space=disk_info.used,
                                              file_system=file_system,
                                              mount_point=mount_point,
                                              date=date_now)
                data_point.save()
                disks_report.data.append(data_point)
        logger.info("disk_stats ended")
    except Exception as e:
        logger.error("Failed to execute folders_stats : {0} ({1})".format(e, e.__class__))
        disks_report.errors.append(e)
    return disks_report

if __name__ == "__main__":
    disks_report = disk_stats()
    folders_report = folders_stats()
    send_reports(disks_report, folders_report)
