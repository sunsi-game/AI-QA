## v0.3.1 — 실제 로그 신선도/모델 혼잡 점검

- `--project <...> --list-logs`: Saved/Logs 및 Saved/Crashes 최신 수정순 파일 15개 확인 (API 호출 없음)
- 자동 선택한 로그가 24시간 이상 오래되면 터미널과 보고서에 경고
- `https://...?UserID=...` 형태의 URL query 파라미터를 로컬 보고서와 AI payload에서 마스킹(완전하지 않으므로 수동 검토 필수)
- Gemini 503 오류 시 원인 안내. SDK의 자동 재시도를 사용하며, **모델을 자동 변경하지 않음** (비용·권한 및 결과 재현성 고려)

```powershell
.\.venv\Scripts\python.exe -m chickenqa --project "C:\Users\KHY\Desktop\AI-QA\ChickenFight.uproject" --list-logs
.\.venv\Scripts\python.exe -m chickenqa --project "C:\Users\KHY\Desktop\AI-QA\ChickenFight.uproject" --out output\fresh-check
```

503이 지속되면 검토한 `ai_payload_preview.json`을 유지한 채 `--model`로 다른 **현재 사용 가능한** 모델을 명시해 재실행할 수 있습니다. `--ai-payload` 사용 시 원본 로그가 변경되지 않아야 합니다. 변경되었으면 `--prepare-ai`부터 다시 실행하세요.

---

# ChickenQA v0.3.1 — Unreal 게임 로그 자동 분석 + Gemini AI QA

Unreal Engine `ChickenFight.uproject`에서 만들어진 **실제 `.log` 파일**을 읽어, 로그에 존재하는 사실과 AI가 제안한 검증 가설을 구분해 Markdown 보고서로 생성합니다.

> 현재 범위: 저장된 로그를 읽기 전용으로 분석하며, v0.4 파이프라인은 Editor 빌드와 기본 설정 테스트 3개 실행 및 JSON 결과 보고서를 연결합니다. 2026-11-24 UE 5.8.2에서 세 테스트 통과와 보고서 생성을 확인했습니다. 임시 월드에서 이동 입력·충돌 응답·넘어짐 경계를 검사하는 게임 동작 테스트 3개도 포함합니다. 맵과 멀티플레이 전체 검증은 아닙니다. Gemini 분석 성공 여부는 이 로컬 테스트 검증과 별개입니다.

## 새 버전에서 추가한 기능

- `--prepare-ai`: 네트워크 호출 없이 **Gemini에 전송할 JSON**을 `ai_payload_preview.json`으로 출력
- `--ai --ai-payload <파일>`: **검토하고 필요하면 내용을 삭제한 JSON만** Gemini API에 전송
- AI 분석 실패 시 로컬 보고서와 `ai_status: failed` 보존, 프로그램 종료 코드 2
- 실제 관찰된 크래시 패턴, `LogChicken*` 비유한(NaN/Inf) 값, PushApply/PostPush 관찰 차이 등에 대한 진단 신호 표시
- 검토 파일의 로그명/크기/수정 시각이 현재 로그와 달라지면 AI 전송을 차단
- PowerShell 5.1에서 한글 인코딩 파싱 에러를 피하도록 스크립트는 ASCII로 유지

## 설치

```powershell
cd "C:\Users\KHY\Desktop\AI-QA\Tools\ChickenQA"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

기존 v0.2의 `.venv`가 정상이라면 재설치 필요 없이 라이브러리 업데이트만 해도 됩니다.

## 1. 게임 플레이 후 로컬 분석 (API 호출 없음)

```powershell
.\.venv\Scripts\python.exe -m chickenqa `
  --project "C:\Users\KHY\Desktop\AI-QA\ChickenFight.uproject" `
  --out output\game-local
```

실제 원본 게임을 사용할 경우 프로젝트만 바꿉니다: `C:\Users\KHY\Desktop\DKU\DKUEndGame\ChickenFight.uproject`.

## 2. Gemini에 보낼 데이터 먼저 확인 (API 호출 없음)

```powershell
.\.venv\Scripts\python.exe -m chickenqa `
  --project "C:\Users\KHY\Desktop\AI-QA\ChickenFight.uproject" `
  --prepare-ai --out output\ai-review
notepad .\output\ai-review\ai_payload_preview.json
```

- `ai_payload_preview.json`을 열어서 공개하면 안 되는 게임 콘텐츠, 계정 ID, 세션 데이터, IP/서버 주소, 토큰 등이 남아 있지 않은지 **직접 확인**하세요. 규칙 기반 자동 마스킹은 완전하지 않습니다.
- 파일에서 불필요한 `gameplay_samples`, `findings` 등의 항목을 삭제해도 됩니다. 단, `source`의 `name`, `file_size_bytes`, `modified_ns`는 수정하지 마세요.
- 가능하면 PIE를 종료하고 Editor도 닫아 파일 변경을 멈춘 뒤 검토하세요. 같은 로그를 지정했어도 파일이 다시 기록되면 검토 과정을 다시 해야 합니다.

## 3. 검토 완료한 파일만 Gemini에 전송

```powershell
$env:GEMINI_API_KEY = Read-Host "Gemini API Key"
.\.venv\Scripts\python.exe -m chickenqa `
  --project "C:\Users\KHY\Desktop\AI-QA\ChickenFight.uproject" `
  --ai --ai-payload ".\output\ai-review\ai_payload_preview.json" `
  --out output\ai-result
notepad .\output\ai-result\report.md
```

**중요:** 키를 채팅, 스크린샷, GitHub에 포함하지 마세요. `--ai`를 지정하지 않으면 외부 AI API를 사용하지 않습니다. API에 따른 할당량/비용이 발생할 수 있습니다. 기본 모델은 `gemini-3.5-flash-lite`이며, 본인 API 계정의 사용 가능 모델과 다를 경우 `--model` 인수로 변경할 수 있습니다.

### 기존 로그가 중간에 바뀌었다면

`[오류] 검토한 AI JSON과 현재 로그 ...`가 나오면 게임/Editor가 로그를 갱신했을 수 있습니다. 입력을 고정하려면 로그를 복사한 후 `--log "C:\...\MySession.log"`로 **미리보기와 AI 실행 모두 같은 복사본**을 지정하세요. 또는 미리보기를 다시 생성하세요.

### 출력물

```
output/
├── game-local/
│   ├── report.md
│   └── summary.json
├── ai-review/
│   ├── report.md
│   ├── summary.json
│   └── ai_payload_preview.json
└── ai-result/
    ├── report.md
    └── summary.json
```

`summary.json`의 `ai_status`는 `not_requested` / `preview_only` / `completed` / `failed`입니다. `completed`는 API 응답 성공일 뿐, **AI 가설이 정답이라는 뜻이 아닙니다.**

## PowerShell로 한 번에 실행하기

```powershell
.\scripts\analyze_game_logs.ps1 `
  -Project "C:\Users\KHY\Desktop\AI-QA\ChickenFight.uproject" -PrepareAi
```

정책 제한이 있거나 PATH 문제가 있으면 위의 Python 직접 실행을 쓰세요. `--log`/`-Log`로 파일 직접 지정도 가능합니다.

## 코드 구조

```
chickenqa/
  discovery.py    # Saved/Logs, Saved/Crashes 최신 .log 탐색
  parser.py       # 규칙 기반 집계·줄 번호·부분 마스킹
  signals.py      # 검증할 가치가 있는 진단 신호
  ai.py           # AI 전송용 데이터 최소화 및 Gemini 호출
  report.py       # Markdown / JSON 보고서
  cli.py          # --project / --prepare-ai / --ai
scripts/
  analyze_game_logs.ps1
  run_unreal_tests.ps1  # C++ 자동 테스트 등록 후 사용
  run_pipeline.ps1      # 추후 자동화 확장
```

## 테스트

실제 테스트의 결함 탐지 능력을 확인하려면 [결함 주입·복원 시연](docs/FAULT_DEMO.md)을 실행합니다. 정상 6개 통과 → 충격 전달 누락 시 충돌 검사 실패 → 원본 복원 후 6개 통과를 별도 증거로 보존합니다.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m chickenqa --demo --prepare-ai --out output\demo-review
```

예제 로그는 **시연용 가상 데이터**이며 실제 게임의 성공/실패 증거가 아닙니다. 실제 테스트 코드를 추가하기 전에는 테스트 수 0을 성공으로 해석하지 마세요.

## 다음 개발 목표

1. 실제 `PostPush` / `MovementUpdate` / `Knockdown` 로그를 확보하여 진단 규칙 정밀화
2. Unreal C++ Automation 테스트 추가 (이동, 충돌 밀림, 넘어짐 판정)
3. C++ 테스트 결과 `index.json`과 이 보고서 연동
4. GitHub Issue 자동 생성은 검토/승인 후 연결

자세한 Windows 실습은 [docs/STEP3_GEMINI_REAL_GAME.md](docs/STEP3_GEMINI_REAL_GAME.md)를 참고하세요.

---
## v0.4: C++ automation smoke tests (game source is not edited by default)

For the step-by-step Korean guide, read `docs/STEP4_UNREAL_AUTOMATION.md`.

```powershell
.\.venv\Scripts\python.exe .\scripts\install_ue_tests.py --project 'C:\...\ChickenFight.uproject'
# Review DRY RUN output, then:
.\.venv\Scripts\python.exe .\scripts\install_ue_tests.py --project 'C:\...\ChickenFight.uproject' --apply
```

Compile your Unreal Editor target in Visual Studio **with the editor closed**. This kit **cannot** compile UE on the machine where the zip was built. Then run:

```powershell
.\scripts\run_unreal_tests.ps1 -Project 'C:\...\ChickenFight.uproject'
```

The tests check native class registration, character movement component defaults, and capsule defaults. They are **configuration smoke tests**, not proof that your push, movement or knockdown gameplay logic is correct. UE `index.json` must exist and show at least 3 passing ChickenQA tests. If no tests ran, the script fails deliberately.

현재 저장소의 기본 실행은 설정 검사 3개와 게임 동작 검사 3개, 총 6개를 요구합니다. 범위와 실행 방법은 [자동 테스트 안내](docs/STEP4_UNREAL_AUTOMATION.md#게임-동작-회귀-테스트-2026-11-24-추가)를 참고하세요.
