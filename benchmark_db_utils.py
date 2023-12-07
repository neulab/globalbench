from __future__ import annotations

import datetime
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from pandas import Series

# note: the auth package itself is imported to allow mocking in tests to work
import explainaboard_web.impl.auth
from explainaboard_web.core.utils.cache_api import get_cache_dir, open_cached_file
from explainaboard_web.impl.constants import ALL_LANG, LING_WEIGHT, POP_WEIGHT
from explainaboard_web.impl.db_utils.dataset_db_utils import DatasetDBUtils
from explainaboard_web.impl.db_utils.db_utils import DBUtils
from explainaboard_web.impl.db_utils.system_db_utils import SystemDBUtils
from explainaboard_web.impl.db_utils.user_db_utils import UserDBUtils
from explainaboard_web.impl.internal_models.system_model import SystemModel
from explainaboard_web.impl.utils import abort_with_error_message
from explainaboard_web.models import (
    BenchmarkConfig,
    BenchmarkCreateProps,
    BenchmarkMetric,
    BenchmarkTableData,
    BenchmarkUpdateProps,
    BenchmarkViewConfig,
    DatasetMetadata,
)


@dataclass
class BenchmarkDBUtils:
    _SPECIAL_WEIGHT_MAPS = {"pop_weight": POP_WEIGHT, "ling_weight": LING_WEIGHT}
    _DEFAULT_SETS = {"all_lang": ALL_LANG}

    @staticmethod
    def _update_with_not_none_values(dest: dict, source: dict) -> None:
        for k, v in source.items():
            if v is not None:
                dest[k] = v

    @staticmethod
    def _convert_id_from_db(doc: dict) -> None:
        doc["id"] = doc["_id"]
        doc.pop("_id")

    @staticmethod
    def _convert_id_to_db(doc: dict) -> None:
        doc["_id"] = doc["id"]
        doc.pop("id")

    @staticmethod
    def find_configs(
        benchmark: str | None, parent: str | None, page: int = 0, page_size: int = 0
    ) -> list[BenchmarkConfig]:
        permissions_list = [{"is_private": False}]
        user = explainaboard_web.impl.auth.get_user()
        if user:
            permissions_list.append({"creator": user.id})
            permissions_list.append({"shared_users": user.email})

        and_list: list[dict[str, Any]] = [{"$or": permissions_list}]
        if benchmark is not None:
            and_list.append({"_id": benchmark})
        if parent is not None:
            and_list.append({"parent": parent})

        filt = {"$and": and_list}
        cursor, _ = DBUtils.find(
            DBUtils.BENCHMARK_METADATA, filt=filt, limit=page * page_size
        )

        config_dicts = []
        for config_dict in list(cursor):
            BenchmarkDBUtils._convert_id_from_db(config_dict)
            parent_id = config_dict.get("parent")
            if parent_id:
                # do not insert preferred username here as every single config will
                # issue a find instruction in DB, which creates a lot of overhead
                parent_config = BenchmarkDBUtils.find_config_by_id(
                    parent_id, include_preferred_username=False
                )
                parent_dict = parent_config.to_dict()
                BenchmarkDBUtils._update_with_not_none_values(parent_dict, config_dict)
                config_dict = parent_dict

            config_dicts.append(config_dict)

        # insert preferred usernames in batch to reduce overhead in DB
        UserDBUtils.insert_preferred_usernames(config_dicts)

        return [BenchmarkConfig.from_dict(config_dict) for config_dict in config_dicts]

    @staticmethod
    def find_config_by_id(
        benchmark_id: str, include_preferred_username: bool = True
    ) -> BenchmarkConfig:
        config_dict = DBUtils.find_one_by_id(DBUtils.BENCHMARK_METADATA, benchmark_id)
        if not config_dict:
            abort_with_error_message(404, f"benchmark id: {benchmark_id} not found")
        BenchmarkDBUtils._convert_id_from_db(config_dict)

        parent_id = config_dict.get("parent")
        if parent_id:
            parent_config = BenchmarkDBUtils.find_config_by_id(parent_id)
            parent_dict = parent_config.to_dict()
            BenchmarkDBUtils._update_with_not_none_values(parent_dict, config_dict)
            config_dict = parent_dict

        if include_preferred_username:
            UserDBUtils.insert_preferred_username(config_dict)
        else:
            config_dict["preferred_username"] = ""

        return BenchmarkConfig.from_dict(config_dict)

    @staticmethod
    def find_configs_featured() -> list[BenchmarkConfig]:
        cursor, _ = DBUtils.find(DBUtils.BENCHMARK_FEATURED_LIST, limit=1)
        cursor_list = list(cursor)
        if len(cursor_list) < 1:
            abort_with_error_message(500, "featured list not found")

        config_dicts = []
        for benchmark_id in cursor_list[0]["ids"]:
            config_dict = BenchmarkDBUtils.find_config_by_id(
                benchmark_id, include_preferred_username=False
            ).to_dict()
            config_dicts.append(config_dict)

        # insert preferred usernames in batch to reduce overhead in DB
        UserDBUtils.insert_preferred_usernames(config_dicts)

        return [BenchmarkConfig.from_dict(config_dict) for config_dict in config_dicts]

    @staticmethod
    def create_benchmark(props: BenchmarkCreateProps) -> BenchmarkConfig:
        props_dict = props.to_dict()

        user = explainaboard_web.impl.auth.get_user()
        if not user:
            abort_with_error_message(401, "login required")

        props_dict["creator"] = user.id
        props_dict["created_at"] = props_dict[
            "last_modified"
        ] = datetime.datetime.utcnow()

        BenchmarkDBUtils._convert_id_to_db(props_dict)
        DBUtils.insert_one(DBUtils.BENCHMARK_METADATA, props_dict)

        BenchmarkDBUtils._convert_id_from_db(props_dict)
        UserDBUtils.insert_preferred_username(props_dict)
        config = BenchmarkConfig.from_dict(props_dict)

        return config

    @staticmethod
    def update_benchmark_by_id(benchmark_id: str, props: BenchmarkUpdateProps) -> bool:
        # We discard all fields that have None values in update props.
        # This is important so that we don't overwrite existing fields in DB.
        props_dict = {k: v for k, v in props.to_dict().items() if v is not None}
        return DBUtils.update_one_by_id(
            DBUtils.BENCHMARK_METADATA, benchmark_id, props_dict
        )

    @staticmethod
    def delete_benchmark_by_id(benchmark_id: str):
        user = explainaboard_web.impl.auth.get_user()
        if not user:
            abort_with_error_message(401, "login required")
        config = BenchmarkDBUtils.find_config_by_id(benchmark_id)
        if config.creator != user.id:
            abort_with_error_message(403, "you can only delete your own benchmark")
        result = DBUtils.delete_one_by_id(DBUtils.BENCHMARK_METADATA, benchmark_id)
        if not result:
            raise RuntimeError(f"failed to delete benchmark {benchmark_id}")

    @staticmethod
    def load_sys_infos(config: BenchmarkConfig) -> list[SystemModel]:
        if config.system_query is not None:
            systems_return = SystemDBUtils.find_systems(
                dataset_name=config.system_query.get("dataset_name"),
                subdataset_name=config.system_query.get("sub_dataset"),
                task=config.system_query.get("task"),
                source_language=config.system_query.get("source_language"),
                target_language=config.system_query.get("target_language"),
                page=0,
                page_size=0,
            )
        elif config.datasets is not None:
            dataset_list = []
            for record in config.datasets:
                dataset_name = record["dataset_name"]
                subdataset_name = record.get("sub_dataset", None)
                dataset_split = record.get("dataset_split", "test")
                dataset_list.append((dataset_name, subdataset_name, dataset_split))
            systems_return = SystemDBUtils.find_systems(
                page=0, page_size=0, dataset_list=dataset_list
            )
        else:
            raise ValueError("system_query or datasets must be set by each benchmark")

        ret_systems = [x for x in systems_return.systems if x.dataset is not None]
        return ret_systems

    @staticmethod
    def generate_dataframe_from_sys_ids(config: BenchmarkConfig, system_ids: list[str]):
        return NotImplementedError

    @staticmethod
    def generate_dataframe_from_sys_infos(
        benchmark_config: BenchmarkConfig, systems: list[SystemModel]
    ):
        """
        Generate a leaderboard from a list of system_output_info:SysOutputInfo
        :param config: A benchmark config
        :param systems: A list of SystemModel
        :return: leaderboard:Leaderboard
        """
        # --- Get df entries

        # TODO(gneubig): this function is a bit hacky/fragile, using objects and dicts
        #                interchangeably due to OpenAPI deserialization being
        #                incomplete. Should be fixed.

        # --- Collect each dataset to be included in the benchmark
        # Get from configuration if it exists
        if benchmark_config.datasets:
            dataset_configs = [dict(x) for x in benchmark_config.datasets]
            dataset_to_id = {
                (
                    x["dataset_name"],
                    x.get("sub_dataset", None),
                    x.get("split", "test"),
                ): i
                for i, x in enumerate(dataset_configs)
            }
            systems = [
                x
                for x in systems
                if (x.dataset.dataset_name, x.dataset.sub_dataset, x.dataset.split)
                in dataset_to_id
            ]
        # Collect (and deduplicate) all datasets from system infos otherwise
        else:
            dataset_tuples = list(
                {
                    (x.dataset.dataset_name, x.dataset.sub_dataset, x.dataset.split)
                    for x in systems
                }
            )
            dataset_configs = [
                {"dataset_name": x, "sub_dataset": y, "split": z}
                for x, y, z in dataset_tuples
            ]
            dataset_to_id = {
                (
                    x["dataset_name"],
                    x.get("sub_dataset", None),
                    x.get("split", "test"),
                ): i
                for i, x in enumerate(dataset_configs)
            }

        dataset_metadatas: list[DatasetMetadata | None] = []
        for x in dataset_configs:
            dataset_return = DatasetDBUtils.find_datasets(
                dataset_name=x["dataset_name"],
                sub_dataset=x.get("sub_dataset", None),
                strict_name_match=True,
            )
            if dataset_return.total == 1:
                dataset_metadatas.append(dataset_return.datasets[0])
            else:
                logging.getLogger().warning(
                    f"Could not find dataset "
                    f'{x["dataset_name"]}, {x.get("sub_dataset", None)}'
                )
                dataset_metadatas.append(None)

        # --- Rearrange so we have each system's result over each dataset
        system_dataset_results: dict[str, list[SystemModel | None]] = {}
        for sys in systems:
            sys_name = sys.system_name
            if sys_name not in system_dataset_results:
                system_dataset_results[sys_name] = [None for _ in dataset_configs]
            dataset_id = dataset_to_id[
                (sys.dataset.dataset_name, sys.dataset.sub_dataset, sys.dataset.split)
            ]
            system_dataset_results[sys_name][dataset_id] = sys

        system_to_creator: dict[str, str] = {
            sys.system_name: sys.creator for sys in systems
        }

        # --- Set up the columns of the dataframe
        # Default dataset information columns
        df_input: dict[str, list] = {
            "system_name": [],
            "dataset_name": [],
            "sub_dataset": [],
            "dataset_split": [],
            "creator": [],
        }
        # Extra dataset information columns needed by datasets or operations
        exclude_keys = ["metrics"] + list(BenchmarkDBUtils._SPECIAL_WEIGHT_MAPS.keys())
        for dataset_config in dataset_configs:
            for dataset_key in dataset_config.keys():
                if not (dataset_key in df_input or dataset_key in exclude_keys):
                    df_input[dataset_key] = []
        for view in benchmark_config.views:
            for operation in view.operations:
                op_keys = [operation.get("weight")] + operation.get("group_by", [])
                for op_key in op_keys:
                    if op_key and not (op_key in df_input or op_key in exclude_keys):
                        df_input[op_key] = []

        # Columns regarding metric scores
        df_input["metric"] = []
        df_input["metric_weight"] = []
        df_input["score"] = []

        # --- Create the actual data
        for sys_name, systems in system_dataset_results.items():
            for dataset_config, dataset_metadata, sys in zip(
                dataset_configs, dataset_metadatas, systems
            ):
                if dataset_metadata is None:
                    continue
                column_dict = dict(dataset_config)
                column_dict["system_name"] = sys_name
                dataset_metrics: list[BenchmarkMetric] = dataset_config.get(
                    "metrics", benchmark_config.metrics
                )
                if dataset_metrics is None:
                    raise ValueError(
                        f"metrics must be specified either on a global or "
                        f'local level, but {dataset_config["dataset_name"]} -- '
                        f'{dataset_config["sub_dataset"]} -- '
                        f'{dataset_config["dataset_split"]} specified neither'
                    )
                for dataset_metric in dataset_metrics:
                    if type(dataset_metric) != dict:
                        dataset_metric = dataset_metric.to_dict()
                    column_dict["metric"] = dataset_metric["name"]
                    column_dict["metric_weight"] = dataset_metric.get(
                        "weight", 1.0 / len(dataset_metrics)
                    )
                    if sys is not None:
                        column_dict["creator"] = sys.creator
                        matching_results = []
                        for level, m in sys.results.items():
                            for k, v in m.items():
                                if k == dataset_metric["name"]:
                                    matching_results.append(v)
                        if len(matching_results) == 0:
                            performance = None
                        else:
                            performance = max(matching_results)
                        column_dict["score"] = (
                            performance
                            if performance
                            else (dataset_metric.get("default") or 0.0)
                        )
                    else:
                        column_dict["creator"] = system_to_creator[sys_name]
                        column_dict["score"] = dataset_metric.get("default") or 0.0
                    for df_key, df_arr in df_input.items():
                        if df_key in column_dict:
                            info = column_dict[df_key]
                        elif df_key == "sub_dataset":
                            info = None
                        elif df_key == "dataset_split":
                            info = "test"
                        elif df_key == "source_language":
                            if len(dataset_metadata.languages) == 0:
                                logging.getLogger().warning(
                                    f"No languages found for "
                                    f"{dataset_metadata.dataset_name}."
                                )
                                info = "eng"
                            else:
                                info = dataset_metadata.languages[0]
                        elif df_key == "target_language":
                            if len(dataset_metadata.languages) == 0:
                                logging.getLogger().warning(
                                    f"No languages found for "
                                    f"{dataset_metadata.dataset_name}."
                                )
                                info = "eng"
                            else:
                                info = dataset_metadata.languages[-1]
                        else:
                            logging.getLogger().warning(
                                f"No {df_key} found for "
                                f"{dataset_metadata.dataset_name}."
                            )
                            info = None
                        df_arr.append(info)
        return pd.DataFrame(df_input)

    @staticmethod
    def _gini(df: pd.DataFrame, numeric_only: bool) -> pd.Series:
        """Calculate the Gini coefficient of a numpy array."""
        # based on bottom eq:
        # http://www.statsdirect.com/help/generatedimages/equations/equation154.svg
        # from:
        # http://www.statsdirect.com/help/default.htm#nonparametric_methods/gini.htm
        # All values are treated equally, arrays must be 1d:
        # Get the score column for each task in df as a numpy array:
        if numeric_only:
            numerics = ["int16", "int32", "int64", "float16", "float32", "float64"]
            df = df.select_dtypes(include=numerics)
        data = []
        index = []
        for col in df.columns:
            array = df[col].to_numpy()
            x = np.sort(array)
            # Gini coefficient:
            total = 0
            for i, xi in enumerate(x[:-1], 1):
                total += np.sum(np.abs(xi - x[i:]))
            gini = total / (len(x) ** 2 * np.mean(x))
            # Round off to 5 decimal places:
            data.append(gini)
            index.append(col)

        return pd.Series(data=data, index=index)

    @staticmethod
    def aggregate_view(
        input_df: pd.DataFrame, view_spec: BenchmarkViewConfig, by_creator: bool
    ) -> pd.DataFrame:
        if input_df.empty:
            return input_df
        output_df = input_df.copy()
        for operation in view_spec.operations:
            # group_by info
            group_by: str | list[str] = operation.get("group_by", [])
            if isinstance(group_by, str):
                group_by = [group_by]
            if not operation.get("skip_group_system") and not by_creator:
                group_by = ["system_name"] + group_by
            if not operation.get("skip_group_system") and by_creator:
                group_by = ["creator"] + group_by
            # weight map info, including special ones indexed by a string
            weight_map: dict[str, float] | str | None = operation.get("weight_map")
            if isinstance(weight_map, str):
                weight_map = BenchmarkDBUtils._SPECIAL_WEIGHT_MAPS[weight_map]
            # Perform operations
            op = operation["op"]
            if op in {"mean", "sum", "max", "min", "gini"}:
                if len(group_by) > 0:
                    output_df = output_df.groupby(group_by)
                if op == "mean":
                    output_df = output_df.mean(numeric_only=True)
                elif op == "sum":
                    output_df = output_df.sum(numeric_only=True)
                elif op == "max":
                    output_df = output_df.max(numeric_only=True)
                elif op == "min":
                    output_df = output_df.min(numeric_only=True)
                elif op == "gini":
                    if len(group_by) > 0:
                        logging.getLogger().warning(
                            "Cannot group and gini, skipping grouping"
                        )
                    output_df = BenchmarkDBUtils._gini(output_df, numeric_only=True)
            elif op in {"multiply", "weighted_sum"}:
                weight = output_df[operation["weight"]]
                if weight_map:
                    weight = weight.map(weight_map)
                    if weight.isnull().values.any():
                        weight = weight.fillna(0)
                # Adjust the logit of the weight to make it more or less peaky
                weight_logit_multiplier = operation.get("weight_logit_multiplier")
                if weight_logit_multiplier is not None:
                    weight = np.exp(np.log(weight + 1e-8) * weight_logit_multiplier)
                    weight /= sum(weight)
                output_df["score"] = output_df["score"] * weight
                if op == "weighted_sum":
                    if len(group_by):
                        output_df = output_df.groupby(group_by).sum(numeric_only=True)
                    else:
                        output_df = output_df.sum(numeric_only=True)
            elif op in {"add_default"}:
                languages = [
                    lang
                    for lang in BenchmarkDBUtils._DEFAULT_SETS[operation["default_set"]]
                    if lang not in output_df[operation["column"]].values
                ]
                temp_df = pd.DataFrame(
                    [[lang, 0] for lang in languages],
                    columns=[operation["column"], "score"],
                )
                output_df = pd.concat([output_df, temp_df], axis=0, ignore_index=True)
                continue
            elif op in {"subtract"}:
                output_df["score"] = output_df["score"].apply(
                    lambda x: operation["num"] - x
                )
            else:
                raise ValueError(f"Unsupported operation {operation['op']} in spec.")
            if output_df.isnull().values.any():
                logging.getLogger().warning(
                    f"op {operation} resulted in NaN, replacing with 0"
                )
                output_df = output_df.fillna(0)
            # By default, when a pandas df is aggregated without groupby it becomes a
            # series and is represented as a column so the labels are in the row
            # indices. The below code compensates for this.
            if isinstance(output_df, Series):
                output_df = output_df.to_frame().transpose()
                if by_creator:
                    output_df["creator"] = "Overall"
                else:
                    output_df["system_name"] = "Overall"
            else:
                output_df.reset_index(inplace=True)

        # Remove all numerical columns other than score
        output_df = pd.concat(
            [output_df.select_dtypes(["object"]), output_df["score"]], axis=1
        )
        return output_df

    @staticmethod
    def generate_view_dataframes(
        config: BenchmarkConfig, orig_df: pd.DataFrame, by_creator
    ) -> list[tuple[str, pd.DataFrame]]:
        view_dfs = []
        for view_spec in config.views:
            view_dfs.append(
                (
                    view_spec.name,
                    BenchmarkDBUtils.aggregate_view(orig_df, view_spec, by_creator),
                )
            )
        view_dfs.append(("Original", orig_df))
        return view_dfs

    @staticmethod
    def _col_name(elem_names: list[str], df_entry):
        # TODO(gneubig): This string-based representation may not be ideal
        return "\n".join(
            ["score"]
            + [
                f"{elem}={df_entry[elem]}"
                for elem in elem_names
                if df_entry[elem] and type(df_entry[elem]) == str
            ]
        )

    @staticmethod
    def dataframe_to_table(
        view_name: str, input_df: pd.DataFrame, plot_dict: dict, col_name: str
    ) -> BenchmarkTableData:
        elem_names = [x for x in input_df.columns if x not in {"score", col_name}]
        system_idx = sorted(list(set(input_df[col_name])))
        row_col_names = [
            BenchmarkDBUtils._col_name(elem_names, x) for _, x in input_df.iterrows()
        ]
        column_idx = sorted(list(set(row_col_names)))
        # Terminate on empty data
        if len(system_idx) == 0 or len(column_idx) == 0:
            return BenchmarkTableData(
                name=view_name,
                system_names=[],
                column_names=[],
                scores=[[]],
                plot_y_values=[],
                plot_x_values=[],
            )
        scores = pd.DataFrame(
            {k: [0.0 for _ in system_idx] for k in column_idx}, index=system_idx
        )
        for (_, df_data), col_id in zip(input_df.iterrows(), row_col_names):
            row_id = df_data[col_name]
            val = df_data["score"]
            scores[col_id][row_id] = val
        scores = scores.sort_values(scores.columns[0], axis=0, ascending=False)
        return BenchmarkTableData(
            name=view_name,
            system_names=list(scores.index),
            column_names=list(scores.columns),
            scores=[[scores[j][i] for j in scores.columns] for i in scores.index],
            plot_y_values=[pt[1] for pt in plot_dict[view_name]],
            plot_x_values=[pt[0] for pt in plot_dict[view_name]],
        )

    @staticmethod
    def generate_plots(benchmark_id):
        config = BenchmarkDBUtils.find_config_by_id(benchmark_id)
        if config.type == "abstract":
            return {}
        plot_path = os.path.join(get_cache_dir(), benchmark_id + "_plot.json")
        plot_file = open_cached_file(
            benchmark_id + "_plot.json", datetime.timedelta(seconds=1)
        )
        if not plot_file:
            sys_infos = BenchmarkDBUtils.load_sys_infos(config)
            # Default trend is "increase",
            # meaning show the next date when there is improvement
            plot_dict = {
                k.name: (k.trend if k.trend else "increase") for k in config.views
            }
            plot_dict["Original"] = "original"
            json_dict = {k.name: [] for k in config.views}
            json_dict["Original"] = []
            json_dict["times"] = []
            unique_dates = sorted(list({x.created_at.date() for x in sys_infos}))

            for date in unique_dates:
                systems = [sys for sys in sys_infos if sys.created_at.date() <= date]
                orig_df = BenchmarkDBUtils.generate_dataframe_from_sys_infos(
                    config, systems
                )
                system_dfs = BenchmarkDBUtils.generate_view_dataframes(
                    config, orig_df, by_creator=False
                )
                for k, v in system_dfs:
                    if plot_dict[k] == "all":
                        json_dict[k].append((str(date), v.max()["score"]))
                    elif plot_dict[k] == "increase":
                        if len(json_dict[k]) == 0 or (
                            len(json_dict[k]) > 0
                            and json_dict[k][-1][1] < v.max()["score"]
                        ):
                            json_dict[k].append((str(date), v.max()["score"]))
            with open(plot_path, "w") as outfile:
                json.dump(json_dict, outfile)

        with open(plot_path) as f:
            plot_data = json.load(f)
        return plot_data
