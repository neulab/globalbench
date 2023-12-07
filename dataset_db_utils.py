from __future__ import annotations

from dataclasses import dataclass

import flask
from google.cloud import firestore

from explainaboard_web.models import DatasetMetadata, DatasetsReturn


@dataclass(frozen=True)
class DatasetPrivateMetadata:
    dataset_metadata: DatasetMetadata
    dataset_id: str
    gcs_base: str
    column_mapping: dict[str, str]


class DatasetDBUtils:
    _client: firestore.Client | None = None
    _collection: firestore.CollectionReference | None = None

    @staticmethod
    def get_collection() -> firestore.CollectionReference:
        if DatasetDBUtils._collection is None:
            project = flask.current_app.config["GCS_PROJECT"]
            DatasetDBUtils._client = firestore.Client(project=project)
            DatasetDBUtils._collection = DatasetDBUtils._client.collection(
                "datalab_datasets"
            )
        return DatasetDBUtils._collection

    @staticmethod
    def parse_metadata(doc: firestore.DocumentSnapshot) -> DatasetPrivateMetadata:
        if not doc.exists:
            raise ValueError(f"Parsing non-existant doc {doc.id}")
        doc_dict = doc.to_dict()
        sub_dataset = (
            None if doc_dict["sub_dataset"] == "NA" else doc_dict["sub_dataset"]
        )
        dataset_metadata = DatasetMetadata(
            dataset_name=doc_dict["dataset"],
            sub_dataset=sub_dataset,
            split={x: 0 for x in doc_dict["splits"]},
            tasks=doc_dict["tasks"],
            languages=doc_dict["languages"],
        )
        return DatasetPrivateMetadata(
            dataset_metadata=dataset_metadata,
            dataset_id=doc.id,
            gcs_base=doc_dict["gcs_base"],
            column_mapping=doc_dict["column_mapping"],
        )

    @staticmethod
    def find_dataset_by_id(dataset_id: str) -> DatasetPrivateMetadata | None:
        # Get the element from the collection
        doc = DatasetDBUtils.get_collection().document(dataset_id).get()
        return DatasetDBUtils.parse_metadata(doc) if doc.exists else None

    @staticmethod
    def find_dataset_by_name(
        dataset_name: str, sub_dataset: str | None
    ) -> DatasetPrivateMetadata | None:
        if sub_dataset is None:
            sub_dataset = "NA"
        dataset_id = f"{dataset_name}:{sub_dataset}"
        return DatasetDBUtils.find_dataset_by_id(dataset_id)

    @staticmethod
    def find_datasets(
        page: int = 0,
        page_size: int = 0,
        dataset_ids: list[str] | None = None,
        dataset_name: str | None = None,
        sub_dataset: str | None = None,
        task: str | None = None,
        no_limit: bool = False,
        strict_name_match: bool = False,
    ) -> DatasetsReturn:
        # TODO(gneubig): If necessary, this could probably be made significantly more
        # efficient by using a single compound query.
        collection = DatasetDBUtils.get_collection()
        # The set of ids, or None if we haven't filtered yet
        ids: set[str] | None = set(dataset_ids) if dataset_ids else None
        if dataset_name is not None:
            if strict_name_match:
                query = collection.where("dataset", "==", dataset_name)
            else:
                query = collection.where("dataset", ">=", dataset_name).where(
                    "dataset", "<", dataset_name + "\uf8ff"
                )
            new_ids = [doc.id for doc in query.stream()]
            ids = ids.intersection(new_ids) if ids else set(new_ids)
        if sub_dataset is not None:
            query = collection.where("sub_dataset", "==", sub_dataset)
            new_ids = [doc.id for doc in query.stream()]
            ids = ids.intersection(new_ids) if ids else set(new_ids)
        if task is not None:
            query = collection.where("tasks", "array_contains", task)
            new_ids = [doc.id for doc in query.stream()]
            ids = ids.intersection(new_ids) if ids else set(new_ids)
        sid, eid = page * page_size, (page + 1) * page_size
        if ids is None:
            query = collection
            ids_list = [doc.id for doc in query.stream()]
        else:
            ids_list = list(ids)
        total = len(ids_list)
        ids_list = ids_list if (no_limit or page_size == 0) else ids_list[sid:eid]
        examps = []
        # We have to do this in batches because of the length 30 limit on
        # "in" queries in firestore.
        for i in range(0, len(ids_list), 30):
            docs = collection.where("__name__", "in", ids_list[i : i + 30]).stream()
            for doc in docs:
                examps.append(DatasetDBUtils.parse_metadata(doc).dataset_metadata)

        return DatasetsReturn(examps, total)
