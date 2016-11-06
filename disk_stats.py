import psutil
import peewee
import os
import datetime
import logging
import logging.handlers
# Settings
import disk_stats_settings as dss

#================ Database info ================
db = peewee.SqliteDatabase(dss.DATABASE_PATH)

#================ Logging settings ================
logger = logging.getLogger()
logger.setLevel(dss.LOGGING_LEVEL)
formatter = logging.Formatter('%(asctime)s :: %(levelname)s :: %(message)s')
file_handler = logging.handlers.WatchedFileHandler(dss.LOG_FILE_PATH)
file_handler.setFormatter(formatter)
file_handler.setLevel(dss.LOGGING_LEVEL)
logger.addHandler(file_handler)

date_now = datetime.datetime.now()

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

#================ Main functions ================
def folders_stats():
    logger.info("Starting folders_stats")
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
    logger.info("folders_stats ending")

def disk_stats():
    """Reads disk stats and saves them in the database with a timestamp
    """
    logger.info("Starting disk_stats")
    db.connect()
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
    logger.info("disk_stats ended")

if __name__ == "__main__":
    try:
        disk_stats()
    except Exception as e:
        logger.error("Failed to execute disk_stats : {0} ({1})".format(e, e.__class__))
    try:
        folders_stats()
    except Exception as e:
        logger.error("Failed to execute folders_stats : {0} ({1})".format(e, e.__class__))
