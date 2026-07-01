# 🎯 Phase 2: Architectural Blueprinting - Application Batch Processing (v2) (@arch)

## 1. Domain & Interface Design
- **목표:** DB 서버(Oracle, MySQL 등)에 부하를 주지 않고, Application(OpenMetadata 파이썬 워커) 쪽으로 "모든 데이터(100%)"를 안전하게 가져와서 정규식 연산을 수행하는 구조로 변경.
- **핵심 기술:** SQLAlchemy의 **Server-Side Cursor (`yield_per`)** 및 **Batch Fetching**. 
- **설계 변경점:** 기존 `SQAValidatorMixin`이 사용하던 DB Push-down(SQL `REGEXP`) 방식을 버리고, `SELECT target_column FROM table` 쿼리를 던지되 메모리 초과(OOM)를 방지하기 위해 1만 건씩(Chunk) 잘라서 파이썬으로 가져와 검증하는 로직으로 전면 교체합니다.

## 2. Component Changes

### [MODIFY] [sqlalchemy/columnValuesToBeValidKoreanPhoneNumber.py](file:///Users/gimo/projects/OpenMetadata/ingestion/src/metadata/data_quality/validations/column/sqlalchemy/columnValuesToBeValidKoreanPhoneNumber.py)
기존 DB 엔진에게 위임하던 로직을 완전히 제거하고, 아래의 흐름을 갖는 코드로 덮어씁니다.

1. **Python 정규식 컴파일:** `pattern = re.compile(self.REGEX_PATTERN)`을 통해 파이썬 메모리에서 고속 연산 준비.
2. **Chunking 쿼리 생성:** `select(column).execution_options(yield_per=10000)` (또는 커넥터 특성에 맞는 fetchmany 옵션 적용)
3. **Application 연산 루프:**
   ```python
   total_count = 0
   valid_count = 0
   for row in self.runner.session.execute(stmt):
       val = row[0]
       if val is not None:
           total_count += 1
           if pattern.match(str(val)):
               valid_count += 1
   ```
4. **결과 리턴:** 파이썬 메모리에서 계산된 최종 `total_count`, `valid_count`를 리턴.

---
> [!WARNING]
> **@arch 피드백 요청:**
> 위 방식(Application Memory Chunking)을 사용하면 DB의 CPU는 보호할 수 있지만, 천만 개의 데이터가 네트워크를 타고 Application 서버로 넘어야 하므로 **네트워크 I/O 병목 및 검증 속도 저하(수 분~수십 분 소요)**는 불가피합니다. 비즈니스 요구사항에 따라 이 Trade-off를 감수하고 위 아키텍처(Application 내부 연산)대로 구현을 수정할까요?
