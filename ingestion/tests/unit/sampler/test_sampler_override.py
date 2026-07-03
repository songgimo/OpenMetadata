import pytest
from unittest.mock import MagicMock, patch

from metadata.sampler.processor import SamplerProcessor

class TestSamplerProcessorOverride:
    @patch("metadata.sampler.processor.adapter_for_pipeline")
    @patch("metadata.sampler.processor.import_sampler_class")
    def test_zero_data_leakage_config_override(self, mock_import_sampler_class, mock_adapter_for_pipeline):
        # Create mock config
        mock_workflow_config = MagicMock()
        mock_workflow_config.source.type = "mysql"
        mock_workflow_config.source.sourceConfig.config.generateSampleData = True
        mock_workflow_config.source.sourceConfig.config.storeSampleData = True

        # Create mock metadata client
        mock_metadata = MagicMock()
        mock_profiler_settings = MagicMock()
        mock_profiler_settings.config_value.sampleDataConfig.storeSampleData = True
        mock_profiler_settings.config_value.sampleDataConfig.readSampleData = True
        mock_metadata.get_profiler_config_settings.return_value = mock_profiler_settings

        # Create mock profiler config class
        mock_profiler_config_class = MagicMock()

        mock_adapter = MagicMock()
        mock_adapter.service_type = MagicMock()
        mock_adapter.service_type.name = "DatabaseService"
        mock_adapter_for_pipeline.return_value = mock_adapter

        mock_import_sampler_class.return_value = MagicMock()

        # Initialize the processor
        processor = SamplerProcessor(
            config=mock_workflow_config, metadata=mock_metadata, profiler_config_class=mock_profiler_config_class
        )

        # Verify the overrides happened
        assert processor.source_config.generateSampleData is False
        assert processor.source_config.storeSampleData is False

        assert processor._sample_data_config.storeSampleData is False
        assert processor._sample_data_config.readSampleData is False
