> **데모 데이터 기반 보고서**: 실제 Unreal 테스트 결과가 아닙니다.

# ChickenQA 분석 리포트

- 생성 시간(UTC): 2026-11-17 06:44:25
- 로그: `example_crash.log`
- 확인한 줄: 8
- 로그 일부만 분석했는가: 아니요
- 참고: 탐지 건수는 로그의 패턴 매칭 건수이며 고유 오류 개수와 다릅니다.

## 1. 자동 집계 (로그에 존재하는 사실)

| 항목 | 건수 |
|---|---:|
| 크래시 관련 로그 | 1 |
| 오류 관련 로그 | 0 |
| 경고 로그 | 4 |
| 통과한 자동 테스트 | 0 |
| 실패한 자동 테스트 | 0 |

### 게임 이벤트 마커
- `MovementUpdate`: 1건
- `PushApply`: 1건
- `PushDispatch`: 1건
- `PushStop`: 1건

### 근거 로그 (라인 번호)
- L1 [warning] `LogTemp: Warning: [PushDispatch] BP_ChickenCharacter_C_3 <-> BP_ChickenCharacter_C_1 | TestPush=300.0`
- L2 [warning] `LogTemp: Warning: [PushApply] Target=BP_ChickenCharacter_C_3 | Impulse=X=-300.000 Y=0.000 Z=0.000 | Mode=3`
- L3 [warning] `LogChickenMovement: Warning: [MovementUpdate] Dt=0.016 Input=X=1.0 Y=0.0 Z=0.0 Fallen=0`
- L4 [warning] `LogTemp: Warning: [PushStop] Cooldown: Elapsed=0.000 / Limit=0.200`
- L7 [crash] `Unhandled Exception: EXCEPTION_ACCESS_VIOLATION reading address 0xffffffffffffffff`

## 2. Unreal Automation JSON 결과 (실제 테스트 수행 결과)

- 테스트 수: **2**
- 성공: 1 / 실패: 1 / 경고 동반: 0 / 미실행: 0 / 기타: 0

| 테스트 이름 | 상태 |
|---|---|
| ChickenQA.Collision.Direction | Success |
| ChickenQA.Knockdown.Threshold | Fail |

## 3. AI 분석 (검증이 필요한 가설)

AI 분석 미실행. `--ai` 옵션을 명시해야 API 요청이 발생합니다.

---
이 문서는 자동 생성된 보조 자료입니다. 최종 원인과 수정 효과는 개발자가 재현 테스트로 검증해야 합니다.
