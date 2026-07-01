#  Copyright 2025 Collate
#  Licensed under the Collate Community License, Version 1.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#  https://github.com/open-metadata/OpenMetadata/blob/main/ingestion/LICENSE
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""
Max Metric definition
"""

from functools import partial
from typing import TYPE_CHECKING, Callable, Optional  # noqa: UP035

from sqlalchemy import TIME, column
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import GenericFunction

from metadata.generated.schema.configuration.profilerConfiguration import MetricType
from metadata.generated.schema.entity.data.table import DataType, Table
from metadata.profiler.adaptors.nosql_adaptor import NoSQLAdaptor
from metadata.profiler.metrics.core import CACHE, StaticMetric, T, _label
from metadata.profiler.metrics.pandas_metric_protocol import PandasComputation
from metadata.profiler.orm.functions.length import LenFn
from metadata.profiler.orm.registry import (
    FLOAT_SET,
    Dialects,
    is_concatenable,
    is_date_time,
    is_quantifiable,
)
from metadata.utils.logger import profiler_logger

# pylint: disable=duplicate-code

if TYPE_CHECKING:
    import pandas as pd

    from metadata.profiler.processor.runner import PandasRunner

logger = profiler_logger()


class MaxFn(GenericFunction):
    name = __qualname__
    inherit_cache = CACHE


@compiles(MaxFn)
def _(element, compiler, **kw):
    col = compiler.process(element.clauses, **kw)
    return f"MAX({col})"


@compiles(MaxFn, Dialects.Trino)
def _(element, compiler, **kw):
    col = compiler.process(element.clauses, **kw)
    first_clause = element.clauses.clauses[0]
    # Check if the first clause is an instance of LenFn and its type is not in FLOAT_SET
    # or if the type of the first clause is date time
    if (
        isinstance(first_clause, LenFn) and type(first_clause.clauses.clauses[0].type) not in FLOAT_SET
    ) or is_date_time(first_clause.type):
        # If the condition is true, return the maximum value of the column
        return f"MAX({col})"
    return f"IF(is_nan(MAX({col})), NULL, MAX({col}))"


@compiles(MaxFn, Dialects.MySQL)
@compiles(MaxFn, Dialects.MariaDB)
def _(element, compiler, **kw):
    col = compiler.process(element.clauses, **kw)
    col_type = element.clauses.clauses[0].type
    if isinstance(col_type, TIME):
        # Mysql Sqlalchemy returns timedelta which is not supported pydantic type
        # hence we profile the time by modifying it in seconds
        return f"MAX(TIME_TO_SEC({col}))"
    return f"MAX({col})"


class Max(StaticMetric):
    """
    MAX Metric

    Given a column, return the max value.
    """

    schema_metric_type = MetricType.max

    @classmethod
    def name(cls):
        return MetricType.max.value

    @_label
    def fn(self):
        """
        sqlalchemy function.
        Disabled for security reasons to prevent exposure of raw values.
        """
        return None

    def df_fn(self, dfs: Optional["PandasRunner"] = None):
        """
        pandas function.
        Disabled for security reasons to prevent exposure of raw values.
        """
        return None

    def nosql_fn(self, adaptor: NoSQLAdaptor) -> Callable[[Table], Optional[T]]:  # noqa: UP045
        """
        nosql function.
        Disabled for security reasons to prevent exposure of raw values.
        """
        return lambda table: None
