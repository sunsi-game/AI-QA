"""충격 전달 누락을 주입하고 실제 UE 실패와 복원 후 성공을 검증한다."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = b"GetCharacterMovement()->AddImpulse(CollisionImpulse, true);"
FAULT = b"/* ChickenQA deliberate fault: collision impulse omitted. */"
COLLISION = "ChickenQA.Gameplay.CollisionPushAndCooldown"
EXPECTED = {
    "ChickenQA.Character.CapsuleConfigured", "ChickenQA.Character.ClassRegistered",
    "ChickenQA.Character.MovementComponentReady", COLLISION,
    "ChickenQA.Gameplay.BalanceFailureGates", "ChickenQA.Gameplay.MovementAndInputGate",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_stage(project: Path, engine: str, output: Path, name: str) -> dict:
    stage = output / name
    stage.mkdir()
    command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
               str(ROOT / "scripts/run_unreal_tests.ps1"), "-Project", str(project),
               "-EngineRoot", engine, "-ReportPath", str(stage / "unreal_automation"), "-BuildEditor"]
    print(f"[ChickenQA] {name}: build and run six tests", flush=True)
    with (stage / "execution.log").open("wb") as stream:
        completed = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    index = stage / "unreal_automation/index.json"
    if not index.is_file():
        raise RuntimeError(f"{name}: no test JSON; build/launch failure is not a detected gameplay fault. See {stage}")
    raw = json.loads(index.read_text(encoding="utf-8-sig"))
    rows = raw.get("tests", [])
    states = {t["fullTestPath"]: t["state"] for t in rows}
    if len(rows) != 6 or set(states) != EXPECTED:
        raise RuntimeError(f"{name}: expected exactly the six known tests, got {states}")
    # 각 실행의 로그를 고정해 이후 실행이 앞선 증거를 덮어쓰지 않게 한다.
    log = stage / "ChickenFight.log"
    log.write_bytes((project.parent / "Saved/Logs/ChickenFight.log").read_bytes())
    analyzed = subprocess.run([sys.executable, "-m", "chickenqa", "--log", str(log),
                              "--ue-report", str(index), "--out", str(stage)], cwd=ROOT,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (stage / "analysis.log").write_bytes(analyzed.stdout)
    if analyzed.returncode:
        raise RuntimeError(f"{name}: local report generation failed")
    messages = [entry.get("event", {}).get("message", "")
                for t in rows if t["fullTestPath"] == COLLISION for entry in t.get("entries", [])]
    return {"exit_code": completed.returncode, "states": states, "collision_messages": messages}


def require_pass(result: dict) -> None:
    if result["exit_code"] != 0 or any(s != "Success" for s in result["states"].values()):
        raise RuntimeError(f"Expected all six tests to pass: {result['states']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--engine-root", default=r"C:\Program Files\Epic Games\UE_5.8")
    args = parser.parse_args()
    project = args.project.resolve(strict=True)
    source = project.parent / "Source/DKUEndGame/Character/ChickenCharacter.cpp"
    before = source.read_bytes()
    if before.count(ORIGINAL) != 1 or FAULT in before:
        raise RuntimeError("Expected exactly one original impulse call; source was not modified")
    output = ROOT / "output" / ("fault_demo_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
    output.mkdir(parents=True)
    (output / "ChickenCharacter.cpp.before").write_bytes(before)
    evidence = {"source": str(source), "original_sha256": digest(before), "stages": {}}
    evidence["test_sha256"] = digest((project.parent / "Source/DKUEndGame/Private/Tests/ChickenQAGameplayTests.cpp").read_bytes())
    evidence_path = output / "evidence.json"

    def save() -> None:
        evidence_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

    save()
    baseline = run_stage(project, args.engine_root, output, "baseline")
    evidence["stages"]["baseline"] = baseline
    save()
    require_pass(baseline)
    if source.read_bytes() != before:
        raise RuntimeError("Source changed during baseline; refusing to inject")
    mutated = before.replace(ORIGINAL, FAULT)
    (output / "mutation.diff").write_text(
        "- " + ORIGINAL.decode() + "\n+ " + FAULT.decode() + "\n", encoding="utf-8")
    source.write_bytes(mutated)
    try:
        evidence["mutated_sha256"] = digest(mutated)
        save()
        fault = run_stage(project, args.engine_root, output, "fault")
        evidence["stages"]["fault"] = fault
        save()
        expected_states = {n: ("Fail" if n == COLLISION else "Success") for n in EXPECTED}
        if fault["exit_code"] == 0 or fault["states"] != expected_states:
            raise RuntimeError("Injected fault did not cause exactly the expected collision test failure")
        for message in ("Single push velocity, no duplicate impulse", "Receiver position changes"):
            if not any(message in m for m in fault["collision_messages"]):
                raise RuntimeError(f"Expected assertion missing: {message}")
    finally:
        # 다른 작업이 소스를 편집했다면 덮어쓰지 않고 백업을 남긴다.
        if source.read_bytes() != mutated:
            raise RuntimeError(f"Source changed externally; restore manually from {output / 'ChickenCharacter.cpp.before'}")
        source.write_bytes(before)
        evidence["restored_sha256"] = digest(source.read_bytes())
        save()
        restored = run_stage(project, args.engine_root, output, "restored")
        evidence["stages"]["restored"] = restored
        save()
        require_pass(restored)
    evidence["verified"] = True
    save()
    (output / "demo.md").write_text('''# ChickenQA 결함 탐지 시연

실제 게임에서 발견한 버그가 아니라, 테스트의 탐지 능력을 확인하기 위한 의도적 결함 주입 실험입니다.

| 단계 | 성공 | 실패 | 증거 |
|---|---:|---:|---|
| 정상 기준 | 6 | 0 | [보고서](baseline/report.md) |
| 충격 전달 호출 제거 | 5 | 1 | [보고서](fault/report.md) |
| 원본 복원 및 재빌드 | 6 | 0 | [보고서](restored/report.md) |

`AddImpulse(CollisionImpulse, true)` 호출만 임시 제거했습니다. 기존 테스트의 조건은 변경하지 않았습니다.
`CollisionPushAndCooldown`에서 밀림 속도와 실제 위치 변화 검사가 실패했고, 호출 복원 뒤 통과했습니다.
원본과 복원 소스의 SHA-256은 `evidence.json`에 기록했습니다. 각 단계의 실행 로그와 UE index.json도 보존합니다.

## 2분 시연 순서

1. 정상 보고서에서 6개 통과를 보여줍니다.
2. mutation.diff의 충격 전달 호출 제거를 설명합니다.
3. 실패 보고서와 fault/unreal_automation/index.json에서 충돌 테스트의 두 실패 조건을 보여줍니다.
4. 복원 보고서의 6개 통과와 원본·복원 해시 일치를 보여줍니다.
5. 임시 월드의 네이티브 동작 회귀 검사이며 실제 맵 접촉 검출·멀티플레이·애니메이션은 별도 검증 대상이라고 설명합니다.

포트폴리오 설명: “Unreal C++ 자동 테스트와 Python 보고서를 연결하고, 충격 전달 누락을 주입해 기존 회귀 테스트의 실패와 복원 후 통과를 검증했습니다.”
''', encoding="utf-8")
    print(f"[ChickenQA] VERIFIED: {output / 'demo.md'}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
