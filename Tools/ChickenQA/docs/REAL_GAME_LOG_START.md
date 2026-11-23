# ChickenQA v0.2 — 실제 Unreal 게임 로그 분석 실습

## 1. 게임 실행

Unreal Engine에서 실제 테스트하려는 `ChickenFight.uproject`를 열어 PIE 또는 Standalone으로 게임을 실행하고 캐릭터 이동, 충돌, 넘어짐 등을 직접 재현합니다. 실행 로그가 `Saved/Logs/*.log`에 기록되었는지 확인합니다. 크래시 로그는 `Saved/Crashes`에 별도로 남을 수도 있습니다.

## 2. 분석 실행 (현재 환경 기준)

```powershell
cd "C:\Users\KHY\Desktop\AI-QA\Tools\ChickenQA"
.\scripts\analyze_game_logs.ps1 -Project "C:\Users\KHY\Desktop\AI-QA\ChickenFight.uproject" -OpenReport
```

`.ps1` 실행이 차단되면 정책을 바꾸지 말고 아래 Python 직접 호출을 사용합니다.

```powershell
.\.venv\Scripts\python.exe -m chickenqa --project "C:\Users\KHY\Desktop\AI-QA\ChickenFight.uproject" --out output\real-game
```

## 3. 리포트 해석

- 크래시/오류/경고 숫자는 **패턴에 맞은 로그 라인 수**이며 사건 수가 아닙니다.
- `source_name`, `log_selection.relative_log_path`, `modified_utc`로 실제 분석한 로그가 맞는지 확인합니다.
- `crash_contexts`는 크래시 관련 줄 직후 최대 10줄을 보관합니다. 전체 호출 스택이나 정확한 원인을 보장하지 않습니다.
- `events`는 `LogChicken*:` 분류 또는 `[PushApply]` 등의 마커가 있는 경우에만 집계됩니다. 게임에서 로그를 찍지 않는 동작은 볼 수 없습니다.
- `test_passed=0`, `test_failed=0`은 테스트 미실행/결과 부재일 수 있습니다. 게임 통과 판정으로 쓰면 안 됩니다.

## 4. 실패 시 확인

- `.uproject 파일을 찾을 수 없습니다`: 경로가 틀렸으니 `.uproject`의 정확한 위치를 다시 지정합니다.
- `프로젝트 로그를 찾지 못했습니다`: 게임을 실행하고 `Saved/Logs`를 확인합니다. 로그가 다른 폴더에 있으면 `--log "실제로그경로"`를 사용합니다.
- `Python venv is missing`: `python -m venv .venv`로 가상환경을 다시 생성합니다.
- `Cannot open/ReadOnly`: Unreal Editor 종료 후 다시 실행하거나 로그를 다른 이름으로 복사해 `--log`로 지정합니다.
- `GEMINI_API_KEY`: `--ai` 없이 먼저 실행합니다. AI는 후속 단계에서 켤 수 있습니다.

## 5. 다음 단계

실제 분석 결과 `report.md`를 검토한 뒤, 게임의 `LogChickenCollision`, `LogChickenMovement`, `PostPush` 등 실제 출력 형식에 맞춰 충돌·이동·넘어짐 검증 규칙을 추가하고 자동 테스트로 발전시킵니다.
