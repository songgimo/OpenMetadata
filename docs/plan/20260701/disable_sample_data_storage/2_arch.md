# Phase 2: Architectural Blueprinting (@arch)

## 🎯 설계 목표 (Goal)
오픈메타데이터 Python Ingestion 프레임워크 레벨에서 원천적으로 실제 데이터(Sample Data 및 Column Value, Failed Rows 등)가 쿼리 및 전송되지 않도록 강제 차단합니다. (Java 백엔드 코어 로직은 유지하되, 사용자 혼선 방지를 위해 프론트엔드 UI/UX에서 노출을 제거하는 하이브리드 접근 채택)

---

## 🏗 구현 계획 (Tasks & Actions)

아래 명시된 Task들은 Python 파이프라인(Client-side) 코드 레벨에서 조치되어 서버 측으로 데이터가 전송되는 것을 사전에 차단합니다.

### Task 1: 일반 샘플 데이터(Sample Data) 적재 원천 차단
`SELECT * LIMIT 50` 등 무작위로 추출되는 테이블/토픽 샘플 데이터가 수집되지 않도록 Ingestion 내부의 샘플링 로직을 강제 비활성화합니다.

- **Action 1-1 (Python)**: Sampler 인터페이스 원천 차단
  - **대상 파일**: `ingestion/src/metadata/sampler/sampler_interface.py`
  - **대상 파일과 함수가 하는 작업**: 이 파일은 여러 DB(MySQL, S3 등)에서 일관된 방식으로 데이터를 추출하기 위한 공통 인터페이스입니다. `generate_sample_data()` 함수는 프로파일링 분석(COUNT, SUM 등)과는 무관하며, 오직 UI의 'Sample Data' 탭에 띄워줄 무작위 원시 데이터(Raw Rows) 50개를 가져와 전송하는 역할만 수행합니다.
  - **작업 내용**: `generate_sample_data()` 메서드 최상단에 방어 로직을 추가하거나, 설정과 무관하게 즉시 `TableData(columns=[], rows=[])`를 반환하도록 하드코딩하여 샘플 쿼리 실행을 방지합니다.

- **Action 1-2 (Code-level Configuration Override)**: 설정 파싱 단계에서의 강제 덮어쓰기
  - **대상 파일**: `ingestion/src/metadata/sampler/processor.py` (Sampler 초기화 부) 또는 Pydantic 모델 영역
  - **대상 파일과 함수가 하는 작업**: 파이프라인 구동 시 백엔드 서버에 저장된 각종 설정값(예: Sample Data 생성 여부 등)을 내려받아 메모리에 로드하고 초기화하는 역할을 수행합니다.
  - **작업 내용**: 사용자가 UI에서 어떤 설정을 하든 무관하게 동작하도록, 파이프라인이 서버로부터 설정을 로드하는 단계에서 `storeSampleData`, `readSampleData`, `generateSampleData` 값을 강제로 `False`로 덮어씌웁니다(Override). 이를 통해 UI 설정 자체가 무력화됩니다.

### Task 2: 데이터 품질 테스트 실패 행(Failed Rows Sample) 수집 차단
DQ(Data Quality) 검증 실패 시 식별 목적으로 가져오는 실제 데이터 행의 조회를 방지합니다.

- **Action 2-1 (Python)**: DQ Handler 원천 차단
  - **대상 파일**: 
    - `ingestion/src/metadata/data_quality/validations/mixins/failed_sample_validator_mixin.py`
    - `ingestion/src/metadata/data_quality/validations/base_test_handler.py`
  - **대상 파일과 함수가 하는 작업**: 이 파일은 데이터 품질(Data Quality) 테스트가 실패했을 때 후처리를 담당하는 핵심 모듈입니다. 테스트가 실패하면 기본적으로 `fetch_failed_rows_sample()` 함수가 실행되어 "왜 실패했는지" 사용자가 확인할 수 있도록 실제 에러가 난 데이터 행(예: null이 들어가면 안 되는데 null이 들어간 row)들을 쿼리해서 가져옵니다. 
  - **작업 내용**: 이 후처리 로직(`result_with_failed_samples` 등) 내에서 실제 실패 행을 가져오는 쿼리 실행부를 강제로 건너뛰게 만들어, 테스트의 '성공/실패 여부'와 '실패 건수'는 정상적으로 기록되되 '실패한 실제 데이터 값'만 유출되지 않도록 막습니다.

### Task 3: 프로파일러 지표(Profiler Metrics) 내 민감 셀 데이터 적재 차단
문자열/숫자 컬럼의 최솟값, 최댓값, 중앙값 및 빈출 단어 목록(Top-K) 등 데이터 값이 직접적으로 노출될 수 있는 프로파일러 지표 연산을 비활성화합니다.

- **Action 3-1 (Python)**: 프로파일러 메트릭 연산 스킵
  - **대상 파일**:
    - `ingestion/src/metadata/profiler/metrics/static/min.py`
    - `ingestion/src/metadata/profiler/metrics/static/max.py`
    - `ingestion/src/metadata/profiler/metrics/window/median.py`
    - `ingestion/src/metadata/profiler/metrics/hybrid/histogram.py`
  - **대상 파일과 함수가 하는 작업**: 오픈메타데이터의 프로파일러는 '하나의 지표 당 하나의 파이썬 클래스' 구조를 가집니다. 위 파일들은 각각 최솟값, 최댓값, 중앙값 등 특정 지표를 추출하기 위해 원천 DB에 날릴 SQL 쿼리 구문(예: `SELECT MIN(col)`)을 동적으로 생성하는 역할을 전담합니다.
  - **작업 내용**: `Min`, `Max`, `Median`, `Cardinality` 연산 실행 로직 자체를 비활성화(`yield` 생략 또는 반환값 제외 처리)하여 원천 DB로 관련 쿼리가 나가지 않도록 차단합니다.

- **Action 3-2 (Code-level Configuration Override)**: 연산 지표 목록 강제 필터링
  - **대상 파일**: `ingestion/src/metadata/profiler/processor/core.py` (Profiler 초기화 부) 또는 `ProfilerProcessorConfig`
  - **대상 파일과 함수가 하는 작업**: 사용자가 UI에서 배포한 프로파일러 파이프라인의 전체 설정(어떤 테이블의 어떤 지표를 수집할지 명시된 배열)을 읽어들여 실제 연산 프로세서를 세팅하는 오케스트레이션 역할을 합니다.
  - **작업 내용**: 사용자가 UI의 고급 설정에서 `min`, `max`, `median` 등의 민감 지표를 명시적으로 선택하여 파이프라인을 배포하더라도, Python 파이프라인이 실행되기 직전에 `metrics` 배열을 가로채어 민감 지표들을 배열에서 강제로 삭제(Filter-out)합니다.

### Task 4: 사용자 쿼리 히스토리(Query History) 내 리터럴 값 마스킹
Usage Ingestion 시 수집되는 원시 SQL 문(예: `WHERE email='test@test.com'`) 내부의 모든 상수값(리터럴)을 서버로 전송하기 전에 마스킹 처리합니다.

- **Action 4-1 (Python)**: 파이프라인 전송 전 선제적 Parameterization (마스킹)
  - **대상 파일**: `ingestion/src/metadata/ingestion/processor/query_parser.py`
  - **대상 파일과 함수가 하는 작업**: Usage 파이프라인에서 원천 DB의 쿼리 로그(Query History)를 긁어온 뒤, 이 파일 내의 **`parse_sql_statement()`** 함수가 각 쿼리를 분석(Parse)하여 서버로 보낼 최종 페이로드(`ParsedData`)를 조립합니다.
  - **작업 내용**: `parse_sql_statement()` 함수가 `ParsedData` 객체를 생성하여 반환하기 직전에, 원본 쿼리 문자열(`record.query`)을 가로채어 내부의 상수 파라미터를 `?` 혹은 `***`로 치환하는 마스킹 로직을 삽입합니다.

### Task 5: 프론트엔드(React) UI에서 Sample Data 노출 제거
Python Ingestion에서 샘플 데이터를 원천 차단함에 따라 발생하는 UX 혼선을 방지하기 위해 프론트엔드 화면에서 해당 기능을 숨깁니다.
- **Action 5-1 (TypeScript/React)**: Sample Data 탭 제거
  - **대상 파일**: `openmetadata-ui/src/main/resources/ui/src/` 내부의 Entity 상세 페이지 컴포넌트
  - **작업 내용**: 테이블(Table) 및 토픽(Topic) 상세 페이지 UI에서 'Sample Data' 탭의 렌더링 로직을 제거하거나 비활성화하여 사용자가 접근할 수 없도록 조치합니다.

---

## User Review Required

> [!CAUTION]
> 사용자의 추가 요청에 따라, 백엔드 코어는 수정하지 않되 **Ingestion 단(Python)의 원천 차단**과 **프론트엔드 단(React)의 UI/UX 제거**를 병행하는 방향으로 설계를 최종 확정하였습니다.
> 이 설계로 진행하는 것에 동의하신다면 승인(Proceed)을 지시해 주십시오.

## 🧪 Verification & Test Plan (@qa & @be)

> [!IMPORTANT]
> **QA 엔지니어(@qa)**의 Zero-Trust 검증 원칙에 따라, DB 커넥터 종류나 UI 설정값에 관계없이 원천 데이터가 서버로 유출되지 않음을 증명해야 합니다.
> **백엔드 엔지니어(@be)**는 프로젝트 규칙에 따라 `unittest.TestCase` 상속을 피하고, 순수 `pytest`와 `mocker` 픽스처를 사용하여 테스트를 구현합니다.

### 1. 샘플 데이터 차단 방어 테스트 (Task 1)
- **대상**: `ingestion/tests/unit/sampler/test_sampler_override.py` (신규)
- **검증 내용**: 
  - `SamplerProcessor` 초기화 시 사용자의 UI 설정과 무관하게 `storeSampleData`, `generateSampleData` 설정이 강제로 `False`로 오버라이드되는지 확인.
  - `generate_sample_data()` 호출 시 실제 DB 커서(`execute`)가 호출되지 않으며 항상 `TableData(columns=[], rows=[])`를 반환하는지 검증.

### 2. 데이터 품질 테스트 실패 행 수집 차단 테스트 (Task 2)
- **대상**: `ingestion/tests/unit/data_quality/test_failed_sample_validator.py` (신규)
- **검증 내용**: 
  - DQ 테스트가 "Failed" 상태일 때 에러 로그 후처리를 담당하는 `BaseTestHandler`가 호출되더라도, 실제 데이터를 가져오는 내부 SQL 쿼리 로직이 호출 스킵(`assert_not_called`)됨을 검증.

### 3. 프로파일러 민감 지표 스킵 테스트 (Task 3)
- **대상**: `ingestion/tests/unit/profiler/test_profiler_metrics_blocker.py` (신규)
- **검증 내용**:
  - `ProfilerProcessorConfig` 생성 시 `min`, `max`, `median`과 같은 민감 지표가 메트릭 설정 배열에서 자동 필터링되는지 검증.
  - `Min`, `Max` 등 개별 메트릭 클래스의 쿼리 제너레이터 함수가 SQL문을 반환하지 않음을 확인.

### 4. 쿼리 히스토리 리터럴 마스킹 테스트 (Task 4)
- **대상**: `ingestion/tests/unit/test_query_parser.py` (기존 혹은 신규 작성)
- **검증 내용**:
  - 파라미터화된 테스트(`@pytest.mark.parametrize`)를 구성하여, `SELECT * FROM users WHERE email='ceo@company.com'` 등의 원시 쿼리가 주입되었을 때 리터럴 값이 `?` 또는 `***`로 안전하게 치환된 `ParsedData` 객체가 생성되는지 확인.

---

## 참고사항
- `workflow/ingestion.py`에 들어가보면 run() 함수에서 `processed_record`를 받아서  
  `if processed_record is not None and isinstance(step, (Processor, Stage, Sink)):`  
  condition을 만족하면 `step.run(processed_record)` 를 호출하여 다음 단계로 넘기는 구조이다.
- Sink가 되는 곳을 찾으려면 `ingestion/src/metadata/ingestion/sink/metadata_rest.py`에서 `ingestion.sink.metadata_rest.MetadataRestSink` 를 참고하자.

### ⚠️ 예상되는 Side Effects (Trade-offs)

데이터 보안(Zero Data Leakage)을 완벽히 달성하기 위해 플랫폼의 편의성과 관측성을 일부 희생함에 따라 발생하는 영향도입니다.

#### 1. Task 1: 샘플 데이터(Sample Data) 차단으로 인한 UX 혼선
- **현상**: OpenMetadata UI의 테이블 상세 페이지에서 'Sample Data' 탭이 항상 비어 있게 됩니다.
- **Side Effect**: 샘플 데이터가 노출되지 않기 때문에, 일반 사용자(Data Analyst 등)는 "Ingestion 파이프라인에 권한 오류가 났다"거나 "시스템이 고장 났다"고 오해할 수 있으며, 이로 인한 CS 문의가 증가할 수 있습니다.
- **대응 방향**: **(설계 변경 반영)** 사용자의 요청에 따라 프론트엔드 화면(UI/UX) 코드 수정을 포함하여 'Sample Data' 탭 자체를 제거(Task 5)하기로 결정하였으므로, 해당 사이드 이펙트(UX 혼선)는 원천적으로 해소됩니다.

#### 2. Task 2: DQ 실패 행(Failed Rows) 수집 차단으로 인한 트러블슈팅 마찰
- **현상**: Data Quality 테스트가 실패(Failed)했을 때, "어떤 데이터 때문에 실패했는지"(예: Null이 들어간 구체적인 Row의 내용)를 오픈메타데이터 UI 에러 로그에서 확인할 수 없습니다.
- **Side Effect**: 데이터 스튜어드나 데이터 엔지니어가 에러 원인을 파악하기 위해 OpenMetadata 화면만으로는 분석이 불가능합니다. **반드시 원천 DB에 직접 접속해 동일한 검증 쿼리를 수동으로 날려봐야** 하는 등 트러블슈팅과 디버깅에 드는 시간(Friction)이 크게 늘어납니다.

#### 3. Task 3: 프로파일러 민감 지표(Min/Max/Median) 스킵으로 인한 기능 제약
- **현상**: 컬럼의 최솟값, 최댓값, 중앙값 등의 지표가 파이프라인에서 수집되지 않아 대시보드에 노출되지 않습니다.
- **Side Effect**:
  1. **데이터 컨텍스트 파악의 어려움**: 날짜(Timestamp) 컬럼의 Min/Max 값이 없으면 "이 테이블에 언제부터 언제까지의 데이터가 있는지" 한눈에 파악하기 어렵습니다.
  2. **의존성 있는 DQ 테스트 연쇄 실패**: 기존에 등록된 DQ 테스트 중 "이 컬럼의 최댓값(MAX)이 100을 넘으면 알림"과 같이 **Profiler 메트릭 값 자체에 의존하는 Rule**이 있다면, 지표 연산이 스킵되면서 해당 DQ 테스트가 동작하지 않거나 에러 처리될 수 있습니다.

#### 4. Task 4: 쿼리 리터럴 마스킹으로 인한 파서 불안정성 (가장 위험한 리스크 ⚠️)
- **현상**: 수집된 Usage 쿼리 원문(예: `WHERE name='John'`)이 파싱 및 마스킹 과정을 거쳐 `WHERE name='?'` 등으로 강제 치환됩니다.
- **Side Effect**: 
  1. **Lineage(데이터 계보) 수집 누락 (Edge Case)**: 단순 정규식으로 마스킹할 경우, 중첩된 따옴표나 특정 DB 방언(Dialect)의 복잡한 문법에서 마스킹 로직 오류가 발생할 수 있습니다. 이로 인해 쿼리 파싱 엔진에서 에러가 날 경우, 단순한 사용량 집계 실패를 넘어 해당 쿼리가 만들어내는 **테이블 간의 Lineage 정보가 통째로 누락**될 위험이 존재합니다.
  2. **쿼리 재사용 불가**: 사용자가 Query History 탭에서 다른 사람의 쿼리를 복사해 실행하려 해도, 리터럴이 마스킹되어 있어 쿼리를 수동으로 복원해야 하는 불편함이 생깁니다.
- **대응 방향**: 파서 에러로 Lineage가 누락되는 것은 치명적이므로, 해당 구현 시 **다양한 사내 DB의 복잡한 실제 쿼리들을 대상으로 대규모 단위/통합 테스트(Stress Test)를 선행**하는 것이 필수적입니다.