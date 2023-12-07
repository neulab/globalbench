from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from bson.objectid import InvalidId, ObjectId
from pymongo.client_session import ClientSession
from pymongo.cursor import Cursor
from pymongo.results import DeleteResult, InsertManyResult, UpdateResult

from explainaboard_web.impl.db import get_db


@dataclass
class DBCollection:
    db_name: str
    collection_name: str


class DBUtils:
    # Names of DBs or collections
    SYSTEM_OUTPUT_COLLECTION_PREFIX = "system_outputs"
    DEV_SYSTEM_METADATA = DBCollection(
        db_name="metadata", collection_name="system_metadata_v012"
    )
    USER_METADATA = DBCollection(db_name="metadata", collection_name="user_metadata")
    BENCHMARK_METADATA = DBCollection(
        db_name="metadata", collection_name="benchmark_metadata"
    )
    BENCHMARK_FEATURED_LIST = DBCollection(
        db_name="metadata", collection_name="benchmark_featured_list"
    )

    @staticmethod
    def _convert_id(_id: str | ObjectId):
        try:
            return ObjectId(_id)
        # mongo accepts custom id
        except InvalidId:
            return _id

    @staticmethod
    def get_database(db_name: str):
        return get_db().cx[db_name]

    @staticmethod
    def get_client() -> ClientSession:
        return get_db().db.client

    @staticmethod
    def get_collection(collection: DBCollection, check_collection_exist=True):
        database = DBUtils.get_database(collection.db_name)
        if check_collection_exist:
            collection_names = database.list_collection_names()
            if collection.collection_name in collection_names:
                return database.get_collection(collection.collection_name)
            raise DBUtilsException(
                f"collection: {collection.collection_name} does not exist"
            )
        return database.get_collection(collection.collection_name)

    @staticmethod
    def drop(collection: DBCollection, check_collection_exist=False):
        """
        drop a collection
        :param check_collection_exist: if True and collection doesn't exist, raise
              exception
        """
        DBUtils.get_collection(collection, check_collection_exist).drop()

    @staticmethod
    def insert_one(
        collection: DBCollection,
        document: dict,
        check_collection_exist: bool = True,
        session: ClientSession = None,
    ) -> str:
        result = DBUtils.get_collection(collection, check_collection_exist).insert_one(
            document, session=session
        )
        return str(result.inserted_id)

    @staticmethod
    def insert_many(
        collection: DBCollection,
        documents: list[dict],
        check_collection_exist=True,
        session: ClientSession = None,
    ) -> InsertManyResult:
        return DBUtils.get_collection(collection, check_collection_exist).insert_many(
            documents, session=session
        )

    @staticmethod
    def find_one_by_id(
        collection: DBCollection,
        docid: str | ObjectId,
        projection: dict | None = None,
        session: ClientSession | None = None,
    ):
        """
        Find and return a document with the _id field
        Prameters:
          - id: value of _id
          - projection: include or exclude fields in the document
        """
        _id = DBUtils._convert_id(docid)
        return DBUtils.get_collection(collection).find_one(
            {"_id": _id}, projection, session=session
        )

    @staticmethod
    def update_one_by_id(
        collection: DBCollection,
        docid: str | ObjectId,
        field_to_value: dict,
        session: ClientSession | None = None,
    ) -> bool:
        """
        Update a document with the _id field
        Parameters:
          - id: value of _id
          - field_to_value: the new "field to value"(s) to be set in the document
        Returns: `True` if a single document has been updated
        """
        _id = DBUtils._convert_id(docid)
        result: UpdateResult = DBUtils.get_collection(collection).update_one(
            {"_id": _id}, {"$set": field_to_value}, session=session
        )
        if int(result.modified_count) == 1:
            return True
        return False

    @staticmethod
    def replace_one_by_id(collection: DBCollection, doc: dict):
        """
        Replace a document with the _id field
        Parameters:
          - doc: the document to replace
        """
        _id = DBUtils._convert_id(doc["_id"])
        return DBUtils.get_collection(collection).replace_one({"_id": _id}, doc)

    @staticmethod
    def delete_one_by_id(
        collection: DBCollection, docid: str | ObjectId, session: ClientSession = None
    ) -> bool:
        """
        Delete one document with the given ID
        Returns: `True` if a single document has been deleted
        """
        _id = DBUtils._convert_id(docid)
        result: DeleteResult = DBUtils.get_collection(collection).delete_one(
            {"_id": _id}, session=session
        )
        if int(result.deleted_count) == 1:
            return True
        return False

    @staticmethod
    def delete_many(
        collection: DBCollection, filt: dict, session: ClientSession = None
    ) -> int:
        """
        Delete one document with the given ID
        Returns: Number of deleted entries
        """
        result: DeleteResult = DBUtils.get_collection(collection).delete_many(
            filt, session=session
        )
        return int(result.deleted_count)

    @staticmethod
    def count(collection: DBCollection, filt: dict = None) -> int:
        if filt is None:
            filt = {}
        return DBUtils.get_collection(collection).count_documents(filt)

    @staticmethod
    def find(
        collection: DBCollection,
        filt: dict | None = None,
        sort: list | None = None,
        skip=0,
        limit: int = 10,
        projection: dict | None = None,
    ) -> tuple[Cursor, int]:
        """
        Find multiple documents
        TODO: error handling for find
        Parameters:
          - filter: filter parameters for find
          - sort: a list of sort parameters e.g. [('field1', pymongo.ASCENDING)]
          - skip: offset
          - limit: limit, pass in 0 to retrieve all documents (this is consistent with
                   the pyMongo API)
          - projection: include or exclude certain fields
          (https://docs.mongodb.com/manual/tutorial/project-fields-from-query-results/)
        Return:
          - a cursor that can be iterated over
          - a number that represents the total matching documents without considering
            skip/limit
        """
        if not filt:
            filt = {}
        cursor = DBUtils.get_collection(collection).find(filt, projection)
        if sort:
            cursor = cursor.sort(sort)
        cursor = cursor.skip(skip).limit(limit)
        total = DBUtils.count(collection, filt)
        return cursor, total

    CallbackRetType = TypeVar("CallbackRetType")

    @staticmethod
    def execute_transaction(
        callback: Callable[[ClientSession], CallbackRetType]
    ) -> CallbackRetType:
        """
        Executes `callback` in a transaction. Returns the return of callback. An
        exception is raised if failure.
        - Ref: https://pymongo.readthedocs.io/en/stable/api/pymongo/client_session.html
        """
        with DBUtils.get_client().start_session() as session:
            with session.start_transaction():
                return callback(session)


class DBUtilsException(Exception):
    """
    An exception type originated from `db_model`. This exception usually means that a
    developer is not using `db_model` properly. The details of the exception is usually
    not useful for the users.
      - `DBUtilsException` should not be used if a user requests for a system (with id)
      that does not exist. For this purpose, use `abort_with_error()` or define some
      other exception type.
    """

    def __init__(self, message: str) -> None:
        self.message = message
