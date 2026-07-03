import pytest
from unittest.mock import MagicMock, patch

from metadata.generated.schema.metadataIngestion.databaseServiceAutoClassificationPipeline import (
    DatabaseServiceAutoClassificationPipeline,
)
from metadata.sampler.processor import SamplerProcessor


class TestSamplerProcessorOverride:
    # 💡 더 이상 adapter_for_pipeline을 mock 할 필요가 없습니다!
    # 실제 Config 인스턴스를 주입하면 entity_adapters.py에 등록된 _BY_PIPELINE에서
    # 알아서 알맞은 어댑터를 찾아줍니다.
    @patch("metadata.sampler.processor.import_sampler_class")
    def test_zero_data_leakage_config_override(self, mock_import_sampler_class):
        # 1. 실제 Config 객체 생성 (adapter_for_pipeline이 타입 매핑을 정상적으로 할 수 있도록)
        mock_source_config = DatabaseServiceAutoClassificationPipeline(
            storeSampleData=True,
        )

        # Create mock workflow config
        mock_workflow_config = MagicMock()
        mock_workflow_config.source.type = "mysql"
        mock_workflow_config.source.sourceConfig.config = mock_source_config

        # Create mock metadata client
        mock_metadata = MagicMock()
        mock_profiler_settings = MagicMock()
        mock_profiler_settings.config_value.sampleDataConfig.storeSampleData = True
        mock_profiler_settings.config_value.sampleDataConfig.readSampleData = True
        mock_metadata.get_profiler_config_settings.return_value = mock_profiler_settings

        # Create mock profiler config class
        mock_profiler_config_class = MagicMock()

        mock_import_sampler_class.return_value = MagicMock()

        # Initialize the processor
        processor = SamplerProcessor(
            config=mock_workflow_config, metadata=mock_metadata, profiler_config_class=mock_profiler_config_class
        )

        # Verify the overrides happened
        # (참고: DatabaseServiceAutoClassificationPipeline에는 generateSampleData 필드가
        # 존재하지 않으므로 storeSampleData만 안전하게 검증합니다.)
        assert processor.source_config.storeSampleData is False

        assert processor._sample_data_config.storeSampleData is False
        assert processor._sample_data_config.readSampleData is False
