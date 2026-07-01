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
Histogram Metric definition
"""

import math
from typing import TYPE_CHECKING, Any, Dict, Optional, Union, cast  # noqa: UP035

from sqlalchemy import and_, case, column, func
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from metadata.profiler.processor.runner import PandasRunner

from metadata.generated.schema.configuration.profilerConfiguration import MetricType
from metadata.profiler.metrics.composed.iqr import InterQuartileRange
from metadata.profiler.metrics.core import HybridMetric
from metadata.profiler.metrics.static.count import Count
from metadata.profiler.metrics.static.max import Max
from metadata.profiler.metrics.static.min import Min
from metadata.profiler.orm.functions.length import LenFn
from metadata.profiler.orm.registry import (
    is_concatenable,
    is_quantifiable,
    is_value_non_numeric,
)
from metadata.utils.helpers import format_large_string_numbers
from metadata.utils.logger import profiler_logger

logger = profiler_logger()


# pylint: disable=too-many-locals
class Histogram(HybridMetric):
    """
    AVG Metric

    Given a column, return the Histogram value.

    - For a quantifiable value, return the usual AVG
    - For a concatenable (str, text...) return the AVG length
    """

    schema_metric_type = MetricType.histogram

    @classmethod
    def name(cls):
        return MetricType.histogram.value

    @property
    def metric_type(self):
        return dict

    @staticmethod
    def _get_bin_width(iqr: float, row_count: float) -> Union[float, int]:  # noqa: UP007
        """
        Compute the bin width for the histogram using Freedman-Diaconis rule
        """
        if iqr == 0:
            return 1
        return 2 * iqr * row_count ** (-1 / 3)

    @staticmethod
    def _get_res(res: Dict[str, Any]):  # noqa: UP006
        # get the metric need for the freedman-diaconis rule
        res_iqr = res.get(InterQuartileRange.name())
        res_row_count = res.get(Count.name())
        res_min = res.get(Min.name())
        res_max = res.get(Max.name())

        if any(var is None for var in [res_row_count, res_min, res_max]):
            return None

        return (
            float(res_iqr) if res_iqr is not None else res_iqr,
            float(res_row_count),
            float(res_min),
            float(res_max),
        )  # Decimal to float

    @staticmethod
    def _format_bin_labels(lower_bin: Union[float, int], upper_bin: Optional[Union[float, int]] = None) -> str:  # noqa: UP007, UP045
        """format bin labels

        Args:
            lower_bin: lower bin
            upper_bin: upper bin. Defaults to None.

        Returns:
            str: formatted bin labels
        """
        if lower_bin is None:
            formatted_lower_bin = "null"
        else:
            formatted_lower_bin = format_large_string_numbers(lower_bin)
        if upper_bin is None:
            return f"{formatted_lower_bin} and up"
        return f"{formatted_lower_bin} to {format_large_string_numbers(upper_bin)}"

    def _get_bins(self, res_iqr: float, res_row_count: float, res_min: float, res_max: float):
        """Get the number of bins and the width of each bin.
        We'll first use the Freedman-Diaconis rule to compute the number of bins.
        If the number of bins is greater than 100, we'll fall back to Sturge's rule. If the number of bins
        is still greater than 100, we'll default to 100 bins.

        Args:
            res_iqr (float): IQR (first quartile - third quartile)
            res_row_count (float): number of rows
            res_min (float): minimum value
            res_max (float): maximum value
        """
        # preinint num_bins over 100.  On the normal path freedman-diaconis will readjust according to the algorithm
        # when we must fallback to sturges rule due to res_iqr being None, then num_bins will be readjusted.
        max_bin_count = 100
        if res_iqr is not None:
            # freedman-diaconis rule
            bin_width = self._get_bin_width(float(res_iqr), res_row_count)  # type: ignore
            num_bins = math.ceil((res_max - res_min) / bin_width)  # type: ignore
        # sturge's rule
        if res_iqr is None or num_bins > max_bin_count:
            num_bins = int(math.ceil(math.log2(res_row_count) + 1))  # noqa: RUF046
            bin_width = (res_max - res_min) / num_bins

        # fallback to max_bin_count bins
        if num_bins > max_bin_count:
            num_bins = max_bin_count
            bin_width = (res_max - res_min) / num_bins

        return num_bins, bin_width

    def fn(
        self,
        sample: Optional[type],  # noqa: UP045
        res: Dict[str, Any],  # noqa: UP006
        session: Optional[Session] = None,  # noqa: UP045
    ):
        """
        Build the histogram query.
        Disabled for security reasons to prevent exposure of raw values.
        """
        return None

    def df_fn(
        self,
        res: Dict[str, Any],  # noqa: UP006
        dfs: Optional["PandasRunner"] = None,
    ):
        """
        Dataframe function.
        Disabled for security reasons to prevent exposure of raw values.
        """
        return None
