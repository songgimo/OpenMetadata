# 오픈메타데이터(OpenMetadata) 데이터 적재 구조 분석 리포트

## 1. 사내 데이터가 OpenMetadata 내부의 데이터베이스에 적재가 되는가?
**네, 제한적인 형태(샘플, 프로파일링 지표, 쿼리 로그 등)로 실제 데이터의 일부가 오픈메타데이터 내부 데이터베이스(Postgres/MySQL)에 물리적으로 적재됩니다.**

오픈메타데이터는 기본적으로 '메타데이터'를 수집하는 카탈로그 솔루션이지만, 사용자의 편의와 데이터 품질(Data Quality) 프로파일링을 위해 실제 데이터를 일부 추출하여 자체 데이터베이스에 저장하는 기능을 제공합니다. 코드를 확인한 결과, 외부 저장소에 별도로 임시 저장하는 것이 아니라 **OpenMetadata의 백엔드 메타데이터 DB 자체에 Entity Extension(확장 데이터) 형태로 직접 저장**하고 있습니다.

---

## 2. 적재가 된다면 어느 레벨(어떤 데이터)까지 적재가 되는가?
오픈메타데이터가 수집하여 내부 DB에 적재하는 실제 사내 데이터의 범위는 크게 세 가지입니다:

### A. 테이블 샘플 데이터 (Sample Data)
- **개요:** 사용자가 데이터의 형태를 미리 볼 수 있도록 돕기 위해 각 테이블의 일부 행(Row) 데이터를 통째로 수집합니다.
- **수집 방식 및 건수 (Python Ingestion):**
  - 기본적으로 **테이블 당 50~100건(rows)** 의 데이터를 추출합니다. `sampleDataCount`라는 설정값이 존재하며, 코드상 기본값(Default)으로 50개(JSON Schema 기준) 혹은 100개(Python 설정 기준)가 설정되어 있습니다.
  - 무작위 추출(Randomized Sample) 또는 지정된 비율(Percentage)에 따라 쿼리를 날려(`fetch_sample_data` 함수 등) 수집합니다.
- **적재 방식 (Java Backend):**
  - 수집된 샘플 데이터는 백엔드 `TableRepository.java` 에서 `table.sampleData` 라는 Entity Extension을 통해 JSON 형태로 메타데이터 DB(PostgreSQL 또는 MySQL) 테이블에 영구 저장됩니다. (단, 설정에서 PII 마스킹 옵션이 존재하여 민감 정보를 별표 등으로 마스킹할 수 있습니다.)

### B. 프로파일링 지표 및 실패한 데이터 품질 검사 결과 (Failed Rows Sample)
- **개요:** 프로파일러(Profiler)를 실행할 때, 단순히 테이블의 통계치(Null 개수, 최대/최소값, 길이 등)뿐만 아니라 Data Quality 테스트가 실패한 경우 원인 파악을 위해 **실패한 원본 행 데이터(Failed Row Sample)** 를 수집합니다.
- **코드 확인:** `ingestion/src/metadata/ingestion/sink/metadata_rest.py`의 `ingest_failed_rows_sample` 함수 및 여러 곳에서 데이터 품질 테스트를 통과하지 못한 실제 로우 데이터(Row data)를 백엔드로 전송하여 적재하는 코드를 확인했습니다.

### C. 사용자 실행 쿼리 원문 (Query History)
- **개요:** 테이블 조회의 랭킹, 사용 빈도(Usage), Lineage(데이터 흐름)를 파악하기 위해 시스템에 남은 사용자의 쿼리 이력을 수집합니다.
- **문제 소지:** 이 과정에서 `query.json` 스키마 및 `QueryRepository.java`에 정의된 대로 **사용자가 실행했던 SQL 쿼리의 원문(Literal SQL string)** 이 그대로 적재됩니다. 쿼리 내부에 실제 비밀번호나 고객정보, 기밀 조건값 같은 중요 데이터가 평문으로 들어있을 경우, 이 역시 오픈메타데이터 내부 DB에 그대로 적재될 위험이 있습니다.

---

## 3. 요약 및 권고사항

사내 보안 규약상 **실제 데이터(Row Data 및 민감 정보)가 외부/서드파티 시스템 내부 DB에 저장되는 것이 금지**되어 있다면, 오픈메타데이터 도입 또는 설정 시 다음 기능들을 **반드시 비활성화(Disable) 혹은 제한**해야 합니다.

1. **샘플 데이터 수집 끄기 (Disable Sample Data):** Profiling Workflow를 구성할 때 `sampleDataCount`를 0으로 설정하거나, `Generate Sample Data` 옵션을 비활성화해야 합니다.
2. **PII 마스킹 필수 적용:** 불가피하게 프로파일링을 켜야한다면, OpenMetadata 내장 PII(개인식별정보) Tagging 및 Masking 기능을 최대한 보수적으로 적용하여 원문 노출을 방지해야 합니다.
3. **Query History 수집 시 평문 쿼리 주의:** Query Log 수집 Ingestion을 켜실 경우, 쿼리 조건절에 들어있는 중요 데이터가 함께 넘어올 수 있습니다. Query Log Ingestion을 아예 차단할 것인지 보안 검토가 필요합니다.
