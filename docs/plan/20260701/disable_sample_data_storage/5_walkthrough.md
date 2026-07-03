# Phase 5: Walkthrough - Task 1, 2, 4 (Zero Data Leakage 구현 상세)

## 개요
이 문서는 **Zero Data Leakage (민감 데이터 유출 원천 차단)** 정책의 일환으로 수행된 **Task 1, 2, 4**의 구현 내역을 상세히 설명하는 워크스루(Walkthrough)입니다.
최근 병합된 커밋들을 기반으로, 어떤 파일들에서 구체적으로 어떤 코드 줄이 변경, 추가, 혹은 삭제되었는지 단 하나도 누락 없이 모두 스캔하여 기록하며, **"각각의 세부 변경점들이 정확히 왜(Why) 수정되어야만 했는지"** 그 근거를 하나하나 명확히 밝힙니다.

---

## 🚀 수정된 전체 파일 및 로직 상세 (Task 1: 일반 샘플 데이터 차단)

### 1. `ingestion/src/metadata/sampler/processor.py`
**[파일 역할]**
파이프라인 구동 시 백엔드 서버에서 내려받은 샘플 데이터 관련 설정을 초기화하는 역할을 합니다.

**[모든 변경점 및 변경 이유]**
- `SamplerProcessor`의 `__init__` 메서드 내부에 `[Zero Data Leakage Policy]` 주석 추가
  - **(변경 이유)**: 후임 개발자들이 해당 강제 오버라이드 코드를 버그로 오인하여 지우는 것을 방지하고, 이것이 전사적인 강력한 보안 정책임을 즉각적으로 인지시키기 위함입니다.
- `self.source_config.generateSampleData` 속성이 존재할 경우 이를 강제로 `False`로 할당
  - **(변경 이유)**: UI의 일반 워크플로우 설정(Source Config)에서 넘어오는 샘플 데이터 추출 지시를 가장 먼저 가로채어 무력화하기 위함입니다.
- `self.source_config.storeSampleData` 속성이 존재할 경우 이를 강제로 `False`로 할당
  - **(변경 이유)**: 데이터를 추출하진 않더라도 샘플 데이터 저장 API를 어떻게든 호출하려는 후속 시도 자체를 원천 봉쇄하기 위함입니다.
- `self._sample_data_config` 내부의 `storeSampleData` 속성을 강제로 `False`로 할당
  - **(변경 이유)**: 프로파일러 전용 설정(Profiler Config)을 통해 넘어오는 독립적인 샘플 데이터 저장 지시까지 예외 없이 전부 무력화하기 위함입니다.
- `self._sample_data_config` 내부의 `readSampleData` 속성을 강제로 `False`로 할당
  - **(변경 이유)**: 백엔드에 이미 예전에 적재되어 있을지도 모르는 기존 샘플 데이터를 런타임에 읽어오려는 시도조차 차단하여, 파이프라인 내 메모리에 민감 데이터가 임시로라도 적재되는 것을 막기 위함입니다.

### 2. `ingestion/src/metadata/sampler/sampler_interface.py`
**[파일 역할]**
여러 소스 DB에서 원시 데이터를 50건씩 추출하는 실질적인 샘플링 핵심 로직을 담당합니다.

**[모든 변경점 및 변경 이유]**
- `generate_sample_data()` 메서드의 최상단에 `logger.info("Sample data generation is force-disabled by Zero Data Leakage policy.")` 로그 출력 추가
  - **(변경 이유)**: 로컬 실행이나 Airflow 환경에서 로그를 확인할 때, 샘플링이 에러 없이 안전하게 스킵되었음을 운영자가 명확히 인지하고 디버깅할 수 있도록 가시성(Observability)을 부여하기 위함입니다.
- 메서드 최상단에서 기존 로직 수행 전 즉시 `return TableData(rows=[], columns=[])`를 하드코딩하여 조기 종료(Early Return) 처리
  - **(변경 이유)**: `processor.py`의 설정 오버라이드를 뚫고 들어오는 예상치 못한 엣지 케이스나, 시스템 내부의 다른 모듈이 이 인터페이스를 직접 호출하는 최악의 상황까지 완벽하게 대비하기 위해, 실제 DB 커넥터를 열어 쿼리를 수행하는 구간으로 진입하기 전에 물리적으로 실행 흐름을 끊어버리는 이중 방어를 구축하기 위함입니다.

### 3. `ingestion/tests/unit/sampler/test_sampler_interface.py`
**[파일 역할]**
샘플 데이터가 설정에 따라 올바르게 추출/저장되는지 확인하는 단위 테스트 파일입니다.

**[모든 변경점 및 변경 이유]**
- 삭제된 기존 테스트 케이스 (총 7개: `test_both_disabled_returns_empty`, `test_read_only_fetches_but_does_not_store`, `test_store_enabled_fetches_data`, `test_both_enabled_fetches_data`, `test_none_config_defaults_to_both_enabled`, `test_store_enabled_with_storage_config_uploads`, `test_store_disabled_with_storage_config_does_not_upload`)
  - **(변경 이유)**: "특정 설정값이 주어지면 데이터를 잘 추출해온다"를 증명하던 기존 테스트들은 더 이상 유효하지 않은 옛날 정책의 산물이므로, 혼동을 막기 위해 과감히 제거했습니다.
- 신규 추가된 테스트 케이스 3개 (`always_returns_empty`, `with_none_config`, `never_called`)
  - **(변경 이유)**: 악의적이거나 극단적인 설정(`True` 할당, `None` 주입 등)을 억지로 주입하더라도 인터페이스가 절대 DB 추출 API를 호출하지 않으며 무조건 빈 배열을 반환한다는 사실을 격리된 테스트 환경에서 확고하게 100% 증명하기 위함입니다.

### 4. `ingestion/tests/unit/sampler/test_sampler_override.py`
**[파일 역할]**
새롭게 추가된 설정 오버라이드 로직을 전담하여 방어력을 테스트하는 신규 파일입니다.

**[모든 변경점 및 변경 이유]**
- `TestSamplerProcessorOverride` 클래스 및 신규 검증 메서드 신규 추가
  - **(변경 이유)**: `processor.py`에 추가된 "설정 강제 덮어쓰기(문지기 방어)" 로직이 의도대로 동작하여, UI에서 악의적인 수집 허용 값이 넘어왔을 때도 파이프라인의 4가지 주요 보안 설정이 모조리 `False`로 변환되는 현상을 철저히 검증하기 위함입니다.

---

## 🚀 수정된 전체 파일 및 로직 상세 (Task 2: 품질 테스트 실패 행 차단)

### 5. `ingestion/src/metadata/data_quality/validations/mixins/failed_sample_validator_mixin.py`
**[파일 역할]**
Data Quality 테스트 실패 시 원인 분석을 위해 오류가 난 실제 행(Failed Rows)을 수집하는 후처리 로직입니다.

**[모든 변경점 및 변경 이유]**
- `result_with_failed_samples()` 내부에 존재하던 `computePassedFailedRowCount` 플래그 및 `TestCaseStatus.Failed` 확인 `if` 조건문 완전히 삭제
  - **(변경 이유)**: 기존에는 해당 수집 플래그가 꺼져 있으면 스킵했지만, 이제는 플래그의 켜짐/꺼짐 여부조차 아예 신뢰하지 않고(Zero Trust) 무조건 스킵해야 하므로 분기문 자체를 걷어냈습니다.
- 실제 데이터를 추출하는 `self.fetch_failed_rows_sample()` 및 검사용 쿼리를 가져오는 `self.get_inspection_query()` 호출 `try-except` 블록 통째로 삭제
  - **(변경 이유)**: 해당 메서드들이 원천 DB에 접속해 실제 민감 데이터를 가져오는 실질적인 I/O 발생 지점이었기 때문에, 이 통로를 완전히 분쇄하기 위함입니다.
- 메서드 최상단에 `logger.info(...)` 로그 및 즉시 `return` 로직 추가
  - **(변경 이유)**: DB 접근 없이 즉시 해당 후처리를 종료시킴으로써 데이터 품질 테스트 실패로 인한 민감 정보 유출 경로를 완벽히 막아내기 위함입니다.

### 6. `ingestion/src/metadata/data_quality/validations/base_test_handler.py`
**[파일 역할]**
모든 DQ 테스트 핸들러들이 상속받는 최상위 추상 인터페이스 파일입니다.

**[모든 변경점 및 변경 이유]**
- `BaseTestValidator` 내부 `fetch_failed_rows_sample()` 메서드에 코드는 수정하지 않고 `# [Zero Data Leakage Policy] Base handler remains NO-OP to prevent data extraction` 주석 1줄을 명시적으로 추가
  - **(변경 이유)**: 최상위 인터페이스는 데이터를 추출하지 않는 빈 깡통(NO-OP)으로 두는 것이 원칙입니다. 하지만 향후 다른 개발자가 여기에 기본 추출 로직을 은연중에 구현해버리거나, 하위 핸들러를 새로 추가하면서 추출 로직을 멋대로 오버라이딩(Overriding)하는 휴먼 에러를 미연에 방지하기 위해 강한 아키텍처 가이드라인을 문서로 박아둔 것입니다.

### 7. `ingestion/tests/unit/data_quality/validations/test_failed_sample_mixin.py`
**[파일 역할]**
실패 행 추출 로직의 동작을 검증하던 단위 테스트 파일입니다.

**[모든 변경점 및 변경 이유]**
- 삭제된 기존 테스트 케이스 (총 6개: `test_samples_fetched_when_failed_and_flag_set`, `test_no_samples_when_status_is_success`, `test_no_samples_when_flag_is_false` 등)
  - **(변경 이유)**: "수집 설정이 켜져있을 때 오류 데이터를 잘 담아오는가?"를 전제로 짜여진 코드이므로, 전면 차단 정책과 정면으로 상충되어 제거했습니다.
- 신규 추가된 단위 테스트 (총 3개: `forces_no_samples`, `with_success_status`, `with_flag_false`)
  - **(변경 이유)**: 억지로 실패 상황을 조작하고 수집 플래그를 강제로 켜두더라도 `response` 객체에 데이터와 쿼리가 일절 담기지 않음(`None`)을 100% 증명하는 테스트 방어막을 구축하기 위함입니다.

---

## 🚀 수정된 전체 파일 및 로직 상세 (Task 4: 사용자 쿼리 원문 마스킹)

### 8. `ingestion/src/metadata/ingestion/processor/query_parser.py`
**[파일 역할]**
원천 DB에서 긁어온 쿼리 로그(Query History)를 구문 분석하고 저장용 객체로 조립하는 로직입니다.

**[모든 변경점 및 변경 이유]**
- `parse_sql_statement()` 내부 `ParsedData(...)` 생성 구문에서 기존의 `sql=record.query` 부분을 `sql="/* REDACTED FOR ZERO DATA LEAKAGE */"`로 완전히 교체(Replace)
  - **(변경 이유)**: 사용자가 실행한 쿼리 로그(`record.query`) 내부에는 사용자 이메일, 주민번호, 비밀번호 등 리터럴 형태의 실제 민감 데이터가 포함될 위험이 극도로 높습니다. 그러나 백엔드 전송 API 스키마 상 `sql` 필드가 필수(Required)이기 때문에 해당 필드를 아예 날려버리거나 `None`으로 전송할 수는 없습니다. 따라서 스키마 제약은 우회하면서도 데이터 유출은 막기 위해 쿼리 원문 텍스트 자체를 의미 없는 정적 더미 텍스트로 마스킹(Redaction)한 것입니다.

### 9. `ingestion/tests/unit/processor/test_query_parser.py`
**[파일 역할]**
쿼리 원문 마스킹 로직이 올바르게 동작하는지 검증하는 단위 테스트입니다.

**[모든 변경점 및 변경 이유]**
- `TestQueryParser` 클래스 및 신규 마스킹 검증 테스트(`test_parse_sql_statement_redacts_sql_query`) 작성
  - **(변경 이유)**: 이메일, 패스워드가 노골적으로 포함된 실제와 유사한 모의 쿼리를 주입했을 때, 쿼리가 파서를 통과한 후 원래 텍스트의 파편이 단 한 글자라도 새어나오지 않는지를 자동화된 테스트로 증명하기 위함입니다.
  - 리턴된 `sql` 필드가 정확히 더미 문자열과 동일한지 검증하는 것은 물론, 치환된 결과물 내부에 원래 쿼리의 조각(`"sensitive@email.com"`, `"secret_password"`, `"SELECT"`)이 절대 존재하지 않음을 `assert "..." not in parsed_data.sql` 구문들을 통해 다중으로 꼼꼼하게 검증했습니다.

---

## 💡 요약
Task 1, 2, 4를 아우르는 이번 페이즈를 통해, 오픈메타데이터 플랫폼이 외부 데이터베이스에 접속하여 **임의의 데이터 조각(Sample)** 이나 **오류 데이터(Failed Rows)** 를 직접 가져오는 경로, 그리고 사용자의 **작업 로그(Query History)** 를 통해 간접적으로 데이터가 유출되는 치명적인 경로가 모두 차단되었습니다.
결과적으로 어떠한 우회 시도나 설정 에러 상황에서도 **고객의 실제 데이터는 관측성 플랫폼 내부로 절대 유입되지 않는다**는 Zero Trust 원칙을 확립했습니다.
