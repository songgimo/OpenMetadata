# Phase 2: Architectural Blueprinting (@arch)

## 🎯 3차 심층 전수조사 결과 및 설계 목표 (Goal)
사용자님의 지시에 따라, 오픈메타데이터가 "외부 시스템에서 실제 데이터를 땡겨와 내부에 적재"하는 모든 로직에 대해 3차례의 추가 심층 분석을 진행했습니다. 그 결과, 기존에 발견된 3가지(Sampler, DQ Failed Rows, Profiler Min/Max) 외에도 **실제 데이터(문자열, 셀 값, 쿼리 리터럴 등)가 메타데이터 DB로 유입되는 3가지 치명적 경로를 추가로 발견**했습니다.

총 **6가지 유출 경로**를 완벽하게 차단하도록 아키텍처를 재설계했습니다.

### 🔍 [기존 3개 경로]
1. **Sample Data (일반 샘플 데이터)**: `SELECT * LIMIT 50` 
2. **Failed Rows Sample (DQ 실패 행)**: `SELECT * WHERE ...`
3. **Profiler Metrics (Min/Max/Median)**: 컬럼의 실제 최댓값/최솟값 셀 데이터 적재.

### 🚨 [추가 발견된 3개 치명적 유출 경로]
4. **Profiler: Cardinality Distribution (Top-K 카테고리 데이터 유출)**
   - `columnProfile` 스키마 내에 `cardinalityDistribution.categories`가 존재합니다. 이는 해당 컬럼에서 가장 자주 등장하는 값(Top-K)의 문자열 데이터(예: 이메일 도메인, 이름, 특정 식별자 등)를 그대로 배열 형태로 가져와 DB에 적재합니다.
5. **Query History (원시 쿼리 내 리터럴 값 유출)**
   - Usage/Query Ingestion 파이프라인은 Snowflake, Redshift 등의 `query_history`를 긁어옵니다. 이때 사용자가 실행한 원시 SQL(예: `WHERE email='test@example.com'`)이 `Query` 엔티티의 `query` 필드에 텍스트 그대로 저장되어, 실제 검색 조건으로 쓰인 민감 데이터가 무방비로 적재됩니다.
6. **Data Quality: Inspection Query 및 결과값 유출**
   - 데이터 품질 테스트(특히 `tableCustomSQLQuery` 등 커스텀 쿼리) 수행 시, 테스트를 위해 DB에 날린 원시 쿼리(Inspection Query)와 그 쿼리의 반환 결과값(`testResultValue`)이 문자열 형태로 그대로 저장됩니다.

---

## 🏗 아키텍처 접근 방식 (Defense-in-Depth V2)

### 1. Java 백엔드 (Server-side Silent Drop & Nullification)
- **Repository `addSampleData`, `addFailedRowsSample`**: 데이터 DB `insert` 구문을 완벽히 생략 (기존 계획 유지).
- **TableProfile 적재 방어**: `TableRepository.addTableProfile` 과정에서 전달된 `ColumnProfile` 내의 다음 필드를 강제로 `null` 처리합니다.
  - `min`, `max`, `median`, `firstQuartile`, `thirdQuartile`
  - `cardinalityDistribution` 및 `histogram`
- **Query 엔티티 적재 방어**: 쿼리 텍스트 로깅이 불가피하다면 정규식 기반 리터럴 마스킹(`'...'` -> `'***'`)을 백엔드 단에 강제 적용하거나, 보안 수준에 따라 Query 엔티티 적재 자체를 Bypass 처리.

### 2. Python Ingestion (Client-side Query Bypass & Masking)
- **샘플 및 실패 행 원천 쿼리 차단**: `generate_sample_data()` 및 `fetch_failed_rows_sample()`에서 무조건 빈 배열 반환. (기존 계획 유지)
- **프로파일러 스펙 제한**: `metadata/profiler/metrics/` 로직에서 `Cardinality`, `Min`, `Max` 등 문자열 데이터를 반환할 수 있는 연산의 실행 자체를 비활성화(Skip)하여 DB에 과부하를 주지 않음.
- **Query Ingestion 마스킹 (필수)**: 
  - 원천 DB로부터 가져온 원시 쿼리 문자열을 OM 서버로 전송하기 전, 쿼리 내의 **모든 상수(리터럴) 값을 `?` 또는 `***`로 치환(Parameterization)** 하도록 강제합니다.

---

## User Review Required

> [!CAUTION]
> **Query History 파이프라인 제약**
> 추가 발견된 5번(Query 원시 리터럴 유출)을 차단하기 위해, SQL 쿼리 문자열의 모든 상수를 마스킹(`***`)하는 강력한 전처리를 적용할 계획입니다. 이렇게 되면 UI에서 리니지는 볼 수 있으나 사용자가 쳤던 정확한 WHERE 조건값은 확인할 수 없게 됩니다. 보안 상 필수 조치입니다.

## Verification Plan
1. **Mock Data Test**: Query Ingestion 테스트 코드에 `SELECT * FROM tbl WHERE id=123` 쿼리를 주입했을 때, DB에는 `WHERE id=***` 로 적재되는지 검증.
2. **Profiler Test**: Profile Ingestion 후 `ColumnProfile` 엔티티 내에 `min`, `max`, `categories` 배열이 절대 존재하지 않는지 (Null 반환) Assert.
