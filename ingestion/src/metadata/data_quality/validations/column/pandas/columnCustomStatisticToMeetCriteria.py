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
Validator for column custom statistic to meet criteria test case
"""

import pandas as pd

from metadata.data_quality.validations.column.base.columnCustomStatisticToMeetCriteria import (
    BaseColumnCustomStatisticToMeetCriteriaValidator,
)
from metadata.data_quality.validations.mixins.pandas_validator_mixin import (
    PandasValidatorMixin,
)


class ColumnCustomStatisticToMeetCriteriaValidator(
    BaseColumnCustomStatisticToMeetCriteriaValidator, PandasValidatorMixin
):
    """
    Pandas validator for Column Custom Statistic To Meet Criteria
    """

    def _run_results(self) -> float:
        """
        Compute the specific statistic based on `statisticType`
        """
        statistic_type = self.get_test_case_param_value(
            self.test_case.parameterValues,
            "statisticType",
            str,
        )

        column_name = self.get_column_name(
            self.test_case.entityLink.__root__,
        )

        res = None
        count = 0
        sum_val = 0.0

        for chunk in self.runner:
            column_data = chunk[column_name]

            if statistic_type == "MAX":
                chunk_res = column_data.max()
                if not pd.isna(chunk_res):
                    res = chunk_res if res is None else max(res, chunk_res)
            elif statistic_type == "MIN":
                chunk_res = column_data.min()
                if not pd.isna(chunk_res):
                    res = chunk_res if res is None else min(res, chunk_res)
            elif statistic_type == "NULL_COUNT":
                res = (res or 0) + column_data.isnull().sum()
            elif statistic_type == "SUM":
                res = (res or 0) + column_data.sum()
            elif statistic_type in ["MEAN", "MEDIAN", "STDDEV"]:
                # For more complex statistics, fall back to concat for now
                # Or consider more complex running aggregations if needed
                df = pd.concat([c for c in self.runner])
                # We need to include the current chunk as we've already started iterating
                if len(df) == 0:
                    df = chunk
                else:
                    df = pd.concat([chunk, df])
                column_data = df[column_name]
                if statistic_type == "MEAN":
                    res = column_data.mean()
                elif statistic_type == "MEDIAN":
                    res = column_data.median()
                elif statistic_type == "STDDEV":
                    res = column_data.std()
                break
            else:
                raise ValueError(f"Unsupported statisticType: {statistic_type}")

        if pd.isna(res):
            raise ValueError(f"Pandas returned NaN for {statistic_type}")

        return float(res)
