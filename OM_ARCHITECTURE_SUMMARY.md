# OpenMetadata Architecture & Development Summary

이 문서는 OpenMetadata의 핵심 아키텍처 원리와 커스터마이징 전략을 기록한 요약본입니다. 새로운 세션에서 이 문서를 참조하면 시스템의 깊은 맥락을 바로 파악할 수 있습니다.

## 1. 검색 엔진 (OpenSearch) 비동기 처리와 최종 일관성
OpenMetadata는 수십만 건의 메타데이터 수집 시 서버 과부하를 막기 위해 **비동기 이벤트 큐(Async Event Queue)** 방식을 사용합니다.

- **아키텍처 로직:** 
  1. Python 수집기가 API를 호출하면, Java 백엔드는 가벼운 MySQL에만 데이터를 즉시 저장(동기)하고 수집기에게 성공 응답(200 OK)을 반환합니다.
  2. 동시에 백엔드 내부의 **이벤트 버스(EventPubSub)**에 이벤트를 발행합니다.
  3. 백그라운드 리스너(`ChangeEventHandler`, `SearchIndexHandler`)가 큐에서 이벤트를 꺼내어 비동기적으로 OpenSearch의 Bulk API를 호출해 인덱싱합니다.
- **최종 일관성(Eventual Consistency):** 이 비동기 처리 시차 때문에, 데이터 수집 직후 검색창에서 바로 검색이 안 될 수 있습니다. 하지만 다이렉트 URL로 접속하면 MySQL을 직접 조회하므로 최신 데이터를 즉시 볼 수 있습니다.

## 2. 이벤트 오프셋 폴링과 실패 복구 (At-Least-Once Delivery)
비동기 큐의 이벤트 처리는 철저하게 **순차적 오프셋(Offset, 책갈피) 폴링** 방식을 따릅니다.
- OpenSearch 서버가 다운되어 인덱싱에 실패(`RetriableException`)하면, 오프셋(책갈피)을 업데이트하지 않습니다.
- 다음 스케줄러가 돌 때 동일한 오프셋부터 다시 데이터를 가져오므로 **무한 자동 재시도**가 이루어집니다.
- 이를 통해 1. 데이터 유실 방지, 2. 데이터 순서 보장(Event Sourcing / CDC 패턴)으로 검색 엔진의 상태가 원본 DB의 역사와 100% 일치하도록 보장합니다.

## 3. 검색 스코어링 (Index Scoring) 커스터마이징
검색 결과 랭킹이나 로직을 커스터마이징하려면 Java 백엔드 소스코드를 직접 수정해야 합니다.
- **위치:** `ElasticQueryBuilder.java`, `OpenSearchQueryBuilder.java`
- **단순 가중치(Boost) 조절:** `name^10.0`, `tags^2.0` 등 필드별 상수 가중치(Boost)를 조작합니다.
- **복잡한 랭킹 (Function Score):** 특정 태그나 조회수(`usageSummary`)가 높은 테이블을 상단에 올리려면, `functionScore` 로직 내부에 `field_value_factor`나 `script_score` 코드를 추가하고 빌드(`mvn clean package`)해야 합니다.

## 4. 데이터 품질 (Data Quality) 아키텍처
DQ 검사는 4단계의 핑퐁 게임으로 구현됩니다.
1. **정의 (Brain):** 유저가 UI에서 JSON Schema 기반으로 룰을 정의하면 MySQL에 저장됩니다.
2. **명령 (Muscle):** Airflow 파이썬 수집기가 API를 통해 이 명세서를 다운받습니다.
3. **실행:** 파이썬의 `SQLAlchemy`를 이용해 실제 대상 DB(Snowflake 등)에서 돌아갈 쿼리를 동적으로 생성하고 채점합니다.
4. **거버넌스:** 결과를 Java API로 보내고, 실패(Failed) 시 자동으로 **인시던트(Incident)** 티켓을 생성합니다.

### 💡 커스텀 검증 룰 추가하기
- **1단계 (JSON):** `openmetadata-spec/.../tests/` 에 JSON Schema 추가 후 `make generate` 실행.
- **2단계 (SQL용):** `ingestion/src/metadata/data_quality/validations/.../sqlalchemy/` 에 로직 작성.
- **3단계 (Pandas용):** `ingestion/src/metadata/data_quality/validations/.../pandas/` 에 로직 작성.

## 5. 인시던트 관리와 Webhook 연동
- OpenMetadata는 자체 UI(Data Observability)에 훌륭한 인시던트(버그 티켓) 관리 보드를 내장하고 있습니다.
- **Slack 연동:** 코딩 없이 UI의 `Event Subscriptions`에서 Webhook URL만 넣으면 끝입니다.
- **다수 채널 동적 라우팅 (Custom Webhook):** 채널이 수십 개라면, OpenMetadata UI에는 **딱 1개의 사내 자체 파이썬 서버 Webhook**만 등록합니다. 이 파이썬 서버가 JSON 페이로드에서 `Owner`를 파싱하여 알맞은 슬랙 채널이나 Jira로 동적 라우팅하도록 구축하는 것이 엔터프라이즈 정석입니다.

## 6. 외부 Airflow 연동 (Decoupled Ingestion)
수천 개의 데이터 품질 검사를 돌리면 단일 내장 Airflow 서버는 뻗어버립니다.
- 사내의 거대한 외부 Airflow(MWAA, Composer)에 `openmetadata-ingestion` 패키지를 설치하여 무거운 연산(SQL 쿼리)을 100% 이관합니다.
- 외부 Airflow는 연산만 하고 가벼운 JSON 결과만 Java API로 쏩니다.
- 커스텀 로직(Custom Validation)을 추가했다면 코드를 두 번 짤 필요 없이, 내가 수정한 파이썬 패키지를 외부 Airflow 워커 노드들에 설치(`pip install`)해 주기만 하면 됩니다.

## 7. Python Ingestion 폴더 구조 이해하기 (`ingestion/src/metadata/`)
완벽한 **ETL (추출 ➡️ 가공 ➡️ 적재)** 뼈대로 이루어져 있습니다.
- `ingestion/source/`: (Extract) 각종 DB 커넥터들 모음. 커스텀 커넥터를 짤 때 여기만 보면 됨.
- `ingestion/processor/`: (Transform) 중간 데이터 필터링 및 가공.
- `ingestion/sink/`: (Load) 완성된 데이터를 백엔드 API로 쏴주는 목적지.
- `ingestion/api/`: 웹 서버 API가 아니라, 모든 커넥터가 따라야 하는 '파이썬 프레임워크 인터페이스(규칙/Base Classes)' 모음. (예: `models.Either`)
- `data_quality/`: 품질 검사 엔진.
- `profiler/`: Min/Max/Null 등 데이터 통계 산출.
- `pii/`: 개인정보 자동 탐지.
