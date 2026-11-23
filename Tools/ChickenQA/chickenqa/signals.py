"""Evidence-based diagnostic signals, not assertions of root cause or test outcome."""
from __future__ import annotations
import re

# Match vector scalar tokens, not names such as 'Info' or arbitrary prose.
NONFINITE = re.compile(r"(?<![A-Za-z0-9_])(?:-?1\.#(?:INF|IND|QNAN|SNAN)|[+-]?(?:nan|inf|infinity))(?![A-Za-z0-9_])", re.I)


def find_signals(summary: dict) -> list[dict]:
    findings = summary.get("findings", [])
    samples = summary.get("gameplay_samples", [])
    results: list[dict] = []
    crashes = [f for f in findings if f.get("severity") == "crash"]
    if crashes:
        results.append({
            "code": "CRASH_LOG_PRESENT", "level": "critical",
            "observation": f"크래시 패턴 로그 {summary['counts']['crash']}줄이 기록되었습니다.",
            "evidence_lines": [x["line"] for x in crashes[:3]],
            "next_check": "첫 크래시의 호출 스택, 객체 수명 및 재현 시점을 확인하세요. 패턴 건수가 크래시 발생 횟수를 뜻하지는 않습니다.",
        })
    nonfinite = [x for x in samples if NONFINITE.search(x.get("text", ""))]
    if nonfinite:
        results.append({
            "code": "NONFINITE_GAMEPLAY_VALUE", "level": "high",
            "observation": "캐릭터 관련 디버그 로그 표본에서 NaN 또는 Inf 표기가 감지되었습니다.",
            "evidence_lines": [x["line"] for x in nonfinite[:5]],
            "next_check": "해당 값이 속도·가속도·위치 등 연산 결과인지 확인하고, 분모 0·미초기화·비정상 물리 업데이트를 검증하세요.",
        })
    events = summary.get("events", {})
    if events.get("PushApply", 0) and not events.get("PostPush", 0):
        results.append({
            "code": "PUSH_FOLLOWUP_NOT_OBSERVED", "level": "info",
            "observation": "PushApply 로그는 있지만 분석 구간에서 PostPush 로그는 확인되지 않았습니다.",
            "evidence_lines": [x["line"] for x in samples if x.get("event") == "PushApply"][:3] or [
                x["line"] for x in findings if "[PushApply]" in x.get("message", "")
            ][:3],
            "next_check": "PostPush 로깅 활성화, 로그 범위/잘림 여부, 다음 프레임 실행 여부를 먼저 확인하세요. 충돌 로직 실패로 단정할 수 없습니다.",
        })
    if summary.get("truncated"):
        results.append({
            "code": "LOG_TRUNCATED", "level": "info",
            "observation": "지정한 줄 수 제한으로 로그의 일부만 읽었습니다.",
            "evidence_lines": [],
            "next_check": "--max-lines 값을 늘리거나 --log로 특정 세션 로그를 지정해 다시 분석하세요.",
        })
    if summary["counts"].get("test_passed", 0) == 0 and summary["counts"].get("test_failed", 0) == 0 and not summary.get("unreal_test_report"):
        results.append({
            "code": "TEST_RESULT_NOT_AVAILABLE", "level": "info",
            "observation": "해당 로그에서 자동 테스트 실행 결과를 확인할 수 없습니다.",
            "evidence_lines": [],
            "next_check": "실제 Unreal Automation 테스트를 등록하고 index.json을 전달하기 전에는 성공/실패로 판단하지 마세요.",
        })
    return results
