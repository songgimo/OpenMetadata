# 🎯 Phase 2: Architectural Blueprinting (@arch)

## 1. Domain & Interface Design
- **목표:** 한국 전화번호 형식 (하이픈 유무 모두 허용: `010-1234-5678`, `01012345678` 등)을 검사하는 `columnValuesToBeValidKoreanPhoneNumber` 룰의 코드 구조 설계.
- **정규식(Regex) 정의:** `^01[016789]-?\d{3,4}-?\d{4}$`
- **인터페이스 & 상속 구조 (KISS/YAGNI 준수):**
  - **Base:** `BaseColumnValuesToBeValidKoreanPhoneNumberValidator`를 구현하여 에러 계산 및 포맷팅 로직의 뼈대를 잡습니다.
  - **SQA (SQL 엔진):** `SQAValidatorMixin`과 `FailedSampleValidatorMixin`을 상속받아 구현. SQA의 경우 `Metrics.regexCount` 또는 `regexp_match` 필터를 활용하여 백엔드 DB단에서 정규식 처리를 위임합니다.
  - **Pandas (Datalake 엔진):** `PandasValidatorMixin`을 상속받아 구현. DataFrame의 `Series.astype(str).str.match()` 메서드를 이용하여 Datalake 파일들의 전화번호 형식을 고속으로 검증합니다.

## 2. Component Changes

### 2.1 JSON Schema
OpenMetadata 서버와 UI에 룰의 명세(이름, 지원 타입 등)를 제공합니다. 파라미터가 없으므로 가장 단순한 형태로 설계합니다.
#### [NEW] [columnValuesToBeValidKoreanPhoneNumber.json](file:///Users/gimo/projects/OpenMetadata/openmetadata-service/src/main/resources/json/data/tests/columnValuesToBeValidKoreanPhoneNumber.json)

### 2.2 Python Ingestion Handlers
실제 검증을 실행하는 파이썬 모듈들입니다. 기존의 `Regex` 룰 구조를 차용하되 비즈니스 로직(정규식)을 하드코딩하여 사용자의 입력을 제거합니다.

#### [NEW] [base/columnValuesToBeValidKoreanPhoneNumber.py](file:///Users/gimo/projects/OpenMetadata/ingestion/src/metadata/data_quality/validations/column/base/columnValuesToBeValidKoreanPhoneNumber.py)
#### [NEW] [sqlalchemy/columnValuesToBeValidKoreanPhoneNumber.py](file:///Users/gimo/projects/OpenMetadata/ingestion/src/metadata/data_quality/validations/column/sqlalchemy/columnValuesToBeValidKoreanPhoneNumber.py)
#### [NEW] [pandas/columnValuesToBeValidKoreanPhoneNumber.py](file:///Users/gimo/projects/OpenMetadata/ingestion/src/metadata/data_quality/validations/column/pandas/columnValuesToBeValidKoreanPhoneNumber.py)

---
> [!IMPORTANT]
> **@arch 피드백 요청:**
> 위와 같은 아키텍처(4개 파일 추가 및 정규식 하드코딩 패턴)로 설계를 확정하고, Phase 3(`@be`) 구현 단계로 넘어가도 될까요?
