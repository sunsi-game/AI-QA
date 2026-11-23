"""Produce auditable reports with deterministic observations separated from AI hypotheses."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json


def make_report(summary: dict, ai_text: str | None = None, model: str | None = None) -> str:
    counts = summary["counts"]
    header = [
        "# ChickenQA 분석 리포트",
        "",
        f"- 생성 시간(UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 로그: `{summary['source_name']}`",
        f"- 확인한 줄: {summary['lines_scanned']:,}",
        f"- 로그 일부만 분석했는가: {'예' if summary['truncated'] else '아니요'}",
        "- 참고: 탐지 건수는 로그의 패턴 매칭 건수이며 고유 오류 개수와 다릅니다.",
        "",
        "## 1. 자동 집계 (로그에 존재하는 사실)",
        "",
        "| 항목 | 건수 |",
        "|---|---:|",
        f"| 크래시 관련 로그 | {counts['crash']} |",
        f"| 오류 관련 로그 | {counts['error']} |",
        f"| 경고 로그 | {counts['warning']} |",
        f"| 로그에서 탐지한 테스트 통과 패턴 | {counts['test_passed']} |",
        f"| 로그에서 탐지한 테스트 실패 패턴 | {counts['test_failed']} |",
        "",
        "### 게임 이벤트 마커",
    ]
    if "log_selection" in summary:
        selected = summary["log_selection"]
        header[6:6] = [
            f"- Unreal 프로젝트: `{selected['project_name']}`",
            f"- 선택한 로그 위치: `{selected['relative_log_path']}`",
            f"- 마지막 파일 수정 시각(UTC): {selected['modified_utc']}",
            f"- 검사한 로그 후보: {selected['candidate_log_count']}개 (수정 시각이 가장 최근인 파일 선택)",
            "- 주의: 새 로그가 자동 선택되었다는 사실만으로 게임 기능 테스트가 실행된 것은 아닙니다.",
            *([f"- **주의: 로그 수정 후 {selected['age_hours_at_analysis']:.1f}시간 경과 — 현재 게임 플레이 기록이 아닐 수 있습니다.**"]
              if selected.get('age_hours_at_analysis', 0) >= 24 else []),
        ]
    if summary["events"]:
        header.extend(f"- `{event}`: {count}건" for event, count in sorted(summary["events"].items()))
    else:
        header.append("- 인식한 이벤트 마커 없음")
    header.extend(["", "### 게임 디버그 로그 표본 (이벤트 종류별 최대 5줄)"])
    if summary.get("gameplay_samples"):
        header.extend(
            f"- L{item['line']} [{item['event']}] `{item['text'].replace('`', chr(39))}`"
            for item in summary["gameplay_samples"]
        )
    else:
        header.append("- `LogChicken*` 형태의 게임 디버그 로그가 감지되지 않았습니다. 로그 설정을 확인하세요.")
    header.extend(["", "### 근거 로그 (라인 번호)"])
    if summary["findings"]:
        header.extend(f"- L{f['line']} [{f['severity']}] `{f['message'].replace('`', chr(39))}`" for f in summary["findings"])
        if summary["findings_limited"]:
            header.append("- 표시 개수 제한으로 일부 로그는 생략되었습니다.")
    else:
        header.append("- 인식한 크래시·오류·경고 로그 없음 (정상 동작을 증명하지는 않습니다).")
    if summary["lines_scanned"] == 0:
        header.append("- **주의: 선택한 로그가 비어 있습니다. 게임 실행 및 로그 기록 상태를 확인하세요.**")
    if summary.get("crash_contexts"):
        header.extend(["", "### 크래시 직후 문맥 (최대 3개, 각 10줄)"])
        for ctx in summary["crash_contexts"]:
            header.append(f"- L{ctx['line']} 크래시 관련 로그: `{ctx['message'].replace('`', chr(39))}`")
            header.extend(
                f"  - L{line['line']}: `{line['text'].replace('`', chr(39))}`"
                for line in ctx["following_lines"]
            )
    if "unreal_test_report" in summary:
        result = summary["unreal_test_report"]
        count = result["counts"]
        header.extend([
            "", "## 2. Unreal Automation JSON 결과 (실제 테스트 수행 결과)", "",
            f"- 테스트 수: **{result['total_tests']}**",
            f"- 성공: {count['passed']} / 실패: {count['failed']} / 경고 동반: {count['warning']} / 미실행: {count['not_run']} / 기타: {count['other']}",
        ])
        if not result["total_tests"]:
            header.append("- **주의: 등록 또는 실행된 테스트가 없습니다. 이 결과를 테스트 통과로 표시하지 마세요.**")
        if result["details"]:
            header.extend(["", "| 테스트 이름 | 상태 |", "|---|---|"])
            header.extend(f"| {t['name'].replace('|','/')} | {t['state']} |" for t in result["details"])
    header.extend(["", "## 3. 진단 신호 (근거 기반 검토 제안)", ""])
    for signal in summary.get("signals", []):
        evidence = ", ".join(f"L{num}" for num in signal["evidence_lines"]) or "로그 줄 직접 인용 없음"
        header.extend([
            f"- **[{signal['level']}] {signal['code']}**: {signal['observation']}",
            f"  - 근거: {evidence}",
            f"  - 다음 확인: {signal['next_check']}",
        ])
    if not summary.get("signals"):
        header.append("- 사전 정의된 진단 신호 없음 (기능 정상이라는 의미는 아닙니다).")
    header.extend(["", "## 4. AI 분석 (검증이 필요한 가설)", ""])
    if ai_text:
        header.extend([f"- 분석 모델: `{model}`", "", ai_text])
    else:
        if summary.get("ai_status") == "preview_only":
            header.append("AI 전송 데이터 미리보기만 생성했습니다. API 호출은 하지 않았습니다.")
        elif summary.get("ai_status") == "failed":
            header.append("AI 분석 요청에 실패했습니다. 로컬 집계는 유지되며 AI 가설은 없습니다.")
        else:
            header.append("AI 분석 미실행. `--ai` 옵션을 명시해야 API 요청이 발생합니다.")
    header.extend(["", "---", "이 문서는 자동 생성된 보조 자료입니다. 최종 원인과 수정 효과는 개발자가 재현 테스트로 검증해야 합니다."])
    return "\n".join(header) + "\n"


def save_results(summary: dict, report: str, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / "report.md"
    json_path = output_dir / "summary.json"
    md_path.write_text(report, encoding="utf-8")
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return md_path, json_path
