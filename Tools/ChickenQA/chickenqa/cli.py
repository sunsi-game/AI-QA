from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from datetime import datetime
from .ai import DEFAULT_MODEL, analyze_with_gemini, build_ai_payload, validate_payload
from .discovery import select_latest_log, find_project_logs, validate_project
from .parser import analyze_file
from .report import make_report, save_results
from .signals import find_signals
from .test_report import read_unreal_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unreal Engine 로그 분석, AI 전송 전 미리보기, 선택적 Gemini QA")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--project", type=Path, help=".uproject의 Saved/Logs 및 Saved/Crashes에서 최신 로그 자동 선택")
    group.add_argument("--log", type=Path, help="실제 Unreal .log/.txt 파일 지정")
    group.add_argument("--demo", action="store_true", help="예제 로그 (실제 게임 실행 결과 아님)")
    parser.add_argument("--list-logs", action="store_true", help="프로젝트의 로그 파일을 최신 수정순으로 출력하고 종료 (API 호출 없음)")
    parser.add_argument("--out", type=Path, default=Path("output"), help="리포트 출력 폴더")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--prepare-ai", action="store_true", help="API 호출 없이 AI 전송 예정 JSON을 저장하여 검토")
    actions.add_argument("--ai", action="store_true", help="Gemini API에 데이터 전송 (명시적 요청)")
    parser.add_argument("--ai-payload", type=Path, help="--prepare-ai에서 생성한 JSON을 AI에 그대로 전송 (--ai 필수)")
    parser.add_argument("--ue-report", type=Path, help="Unreal Automation index.json 경로 (선택)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Gemini model ID")
    parser.add_argument("--max-lines", type=int, default=200_000)
    args = parser.parse_args(argv)
    if args.max_lines < 1:
        parser.error("--max-lines는 1 이상이어야 합니다")
    if args.ai_payload and not args.ai:
        parser.error("--ai-payload는 --ai와 함께 사용해야 합니다")
    if args.list_logs and not args.project:
        parser.error("--list-logs에는 --project가 필요합니다")
    if args.list_logs and (args.prepare_ai or args.ai):
        parser.error("--list-logs에는 AI 옵션을 함께 사용할 수 없습니다")
    if args.list_logs:
        try:
            project = validate_project(args.project)
            paths = find_project_logs(project)
            if not paths:
                raise FileNotFoundError(f"로그 파일이 없습니다: {project.parent / 'Saved'}")
            print(f"[프로젝트] {project}")
            print(f"[로그 후보] {len(paths)}개, 최근 수정순 상위 15개 (PC 현지 시각)")
            for item in paths[:15]:
                modified = datetime.fromtimestamp(item.stat().st_mtime).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
                print(f"  {modified}  {item.relative_to(project.parent)}")
            return 0
        except (OSError, ValueError) as exc:
            print(f"[오류] {exc}", file=sys.stderr)
            return 2
    try:
        if args.project:
            path, selection = select_latest_log(args.project)
            print(f"[로그 선택] {path}")
            print(f"[후보 파일] {selection['candidate_log_count']}개 중 최근 수정 로그 선택")
            if selection["age_hours_at_analysis"] >= 24:
                print(f"[주의] 선택된 로그는 약 {selection['age_hours_at_analysis']:.1f}시간 전에 수정됐습니다. "
                      "현재 플레이 로그가 아닐 수 있으니 --list-logs로 확인하세요.")
        else:
            path = Path(__file__).resolve().parent.parent / "samples" / "example_crash.log" if args.demo else args.log
            selection = None
        summary = analyze_file(path, max_lines=args.max_lines)
        stat = path.stat()
        summary["log_file_size_bytes"] = stat.st_size
        summary["log_modified_ns"] = stat.st_mtime_ns
        if selection is not None:
            summary["log_selection"] = selection
        if args.ue_report:
            summary["unreal_test_report"] = read_unreal_report(args.ue_report)
        summary["signals"] = find_signals(summary)
        args.out.mkdir(parents=True, exist_ok=True)
        ai_text = None
        ai_status = "not_requested"
        if args.prepare_ai:
            payload = build_ai_payload(summary)
            preview = args.out / "ai_payload_preview.json"
            preview.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            ai_status = "preview_only"
            print(f"[AI 전송 전 검토] {preview.resolve()}")
            print("[안내] 로컬 파일만 만들었습니다. Gemini API 호출은 하지 않았습니다.")
        elif args.ai:
            # An explicit payload file allows inspecting/removing project-specific data
            # before submission. No raw Unreal log or source file is uploaded directly.
            if args.ai_payload:
                payload = validate_payload(json.loads(args.ai_payload.read_text(encoding="utf-8-sig")))
                source = payload["source"]
                if source["name"] != summary["source_name"] or source.get("file_size_bytes") != summary["log_file_size_bytes"] or source.get("modified_ns") != summary["log_modified_ns"]:
                    raise ValueError("검토한 AI JSON과 현재 로그의 이름/크기/수정 시각이 다릅니다. 같은 --log 파일로 --prepare-ai를 다시 실행하세요.")
                print(f"[AI 전송] 검토한 JSON 사용: {args.ai_payload}")
            else:
                payload = build_ai_payload(summary)
                print("[AI 전송] 규칙 기반으로 마스킹된 요약을 전송합니다. 비공개 내용은 별도 검토하세요.")
            try:
                ai_text = analyze_with_gemini(model=args.model, payload=payload)
                ai_status = "completed"
            except Exception as exc:
                # A usable local report is still produced; don't claim AI succeeded.
                ai_status = "failed"
                summary["ai_error"] = type(exc).__name__
                print(f"[AI 오류] {type(exc).__name__}: {exc}", file=sys.stderr)
                # Keep SDK automatic backoff; do not silently retry with a paid model.
                if "503" in str(exc) and "UNAVAILABLE" in str(exc).upper():
                    print("[안내] Gemini 모델이 혼잡합니다. SDK 기본 재시도 후에도 실패했습니다. "
                          "잠시 후 재요청하거나, 사용 가능한 다른 모델을 --model로 직접 지정하세요.", file=sys.stderr)
        summary["ai_status"] = ai_status
        report = make_report(summary, ai_text, args.model if ai_text else None)
        md_path, json_path = save_results(summary, report, args.out)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"[오류] {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"[오류] 분석 중 예기치 않은 문제가 발생했습니다: {type(exc).__name__}", file=sys.stderr)
        return 3
    print(f"[완료] Markdown: {md_path.resolve()}")
    print(f"[완료] JSON: {json_path.resolve()}")
    print(f"[로그 패턴 집계] {summary['counts']}")
    if "unreal_test_report" in summary:
        print(f"[Unreal Automation JSON 결과] {summary['unreal_test_report']['counts']}")
    if ai_status == "failed":
        print("[주의] 로컬 리포트는 생성되었으나 AI 분석은 실패했습니다.", file=sys.stderr)
        return 2
    return 0
