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
Median Metric definition
"""
# pylint: disable=duplicate-code

from typing import TYPE_CHECKING, List, NamedTuple, Optional  # noqa: UP035

from sqlalchemy import column

from metadata.generated.schema.configuration.profilerConfiguration import MetricType
from metadata.profiler.metrics.core import StaticMetric, _label
from metadata.profiler.metrics.pandas_metric_protocol import PandasComputation
from metadata.profiler.metrics.window.percentille_mixin import PercentilMixin
from metadata.profiler.orm.functions.length import LenFn
from metadata.profiler.orm.registry import is_concatenable, is_quantifiable
from metadata.utils.logger import profiler_logger

logger = profiler_logger()

if TYPE_CHECKING:
    import numpy as np
    import pandas as pd

    from metadata.profiler.processor.runner import PandasRunner


class MedianAccumulator(NamedTuple):
    """Accumulator holding chunked NumPy arrays for fast median computation."""

    arrays: List["np.ndarray"]  # noqa: UP006
    count_value: int


class Median(StaticMetric, PercentilMixin):
    """
    Median Metric

    Given a column, return the Median value.

    - For a quantifiable value, return the usual Median
    """

    schema_metric_type = MetricType.median

    @classmethod
    def name(cls):
        return MetricType.median.value

    @classmethod
    def is_window_metric(cls):
        return True

    @property
    def metric_type(self):
        return float

    @_label
    def fn(self):
        """
        sqlalchemy function.
        Disabled for security reasons to prevent exposure of raw values.
        """
        return None

    def df_fn(self, dfs: Optional["PandasRunner"] = None):
        """
        Dataframe function.
        Disabled for security reasons to prevent exposure of raw values.
        """
        return None
