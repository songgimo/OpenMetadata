# Phase 2: Architectural Blueprinting (@arch)

## 🎯 설계 목표 (Goal)
오픈메타데이터 정책에 따라 어떤 데이터 엔티티(Table, Topic, Container, File, SearchIndex)의 샘플 데이터도 내부 DB에 저장되지 않도록 강제합니다. (사용자 선택: **옵션 B - 서버 코드 수정(Hard Block)**)

## 🏗 아키텍처 접근 방식
Dropwizard 백엔드의 각 데이터 자원(Repository) 클래스 내에 있는 `addSampleData()` 메서드 구현을 수정합니다.
Ingestion(Profiler) 파이프라인에서 샘플 데이터 삽입 요청(`PUT /api/v1/.../sampleData`)이 들어올 때, **파이프라인 동작을 중단(Crash)시키지 않으면서도 DB 적재를 막기 위해** 에러(Exception)를 던지는 대신 DB `insert` 로직을 생략(Bypass/Silent Drop)하고 기존 엔티티를 그대로 200 OK 상태로 반환하도록 설계합니다.

## User Review Required

> [!WARNING]
> **API 호환성 및 Silent Drop 정책**
> REST API에서 에러(400 Bad Request 등)를 반환하면 Python 프로파일러 전체가 실패할 위험이 있어, 서버가 "요청은 정상적으로 받았으나 저장하지 않는다(Silent Drop)"는 방식을 택했습니다.

## Proposed Changes

### 백엔드 Repository 컴포넌트 (Java)

샘플 데이터가 저장되는 모든 엔티티의 Repository에서 `daoCollection.entityExtensionDAO().insert(...)` 구문을 제거하거나 Bypass 처리합니다.

#### [MODIFY] [TableRepository.java](file:///Users/gimo/projects/OpenMetadata/openmetadata-service/src/main/java/org/openmetadata/service/jdbi3/TableRepository.java)
- `addSampleData(UUID tableId, TableData tableData)` 내부의 `insert` 부분 및 `table.withSampleData(tableData)` 바인딩 생략 (DB 적재 방지).
- 향후 식별을 위해 로거(LOG)로 "Sample data storage is disabled by policy" 경고 출력 추가.

#### [MODIFY] [TopicRepository.java](file:///Users/gimo/projects/OpenMetadata/openmetadata-service/src/main/java/org/openmetadata/service/jdbi3/TopicRepository.java)
- `addSampleData(UUID topicId, TopicSampleData sampleData)` 내부 로직 Bypass.

#### [MODIFY] [ContainerRepository.java](file:///Users/gimo/projects/OpenMetadata/openmetadata-service/src/main/java/org/openmetadata/service/jdbi3/ContainerRepository.java)
- `addSampleData(UUID containerId, TableData tableData)` 내부 로직 Bypass.

#### [MODIFY] [SearchIndexRepository.java](file:///Users/gimo/projects/OpenMetadata/openmetadata-service/src/main/java/org/openmetadata/service/jdbi3/SearchIndexRepository.java)
- `addSampleData(UUID searchIndexId, SearchIndexSampleData sampleData)` 내부 로직 Bypass.

#### [MODIFY] [FileRepository.java](file:///Users/gimo/projects/OpenMetadata/openmetadata-service/src/main/java/org/openmetadata/service/jdbi3/FileRepository.java)
- `addSampleData(UUID fileId, TableData tableData)` 내부 로직 Bypass.

---

## Verification Plan

### Automated Tests
- `mvn clean package -DskipTests` (빌드 확인)
- 관련 엔티티의 단위/통합 테스트에서 샘플 데이터 테스트가 깨지는지 확인. `testAddSampleData` 류의 테스트가 있다면, 의도된 `Bypass` 동작에 맞게 테스트 코드를 수정하거나 무시(Ignore) 처리 필요.

### Manual Verification
- 로컬 도커 환경에서 강제로 Sample Data Ingestion 파이프라인을 실행해보고, 로그에 Bypass 경고가 남으며 DB에 적재되지 않는지 점검.
