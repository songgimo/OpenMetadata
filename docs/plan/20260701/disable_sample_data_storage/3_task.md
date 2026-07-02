# Phase 3: Implementation Task List

- [x] **Task 1: 일반 샘플 데이터(Sample Data) 적재 원천 차단**
  - [x] Action 1-1: `sampler_interface.py` 방어 로직 추가
  - [x] Action 1-2: `processor.py` 설정 오버라이드
  - [x] 테스트 코드 작성 및 검증 (`test_sampler_interface.py`, `test_sampler_override.py`)

- [x] **Task 2: 데이터 품질 테스트 실패 행(Failed Rows Sample) 수집 차단**
  - [x] Action 2-1: `failed_sample_validator_mixin.py` 쿼리 실행 스킵 로직 구현
  - [x] Action 2-2: `base_test_handler.py` 쿼리 실행 스킵 로직 구현
  - [x] 테스트 코드 작성 및 검증

- [ ] **Task 3: 프로파일러 지표(Profiler Metrics) 내 민감 셀 데이터 적재 차단**
  - [ ] Action 3-1: `min.py`, `max.py`, `median.py`, `histogram.py` 연산 스킵
  - [ ] Action 3-2: `core.py` 지표 목록 강제 필터링
  - [ ] 테스트 코드 작성 및 검증

- [x] **Task 4: 사용자 쿼리 히스토리(Query History) 원문 적재 완전 차단**
  - [x] Action 4-1: `query_parser.py` 쿼리 원문을 더미 텍스트(REDACTED)로 치환하는 로직 구현
  - [x] 테스트 코드 작성 및 검증

- [ ] **Task 5: 프론트엔드(React) UI에서 Sample Data 관련 노출 제거**
  - [ ] Action 5-1: React 컴포넌트 'Sample Data' 탭 및 기타 관련 요소 제거
  - [ ] UI 검증
