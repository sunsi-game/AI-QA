"""Read UE Automation index.json (separate from heuristic .log scanning)."""
from __future__ import annotations
import json
from pathlib import Path
from .parser import redact


def read_unreal_report(source: Path) -> dict:
    path = source / "index.json" if source.is_dir() else source
    if not path.is_file():
        raise FileNotFoundError(f"UE 테스트 JSON을 찾을 수 없습니다: {path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict) or not isinstance(data.get("tests"), list):
        raise ValueError("예상한 UE Automation 리포트 구조가 아닙니다: tests 배열이 없습니다")
    counts = {"passed": 0, "failed": 0, "warning": 0, "not_run": 0, "other": 0}
    details = []
    for test in data["tests"]:
        if not isinstance(test, dict):
            continue
        state = str(test.get("state", "Unknown"))
        normalized = state.lower().replace(" ", "")
        if normalized in ("success", "passed", "succeeded"):
            status = "passed"
        elif normalized in ("fail", "failed"):
            status = "failed"
        elif normalized in ("successwithwarnings", "passedwithwarnings"):
            status = "warning"
        elif normalized in ("skipped", "notrun", "notexecuted"):
            status = "not_run"
        else:
            status = "other"
        counts[status] += 1
        if len(details) < 50:
            details.append({
                "name": redact(str(test.get("fullTestPath", test.get("testDisplayName", "Unknown"))))[:250],
                "state": state,
                "duration_s": test.get("duration"),
                "errors": test.get("errors"),
            })
    return {
        "file_name": path.name,
        "counts": counts,
        "total_tests": sum(counts.values()),
        "duration_s": data.get("totalDuration"),
        "details": details,
        "details_limited": len(data["tests"]) > len(details),
    }
