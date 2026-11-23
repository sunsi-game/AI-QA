# ChickenQA v0.4 — Unreal C++ 자동 테스트 연결

## 현재 범위

- 게임의 기존 `ChickenCharacter.cpp` 내용을 수정하지 않습니다.
- 프로젝트의 `.uproject` 모듈명과 `AChickenCharacter : public ACharacter` 선언을 찾아 `Source/<module>/Private/Tests/ChickenQASmokeTests.cpp`를 생성합니다.
- 생성되는 **3개 기본(Smoke) 테스트**는 게임의 실제 충돌/넘어짐 동작이 아닌 기본 설정을 검증합니다.
- Unreal Engine 빌드와 테스트 실행은 사용자 Windows PC에서 진행해야 합니다.
- 프로젝트 소스는 백업하거나 Git 브랜치에서 적용하세요.

## 1. 준비 확인

```powershell
cd 'C:\Users\KHY\Desktop\AI-QA\Tools\ChickenQA'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 2. 프로젝트 선택 및 설치 전 점검(DRY RUN)

`AI-QA` 프로젝트를 실제로 수정하는 경우:

```powershell
$project = 'C:\Users\KHY\Desktop\AI-QA\ChickenFight.uproject'
.\.venv\Scripts\python.exe .\scripts\install_ue_tests.py --project $project
```

**원본 `DKU` 프로젝트에 적용하려면** 반드시 아래로 바꾸세요.

```powershell
$project = 'C:\Users\KHY\Desktop\DKU\DKUEndGame\ChickenFight.uproject'
.\.venv\Scripts\python.exe .\scripts\install_ue_tests.py --project $project
```

출력된 `Module`, `Class`, `DRY RUN` 경로가 현재 작업하는 프로젝트와 일치하는지 확인합니다. 실제 프로젝트 코드가 아직 업로드되지 않았으므로 클래스 선언 구조가 다르면 설치기를 수정해야 할 수 있습니다.

## 3. 자동 테스트 파일 생성

```powershell
.\.venv\Scripts\python.exe .\scripts\install_ue_tests.py --project $project --apply
```

이미 생성한 파일은 같은 내용이면 그대로 두고, 다르면 덮어쓰지 않습니다. 생성 직후부터는 해당 C++ 파일이 Git 변경사항으로 표시됩니다.

## 4. 에디터 종료 후 컴파일

1. Unreal Editor 종료
2. 필요하다면 `.uproject`를 우클릭해 Visual Studio 프로젝트 파일 생성
3. 이 프로젝트는 **`DKUEndGameEditor` / Development Editor / Win64** 대상으로 빌드 (`ChickenFight.uproject` 파일명과 타깃명은 다릅니다)
4. 컴파일 오류가 생기면 해당 오류 메시지를 확인하고 수정 (게임 코드를 함부로 변경하지 마세요)

## 5. 테스트 실행

```powershell
.\scripts\run_unreal_tests.ps1 -Project $project -BuildEditor
```

기본 엔진 경로는 `C:\Program Files\Epic Games\UE_5.8`입니다. 다른 경로라면 `-EngineRoot`를 지정하세요.

`-BuildEditor`는 `Source/*Editor.Target.cs`에서 단일 Editor 타깃을 찾아 먼저 빌드합니다. 빌드 실패 시 테스트를 실행하지 않습니다. 이미 해당 프로젝트의 최신 소스를 빌드했다면 옵션을 생략할 수 있습니다.

`No automation tests matched 'ChickenQA.Character'`는 테스트 실패가 아니라 테스트 미발견입니다. 테스트 파일 추가 뒤 Editor를 재빌드했는지, 빌드와 실행에 같은 `$project`를 사용했는지 확인하세요. 소스 파일을 복사한 것만으로 실행 DLL에 테스트가 등록되지는 않습니다.

## 6. 실제 통과 여부 확인

성공은 **Unreal 실행 프로세스 종료 코드가 0인 것만으로 인정하지 않습니다.** `index.json`에 `ChickenQA.Character.*` 세 항목이 있고 전부 `Success`일 때만 통과로 확인합니다.

- `ChickenQA.Character.ClassRegistered`: 네이티브 클래스 등록, CDO 확인
- `ChickenQA.Character.MovementComponentReady`: MovementComponent와 기본 수치 유효성
- `ChickenQA.Character.CapsuleConfigured`: CapsuleComponent 및 캡슐 크기 유효성

이 테스트는 **실제 이동/충돌 물리·넘어짐 판정·복제 상태**를 실행 검증하지 않습니다. 이것들은 `ChickenCharacter.cpp/.h`의 최신 함수를 검토한 다음 테스트 시나리오를 만들어야 합니다.

## 7. 자동 분석 리포트로 연결

```powershell
.\scripts\run_pipeline.ps1 -Project $project -RunTests -BuildEditor
```

이 명령은 UE 자동 테스트 결과가 검증되었을 경우에만 ChickenQA Python 리포트를 생성합니다. AI 호출은 하지 않으며 Gemini API의 503 상태와 관계없이 진행할 수 있습니다.

## 주의

- 2026-11-24 Codex 검증: UE 5.8.2에서 `DKUEndGameEditor` 재빌드 후 세 테스트 모두 `Success`, 파이프라인 종료 코드 0 및 보고서 생성 확인. 실행 증거는 로컬 `output/run_20261124_054716_936/unreal_automation/index.json`입니다. 게임 동작 테스트 완료를 뜻하지 않습니다.
- 보고서의 로그 패턴 건수와 Automation JSON의 실제 테스트 수는 별개입니다. 실행 결과는 JSON 결과 항목을 확인하세요.

- 필요한 `AChickenCharacter` 헤더가 없거나 클래스 선언이 다르면 설치기가 오류를 내고 파일을 생성하지 않습니다.
- UE가 설치되지 않은 환경에서는 C++ 컴파일과 실제 테스트 실행을 검증할 수 없습니다.
- 테스트 단계부터 원본 게임 코드를 덮어쓰거나 무단으로 GitHub에 push하지 마세요.


## 게임 동작 회귀 테스트 (2026-11-24 추가)

현재 저장소에는 `ChickenQA.Gameplay.*` 세 테스트가 추가되어 기본 실행은 기존 설정 검사와 합쳐 6개를 요구합니다. `install_ue_tests.py`는 여전히 기본 설정 검사 파일만 설치합니다. 다른 프로젝트에 설치할 때 이 게임 전용 테스트가 함께 설치되는 것은 아닙니다.

| 테스트 | 검증 조건 |
|---|---|
| MovementAndInputGate | 실제 MoveForward 입력 후 이동 컴포넌트를 30프레임 실행하여 위치 변화 확인, 라운드 입력 차단 뒤 정지 |
| CollisionPushAndCooldown | 멀어지는 접촉 거절, 접근하는 접촉의 밀림과 실제 위치 변화, 연속 접촉의 충격 중복 방지 |
| BalanceFailureGates | 네 방향 내부·표시 기울기 조건, 공중/발사 대기 제외, 지상 즉시 탈락, 방향 선택과 중복 탈락 거절 |

테스트는 임시 월드의 네이티브 캐릭터를 사용합니다. 수평 이동은 중력을 분리한 Flying 모드이며 충돌 접촉 정보와 기울기 경계 상태를 주입합니다. 실제 충돌 응답·이동 적분·탈락 함수는 게임 구현을 실행합니다. 맵에서의 자연 충돌 검출, 바닥 걷기, 자동 홉, Blueprint/애니메이션, 네트워크 복제까지 검증한 것은 아닙니다. 테스트 전용 friend 접근은 `WITH_DEV_AUTOMATION_TESTS`에서만 활성화됩니다.

기본 설정 검사만 실행할 때:

```powershell
.\scripts\run_unreal_tests.ps1 -Project $project -TestPrefix 'ChickenQA.Character.' -MinTests 3
```


실행 검증: UE 5.8.2 / 2026-11-24, `output/run_20261124_062845_155/unreal_automation/index.json`에서 설정 3개와 동작 3개 모두 Success, 파이프라인 종료 코드 0. 첫 충돌 검사 실패는 BeginPlay를 생략한 임시 월드의 이동 컴포넌트 비활성 때문이었으며 준비 단계의 Activate(true)로 해결했다. 게임 결함을 발견·수정한 사례로 표현하지 않는다.

이 실행의 로그 경고 패턴 187건은 자동 테스트 실패 수가 아니다. 기존 OnMovementModeChanged의 LogTemp Warning 디버그 출력과 Automation의 재출력 등이 포함된다. JSON 상태는 6개 모두 Success이며 경고 로그가 없다는 뜻은 아니다.
