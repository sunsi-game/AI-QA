# 3단계 실습: 실제 닭싸움 게임 로그 → Gemini 진단 리포트

## 요구 사항

- Python 가상환경(`.venv`) 준비, `pip install -r requirements.txt` 완료
- 실제 게임 플레이 후 Saved/Logs에 `.log` 생성
- AI를 쓸 때만 `GEMINI_API_KEY` 필요
- 프로젝트 소스는 직접 수정하지 않으며 로그 읽기만 수행

## 실행 순서 (Windows PowerShell)

```powershell
cd "C:\Users\KHY\Desktop\AI-QA\Tools\ChickenQA"

# 1. 본인의 게임 최신 로그를 읽음 (로컬)
.\.venv\Scripts\python.exe -m chickenqa --project "C:\Users\KHY\Desktop\AI-QA\ChickenFight.uproject" --out output\v03-local

# 2. 외부로 나갈 JSON만 준비 (아직 업로드 안 함)
.\.venv\Scripts\python.exe -m chickenqa --project "C:\Users\KHY\Desktop\AI-QA\ChickenFight.uproject" --prepare-ai --out output\v03-review
notepad .\output\v03-review\ai_payload_preview.json

# 3. 파일을 꼼꼼히 확인하고 필요 없는 데이터를 지움
# 4. 같은 로그 파일에 한해 검토된 내용만 전송
$env:GEMINI_API_KEY = Read-Host "Gemini API Key"
.\.venv\Scripts\python.exe -m chickenqa --project "C:\Users\KHY\Desktop\AI-QA\ChickenFight.uproject" --ai --ai-payload .\output\v03-review\ai_payload_preview.json --out output\v03-ai

# 5. 결과 열기
notepad .\output\v03-ai\report.md
```

만일 AI 호출 전에 최신 로그가 바뀌었다는 오류가 발생한다면 `--prepare-ai`를 다시 실행하거나, 동일한 로그를 복사한 뒤 `--log <복사본>`을 1~3단계에서 통일해서 쓰세요.

## 보고서 해석과 포트폴리오 기록

- `CRASH_LOG_PRESENT`: 크래시 표현이 있었다는 사실. 개별 크래시 건수로 환산하지 않기
- `NONFINITE_GAMEPLAY_VALUE`: 샘플 텍스트에 NaN/Inf 표현 존재. 계산 오류로 확정하지 않기
- `PUSH_FOLLOWUP_NOT_OBSERVED`: PushApply가 있지만 PostPush가 없는 표본. 로깅과 프레임 진행 확인이 먼저
- `TEST_RESULT_NOT_AVAILABLE`: 자동 테스트 결과가 없는 상태. 테스트 통과로 주장하지 않기
- AI 응답의 가설은 C++ 코드와 재현 테스트로 검증해야 함

포트폴리오 스크린샷 후보: `report.md`의 집계 및 진단 섹션, `ai_status`, 테스트 실행 콘솔. 프로젝트명/사용자 경로·계정 토큰은 가리고 공개하세요.
