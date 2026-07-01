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

from sqlalchemy import Column

from metadata.data_quality.validations.column.base.columnCustomStatisticToMeetCriteria import (
    BaseColumnCustomStatisticToMeetCriteriaValidator,
)
from metadata.data_quality.validations.mixins.sqa_validator_mixin import (
    SQAValidatorMixin,
)
from metadata.profiler.metrics.registry import Metrics

class ColumnCustomStatisticToMeetCriteriaValidator(
    BaseColumnCustomStatisticToMeetCriteriaValidator, SQAValidatorMixin
):
    """
    SQLAlchemy validator for Column Custom Statistic To Meet Criteria
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

        column = self.get_column_name(
            self.test_case.entityLink.__root__,
            self.runner.table.__table__.columns,
        )

        if statistic_type == "MAX":
            metric = Metrics.MAX.value
        elif statistic_type == "MIN":
            metric = Metrics.MIN.value
        elif statistic_type == "MEAN":
            metric = Metrics.MEAN.value
        elif statistic_type == "MEDIAN":
            metric = Metrics.MEDIAN.value
        elif statistic_type == "STDDEV":
            metric = Metrics.STDDEV.value
        elif statistic_type == "NULL_COUNT":
            metric = Metrics.NULL_COUNT.value
        elif statistic_type == "SUM":
            metric = Metrics.SUM.value
        else:
            raise ValueError(f"Unsupported statisticType: {statistic_type}")

        res = self.run_query_results(self.runner, metric, column)

        if res is None:
            raise ValueError(f"Query returned None for {statistic_type}")

        return float(res)
