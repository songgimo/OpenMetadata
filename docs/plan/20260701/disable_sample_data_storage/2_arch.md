# Phase 2: Architectural Blueprinting (@arch)

## 🎯 설계 목표 (Goal)
오픈메타데이터 서버 내부에 어떠한 형태의 **실제 데이터(Sample Data 및 Column Value)** 도 저장되지 않도록 식별된 6가지 유출 경로를 완벽하게 차단(Defense-in-Depth)합니다.

---

## 🏗 구현 계획 (Tasks & Actions)

아래 명시된 Task들은 각각 Java 백엔드(Server-side 차단)와 Python 파이프라인(Client-side 차단) 양방향에서 이중으로 조치(Defense-in-Depth)됩니다.

### Task 1: 일반 샘플 데이터(Sample Data) 적재 원천 차단
`SELECT * LIMIT 50` 쿼리를 통해 무작위로 추출되는 테이블/토픽 샘플 데이터의 DB 적재를 방지합니다.

- **Action 1-1 (Java)**: `Table`, `Topic`, `Container`, `SearchIndex`, `File` Repository 수정
  - **대상 파일**: `openmetadata-service/src/main/java/org/openmetadata/service/jdbi3/*Repository.java`
  - **작업 내용**: `addSampleData()` 메서드 내의 `daoCollection.entityExtensionDAO().insert(...)` 구문을 삭제 또는 주석 처리합니다. 에러 없이 `200 OK`를 응답하도록 Bypass 처리합니다.
- **Action 1-2 (Python)**: Sampler 인터페이스 원천 차단
  - **대상 파일**: `ingestion/src/metadata/sampler/sampler_interface.py`
  - **작업 내용**: `generate_sample_data()` 메서드 최상단에 방어 로직을 추가하여 무거운 쿼리 실행 없이 즉시 `TableData(columns=[], rows=[])`를 반환하도록 수정합니다.

### Task 2: 데이터 품질 테스트 실패 행(Failed Rows Sample) 적재 차단
DQ 검증 실패 시 식별 목적으로 가져오는 실제 데이터 행의 적재를 방지합니다.

- **Action 2-1 (Java)**: TestCase Repository 수정
  - **대상 파일**: `openmetadata-service/src/main/java/org/openmetadata/service/jdbi3/TestCaseRepository.java`
  - **작업 내용**: `addFailedRowsSample()` 메서드 내의 DB `insert` 구문을 제거하여 데이터가 무시되도록 처리합니다.
- **Action 2-2 (Python)**: DQ Handler 원천 차단
  - **대상 파일**: `ingestion/src/metadata/data_quality/validations/base_test_handler.py`
  - **작업 내용**: `fetch_failed_rows_sample()` 메서드 내에서 실패 행을 가져오는 쿼리 실행부를 건너뛰고 빈 배열을 반환하도록 수정합니다.

### Task 3: 프로파일러 지표(Profiler Metrics) 내 셀 데이터 적재 차단
문자열/숫자 컬럼의 최솟값, 최댓값, 중앙값 및 빈출 단어 목록(Top-K)이 통계 지표라는 명목 하에 수집되는 것을 방지합니다.

- **Action 3-1 (Java)**: TableProfile 저장 시 필드 초기화 (Nullification)
  - **대상 파일**: `openmetadata-service/src/main/java/org/openmetadata/service/jdbi3/TableRepository.java`
  - **작업 내용**: `addTableProfile()` 등에서 전달된 `ColumnProfile`을 순회하며 `min`, `max`, `median`, `firstQuartile`, `thirdQuartile`, `cardinalityDistribution`, `histogram` 값을 명시적으로 `null`로 덮어씌운 뒤 DB에 저장합니다.
- **Action 3-2 (Python)**: 프로파일러 메트릭 연산 스킵
  - **대상 파일**: `ingestion/src/metadata/profiler/processor/profiler.py` (또는 관련 Metrics 연산부)
  - **작업 내용**: `Min`, `Max`, `Median`, `Cardinality` 연산 실행 로직 자체를 비활성화(`yield` 생략)하여 원천 DB로 관련 쿼리가 나가지 않도록 차단합니다.

### Task 4: 사용자 쿼리 히스토리(Query History) 내 리터럴 값 마스킹
Usage Ingestion 시 수집되는 원시 SQL 문(예: `WHERE email='test@test.com'`) 내부의 모든 상수값(리터럴)을 마스킹합니다.

- **Action 4-1 (Java)**: Query 엔티티 저장 전 마스킹
  - **대상 파일**: `openmetadata-service/src/main/java/org/openmetadata/service/jdbi3/QueryRepository.java`
  - **작업 내용**: `create()` / `createInternal()` 시 `query.getQuery()` 텍스트에 정규식을 적용하여 모든 리터럴 값을 `***`로 치환한 뒤 DB에 적재합니다.
- **Action 4-2 (Python)**: 파이프라인 전송 전 선제적 Parameterization
  - **대상 파일**: `ingestion/src/metadata/ingestion/source/database/query_parser.py` (또는 Usage 소스 관련 파일)
  - **작업 내용**: 파싱된 원시 SQL을 REST API로 쏘기 전에 쿼리 내 상수 파라미터를 `?`로 치환하는 방어 로직을 삽입합니다.

---

## User Review Required

> [!CAUTION]
> 위와 같이 명확한 Task와 Action 단계로 로직 수정안을 재구성하였습니다. 각 Task마다 백엔드 및 클라이언트 단의 역할을 나누어 두었으며, 이 전략에 동의하신다면 승인(Proceed)을 눌러 구현 지시를 내려 주십시오.

## Verification Plan
1. **Mock Data Test**: Query Ingestion 테스트 코드에 `SELECT * FROM tbl WHERE id=123` 쿼리를 주입했을 때, DB에는 `WHERE id=***` 로 적재되는지 검증.
2. **Profiler Test**: Profile Ingestion 후 `ColumnProfile` 엔티티 내에 `min`, `max`, `categories` 배열이 절대 존재하지 않는지 (Null 반환) Assert.
