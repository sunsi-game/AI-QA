# 결함 주입·복원 시연

이 시연은 실제 게임에서 발견한 결함 사례가 아니라 **기존 테스트가 의도적 결함을 탐지하는지 확인하는 실험**이다. 외부 AI API는 호출하지 않는다.

## 실행

Unreal Editor를 닫고 해당 소스를 다른 작업에서 편집하지 않는 상태로 실행한다. 빌드와 테스트를 정상 기준·결함 주입·복원 후의 세 단계로 실행한다.

```powershell
cd 'C:\Users\KHY\Desktop\AI-QA\Tools\ChickenQA'
.\.venv\Scripts\python.exe scripts/run_fault_demo.py --project 'C:\Users\KHY\Desktop\AI-QA\ChickenFight.uproject'
```

1. `ChickenCharacter.cpp` 전체 바이트를 로컬 출력 폴더에 백업하고 SHA-256을 기록한다. 커밋하지 않은 기존 수정도 포함해 보존한다.
2. 정상 빌드에서 알려진 6개 테스트가 모두 통과하는지 확인한다.
3. `AddImpulse(CollisionImpulse, true)` 한 곳만 임시 제거한다. 테스트 코드와 통과 기준은 변경하지 않는다.
4. `CollisionPushAndCooldown`만 실패하고, 밀림 속도·위치 변화의 두 검사 메시지가 존재하는지 확인한다. 테스트 누락이나 컴파일 실패는 결함 탐지 성공으로 인정하지 않는다.
5. `finally`에서 원본 바이트를 복원하고 재빌드해 6개 통과를 확인한다.

완료 결과는 `output/fault_demo_<실행시각>/demo.md`에 생성한다. 각 단계에는 `execution.log`, `unreal_automation/index.json`, 고정된 게임 로그, 분석 보고서가 들어간다. `evidence.json`은 실행 종료 코드·테스트 상태·해시를 기록한다. `demo.md`에는 2분 시연 순서와 포트폴리오 설명문이 있다. 영상 자체를 녹화하는 도구는 아니다.

## 중단·복원

일반 예외는 원본 복원과 복원 빌드를 시도한다. 프로세스 강제 종료·전원 차단에서는 복원이 보장되지 않는다. 이 경우 해당 출력 폴더의 `ChickenCharacter.cpp.before`와 원본 경로·해시를 확인해 복원하고 `run_pipeline.ps1 -Project <경로> -RunTests -BuildEditor`로 재검증한다. 시연 중 외부 편집을 감지하면 그 편집을 덮어쓰지 않고 중단하므로 백업과 현재 파일을 비교해야 한다. 소스 복원만으로 DLL이 정상으로 돌아오는 것은 아니며 재빌드가 필요하다.

## 해석 범위

2026-11-24 Codex 실행 검증(미커밋): UE 5.8.2에서 정상 6개 성공, 의도적 충격 전달 누락 시 5개 성공·충돌 1개 실패, 복원 후 6개 성공을 확인했다. 실패 메시지는 밀림 속도와 상대 위치 변화 검사였다. 증거 폴더는 `output/fault_demo_20261124_063218_196811/`이며 원본과 복원 소스의 SHA-256이 일치한다.

임시 월드의 네이티브 캐릭터 충돌 응답 회귀 테스트에 대한 탐지 증거다. 자연스러운 접촉 검출, 실제 맵, Blueprint, 애니메이션, 네트워크 복제는 검증 범위 밖이다. 로그 경고 건수와 테스트 실패 수는 구분한다. 자세한 범위는 [자동 테스트 안내](STEP4_UNREAL_AUTOMATION.md)를 참고한다.
