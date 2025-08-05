from fastapi import FastAPI, HTTPException, Path, Query
from pydantic import BaseModel
from typing import Annotated, Final, List
import logging
import os
import sqlite3


class ModelGAV(BaseModel):
    group_id: str
    artifact_id: str
    artifact_version: str
    file_name: str
    major_version: int
    version_seq: int
    last_modified: str
    size: int
    sha1: str
    signature_exists: int
    sources_exists: int
    javadoc_exists: int
    classifier: str
    file_extension: str
    packaging: str
    name: str

class ModelLastModified(BaseModel):
    last_modified: str

class ModelUpgrade(BaseModel):
    artifact_version: str
    last_modified: str


class DBMetadata:

    MAXLEN_GROUP_ID : Final = 254
    MAXLEN_ARTIFACT_ID : Final = 254
    MAXLEN_ARTIFACT_VERSION : Final = 128
    MAXLEN_FILE_NAME : Final = 512


    # Maximum number of items to return in a single page
    PAGE_SIZE : Final = 100

    PAGE_SIZE_BIG : Final = 1000

    # This file is very big
    #  - As Aug 2025 it is 26 GB
    SQLITE_FILE_NAME : Final = "mavendb.sqlite"

    # Reference
    # - https://phiresky.github.io/blog/2020/sqlite-performance-tuning/
    # - https://www.powersync.com/blog/sqlite-optimizations-for-ultra-high-performance
    SQL_PERF_TUNE : Final = [
                'PRAGMA query_only = 1;',
                'PRAGMA journal_mode = DELETE;',
                'PRAGMA synchronous = 0;',
                'PRAGMA cache_size = 100000;',         # 100,000 pages, 1 page = 4096 bytes, so 400 MB
                'PRAGMA journal_size_limit = 33554432;',#  32 MB
                'PRAGMA mmap_size = 536870912;',        # 512 MB
                'PRAGMA synchronous = normal;',
                'PRAGMA temp_store = MEMORY;']

    SQL_SELECT_GAV : Final = """
        SELECT  group_id, artifact_id, artifact_version,
        file_name, major_version, version_seq, last_modified,
        size, sha1, signature_exists, sources_exists, javadoc_exists,
        classifier, file_extension, packaging, name
        FROM gav
        """

    SQL_GAV_SELECT_ALL : Final = SQL_SELECT_GAV + " LIMIT ? OFFSET ?"
    SQL_GAV_SELECT_FILE_NAME : Final = SQL_SELECT_GAV + " WHERE file_name = ? LIMIT 1"
    SQL_GAV_SELECT_FILE_LAST_MODIFIED : Final = "SELECT max(last_modified) FROM gav WHERE file_name LIKE ? LIMIT 1"
    SQL_GAV_SELECT_GAV : Final = SQL_SELECT_GAV + " WHERE group_id = ? AND artifact_id = ? AND artifact_version = ? LIMIT " + str(PAGE_SIZE)

    # This query is used to find newer versions of a file
    SQL_GAV_UPGRADE : Final = "SELECT distinct artifact_version, max(last_modified) AS last_modified from gav WHERE group_id = ? AND artifact_id = ? AND version_seq > ? GROUP BY artifact_version ORDER BY version_seq LIMIT ?"


    # Create a global connection to the database
    # This connection is read-only and can be shared across threads
    # https://docs.python.org/3/library/sqlite3.html#sqlite3.connect
    # https://www.sqlite.org/pragma.html#pragma_mmap_size
    # https://www.sqlite.org/pragma.html#pragma_journal_mode
    # https://www.sqlite.org/pragma.html#pragma_synchronous
    # https://www.sqlite.org/pragma.html#pragma_temp_store
    # https://www.sqlite.org/pragma.html#pragma_journal_size_limit
    # https://stackoverflow.com/questions/7165746/is-it-safe-to-share-a-single-sqlite-connection-across-multiple-threads
    def connect() -> sqlite3.Connection:
        """ Connect to the SQLite database.
        Returns:
            sqlite3.Connection: A connection object to the SQLite database.
        Raises:
            sqlite3.Error: If there is an error connecting to the database.
        """

        try:
            conn = sqlite3.connect('file:' + DBMetadata.SQLITE_FILE_NAME + '?mode=ro', uri=True, check_same_thread=False)
            cur = conn.cursor()
            for sql in DBMetadata.SQL_PERF_TUNE:
               cur.execute(sql)
            cur.close()
            return conn

        except sqlite3.OperationalError as e:
            raise HTTPException(status_code=503, detail="Database is under maintenance and not available. try again after 2 hours.")

     
    def gav2item(row) -> ModelGAV:
        """ Convert a database row to a GAV item.
        Args:
            row (tuple): A tuple containing the row data from the database.
        Returns:
            ModelGAV: An instance of the GAV model populated with the row data.
        Raises:
            ValueError: If the row does not contain the expected number of elements.
        """

        return ModelGAV(
            group_id=row[0],
            artifact_id=row[1],
            artifact_version=row[2],
            file_name=row[3],
            major_version=row[4],
            version_seq=row[5],
            last_modified=row[6],
            size=row[7],
            sha1=row[8],
            signature_exists=row[9],
            sources_exists=row[10],
            javadoc_exists=row[11],
            classifier=row[12],
            file_extension=row[13],
            packaging=row[14],
            name=row[15]
        )


app = FastAPI()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@app.get("/")
async def root():
    """
    Root endpoint returning a simple message.
    """    
    return {"message": "Server is up and running.."}

@app.get("/api/")
async def root():
    """
    Root endpoint returning a simple message.
    """    
    return {"message": "API Server is up and running.."}


@app.get("/api/file/{file_name}", response_model=ModelGAV)
def gav_file_name(
        file_name: str = Path(max_length=DBMetadata.MAXLEN_FILE_NAME)):
    """ Retrieve a GAV item based on the file name.
    Args:
        file_name (str): The name of the file to search for.
    Returns:
        ModelGAV: An instance of the GAV model containing the file information.
    Raises:
        HTTPException: If the file is not found in the database.
    """

    connection = DBMetadata.connect()
    cursor = connection.cursor()
    cursor.execute(DBMetadata.SQL_GAV_SELECT_FILE_NAME, (file_name, ))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="File " + file_name + " not found")

    item = DBMetadata.gav2item(row)
    cursor.close()
    connection.close()
    return item


@app.get("/api/filelastmodified/{file_name}", response_model=ModelLastModified)
def gav_file_last_modified(
        file_name: str = Path(max_length=DBMetadata.MAXLEN_FILE_NAME)):
    """ Retrieve the last modified date of a file based on its name.
    Args:
        file_name (str): The name of the file to search for.
    Returns:
        ModelLastModified: An instance of the LastModified model containing the last modified date.
    Raises:
        HTTPException: If the file is not found in the database or if the file name is too short.
    """

    filename_without_extension, extension = os.path.splitext(file_name)
    if len(filename_without_extension) < 1:
        raise HTTPException(status_code=400, detail="File name is too short: " + file_name)

    connection = DBMetadata.connect()
    cursor = connection.cursor()
    cursor.execute(DBMetadata.SQL_GAV_SELECT_FILE_LAST_MODIFIED, (filename_without_extension + "%", ))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="File " + file_name + " not found")

    item = ModelLastModified(
            last_modified=row[0])

    cursor.close()
    connection.close()
    return item


@app.get("/api/gav", response_model=List[ModelGAV])
def gav(
        skip: int = 0,
        limit: Annotated[int, Query(le=DBMetadata.PAGE_SIZE)] = DBMetadata.PAGE_SIZE):
    """ Retrieve a list of GAV items with pagination.
    Args:
        skip (int): The number of items to skip (for pagination).
        limit (int): The maximum number of items to return (default is 100).
    Returns:
        List[ModelGAV]: A list of GAV items.
    Raises:
        HTTPException: If no items are found in the database.
    """

    connection = DBMetadata.connect()
    cursor = connection.cursor()
    cursor.execute(DBMetadata.SQL_GAV_SELECT_ALL, (limit, skip))
    rows = cursor.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No items found")

    items = []
    for row in rows:
        items.append(DBMetadata.gav2item(row))

    cursor.close()
    connection.close()
    return items


@app.get("/api/gav/{group_id}/{artifact_id}/{artifact_version}", response_model=List[ModelGAV])
def gav(
        group_id: str = Path(max_length=DBMetadata.MAXLEN_GROUP_ID),
        artifact_id: str = Path(max_length=DBMetadata.MAXLEN_ARTIFACT_ID),
        artifact_version: str = Path(max_length=DBMetadata.MAXLEN_ARTIFACT_VERSION)):

    """ Retrieve a single GAV item based on group_id, artifact_id, and artifact_version.
    Args:
        group_id (str): The group ID of the artifact.
        artifact_id (str): The artifact ID.
        artifact_version (str): The version of the artifact.
    Returns:
        ModelGAV: An instance of the GAV model containing the artifact information.  
    Raises:
        HTTPException: If the GAV item is not found in the database.
    """

    gav_str = f"{group_id}/{artifact_id}/{artifact_version}"
    connection = DBMetadata.connect()
    cursor = connection.cursor()
    cursor.execute(DBMetadata.SQL_GAV_SELECT_GAV, (group_id, artifact_id, artifact_version, ))
    rows = cursor.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="GAV " + gav_str + " not found")

    items = []
    for row in rows:
        items.append(DBMetadata.gav2item(row))

    cursor.close()
    connection.close()
    return items


@app.get("/api/fileupgrade/{file_name}", response_model=List[ModelUpgrade])
def file_upgrade(
        file_name: str = Path(max_length=DBMetadata.MAXLEN_FILE_NAME),
        limit: Annotated[int, Query(le=DBMetadata.PAGE_SIZE_BIG)] = DBMetadata.PAGE_SIZE_BIG):

    """ Check if newer file exists for the given file name.
    Args:
        file_name (str): The name of the file to search for.
    Returns:
        ModelUpgrade: An instance of the GAV model containing the file information.
    Raises:
        HTTPException: If the file is not found in the database.
    """

    connection = DBMetadata.connect()
    cursor = connection.cursor()

    # Check if the file exists in the database
    cursor.execute(DBMetadata.SQL_GAV_SELECT_FILE_NAME, (file_name, ))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="File " + file_name + " not found")
    item = DBMetadata.gav2item(row)

    # Check for newer versions of the file
    cursor.execute(DBMetadata.SQL_GAV_UPGRADE, (item.group_id, item.artifact_id, item.version_seq, limit, ))
    rows = cursor.fetchall()
    if not rows:
        raise HTTPException(status_code=204, detail="No newer versions found for file " + file_name)

    items = []
    for row in rows:
        items.append(ModelUpgrade(
            artifact_version=row[0],
            last_modified=row[1]
        ))

    cursor.close()
    connection.close()
    return items


@app.get("/api/gavupgrade/{group_id}/{artifact_id}/{artifact_version}", response_model=List[ModelUpgrade])
def gav_upgrade(
        group_id: str = Path(max_length=DBMetadata.MAXLEN_GROUP_ID),
        artifact_id: str = Path(max_length=DBMetadata.MAXLEN_ARTIFACT_ID),
        artifact_version: str = Path(max_length=DBMetadata.MAXLEN_ARTIFACT_VERSION),
        limit: Annotated[int, Query(le=DBMetadata.PAGE_SIZE_BIG)] = DBMetadata.PAGE_SIZE_BIG):

    gav_str = f"{group_id}/{artifact_id}/{artifact_version}"
    connection = DBMetadata.connect()
    cursor = connection.cursor()

    # Check if the file exists in the database
    cursor.execute(DBMetadata.SQL_GAV_SELECT_GAV, (group_id, artifact_id, artifact_version, ))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="GAV " + gav_str + " not found")
    item = DBMetadata.gav2item(row)

    # Check for newer versions of the gav
    cursor.execute(DBMetadata.SQL_GAV_UPGRADE, (item.group_id, item.artifact_id, item.version_seq, limit, ))
    rows = cursor.fetchall()
    if not rows:
        raise HTTPException(status_code=204, detail="No newer versions found for GAV " + gav_str)

    items = []
    for row in rows:
        items.append(ModelUpgrade(
            artifact_version=row[0],
            last_modified=row[1]
        ))

    cursor.close()
    connection.close()
    return items
