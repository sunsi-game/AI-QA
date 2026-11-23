"""Safely discover game logs in a specified Unreal Engine project.

Only reads from the project's Saved/Logs and Saved/Crashes directories.
Does not launch the game or modify any project files.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def validate_project(project: Path) -> Path:
    project = project.expanduser().resolve()
    if not project.is_file() or project.suffix.lower() != ".uproject":
        raise FileNotFoundError(f".uproject 파일을 찾을 수 없습니다: {project}")
    return project


def find_project_logs(project: Path) -> list[Path]:
    """Return all readable-looking .log files, newest first.

    File timestamps refer to the latest write on disk, not game session start.
    """
    project = validate_project(project)
    saved = project.parent / "Saved"
    candidates: list[Path] = []
    logs_folder = saved / "Logs"
    if logs_folder.is_dir():
        candidates.extend(p for p in logs_folder.glob("*.log") if p.is_file())
    crashes_folder = saved / "Crashes"
    if crashes_folder.is_dir():
        candidates.extend(p for p in crashes_folder.glob("**/*.log") if p.is_file())

    # If a file disappears while scanning (editor rotating logs), skip it.
    ranked = []
    for candidate in candidates:
        try:
            stat = candidate.stat()
        except OSError:
            continue
        ranked.append((stat.st_mtime_ns, candidate))
    ranked.sort(key=lambda item: (item[0], str(item[1]).lower()), reverse=True)
    return [item[1] for item in ranked]


def select_latest_log(project: Path) -> tuple[Path, dict]:
    """Select the newest project log and return reproducibility metadata."""
    project = validate_project(project)
    candidates = find_project_logs(project)
    if not candidates:
        root = project.parent / "Saved" / "Logs"
        raise FileNotFoundError(
            "프로젝트 로그를 찾지 못했습니다. "
            f"확인 위치: {root}. Unreal Editor에서 프로젝트를 실행한 뒤 다시 시도하거나 "
            "--log 로 실제 로그 파일을 직접 지정하세요."
        )
    selected = candidates[0]
    stat = selected.stat()
    meta = {
        "project_name": project.name,
        "selection_rule": "latest_modified_log",
        "relative_log_path": selected.relative_to(project.parent).as_posix(),
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
        "file_size_bytes": stat.st_size,
        "age_hours_at_analysis": round(max(0.0, (datetime.now(timezone.utc) - datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)).total_seconds() / 3600), 1),
        "candidate_log_count": len(candidates),
    }
    return selected, meta
