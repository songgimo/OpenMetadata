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

import traceback
from abc import abstractmethod
from typing import Optional

from metadata.data_quality.validations.base_test_handler import BaseTestValidator
from metadata.generated.schema.tests.basic import (
    TestCaseResult,
    TestCaseStatus,
    TestResultValue,
)


class BaseColumnCustomStatisticToMeetCriteriaValidator(BaseTestValidator):
    """
    Base validator for Column Custom Statistic To Meet Criteria
    """

    def _get_operator_and_thresholds(self):
        """
        Extract operator and thresholds from test case parameters
        """
        statistic_type = self.get_test_case_param_value(
            self.test_case.parameterValues,
            "statisticType",
            str,
        )
        operator = self.get_test_case_param_value(
            self.test_case.parameterValues,
            "operator",
            str,
        )
        threshold1 = self.get_test_case_param_value(
            self.test_case.parameterValues,
            "threshold1",
            float,
        )
        threshold2 = self.get_test_case_param_value(
            self.test_case.parameterValues,
            "threshold2",
            float,
            default=None,
        )

        return statistic_type, operator, threshold1, threshold2

    def evaluate_result(self, result_value: float) -> bool:
        """
        Evaluate if the calculated statistic meets the given criteria
        """
        statistic_type, operator, threshold1, threshold2 = self._get_operator_and_thresholds()

        if operator == "EQUALS":
            return result_value == threshold1
        elif operator == "GREATER_THAN":
            return result_value > threshold1
        elif operator == "LESS_THAN":
            return result_value < threshold1
        elif operator == "GREATER_THAN_OR_EQUALS":
            return result_value >= threshold1
        elif operator == "LESS_THAN_OR_EQUALS":
            return result_value <= threshold1
        elif operator == "BETWEEN":
            if threshold2 is None:
                raise ValueError("threshold2 must be provided for BETWEEN operator")
            return threshold1 <= result_value <= threshold2

        raise ValueError(f"Unsupported operator: {operator}")

    def run_validation(self) -> TestCaseResult:
        """Run validation for the given test case

        Returns:
            TestCaseResult:
        """
        try:
            res = self._run_results()

            statistic_type = self.get_test_case_param_value(
                self.test_case.parameterValues,
                "statisticType",
                str,
            )

            test_result_value = [
                TestResultValue(
                    name=statistic_type,
                    value=str(res),
                )
            ]

            status = TestCaseStatus.Success if self.evaluate_result(res) else TestCaseStatus.Failed

            return self.get_test_case_result_object(
                self.execution_date,
                status,
                f"Found {statistic_type}={res}.",
                test_result_value,
            )
        except Exception as exc:
            msg = f"Error computing {self.test_case.fullyQualifiedName.root}: {exc}"
            self.logger.debug(traceback.format_exc())
            self.logger.warning(msg)
            return self.get_test_case_result_object(
                self.execution_date,
                TestCaseStatus.Aborted,
                msg,
                [TestResultValue(name="statistic", value=None)],
            )

    @abstractmethod
    def _run_results(self) -> float:
        """
        Compute the statistic
        """
        raise NotImplementedError
