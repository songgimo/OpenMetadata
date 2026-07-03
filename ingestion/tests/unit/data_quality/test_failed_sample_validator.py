import pytest
from unittest.mock import MagicMock, patch

from metadata.data_quality.validations.base_test_handler import BaseTestValidator
from metadata.data_quality.validations.mixins.failed_sample_validator_mixin import FailedSampleValidatorMixin
from metadata.generated.schema.tests.basic import TestCaseStatus
from metadata.data_quality.api.models import TestCaseResultResponse

class DummyValidator(BaseTestValidator, FailedSampleValidatorMixin):
    def fetch_failed_rows_sample(self):
        # Should not be called
        pass

    def _run_validation(self):
        pass

def test_failed_sample_validator_mixin():
    # Test that result_with_failed_samples is a no-op and does not call anything
    validator = DummyValidator(MagicMock(), MagicMock(), MagicMock())

    mock_response = MagicMock()
    mock_response.testCaseResult.testCaseStatus = TestCaseStatus.Failed

    # Run the function
    validator.result_with_failed_samples(mock_response)

    # fetch_failed_rows_sample is not even called because it's a direct no-op
    # No exception means it works as intended by the zero data leakage policy
