"""Rule-based parser. All counts are observable log patterns, not inferred root causes."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re

CRASH = re.compile(r"Unhandled Exception|EXCEPTION_ACCESS_VIOLATION|Fatal error:|Assertion failed:", re.I)
ERROR = re.compile(r"\bLog\w+:\s*Error:|\bError:\s|Ensure condition failed|Test Completed\. Result=Failed", re.I)
WARNING = re.compile(r"\bLog\w+:\s*Warning:|\bWarning:\s", re.I)
TEST = re.compile(r"Test Completed\. Result=(\w+).*?(?:Path=([^\s]+))?", re.I)
EVENT_NAMES = "PushApply|PushDispatch|PushStop|MovementUpdate|PostPush|Knockdown|Fallen"
EVENT = re.compile(r"\[(" + EVENT_NAMES + r")\]")
# Bare event names count only when they *start* a LogChicken message,
# not when they occur as ordinary fields (e.g., Fallen=0).
EVENT_BARE = re.compile(
    r"\bLogChicken\w*:\s*(?:(?:Warning|Error|Display|Verbose|VeryVerbose|Log):\s*)?(" + EVENT_NAMES + r")\b",
    re.I,
)
CHICKEN_CATEGORY = re.compile(r"\bLogChicken\w*:", re.I)

# Selected examples of sensitive data; users must review for project-specific secrets.
REDACTIONS = [
    # Drop HTTP URL query strings, which often include telemetry UserID/SessionID,
    # auth tokens or server-specific secrets. Preserve the endpoint for diagnosis.
    (re.compile(r'(?i)(https?://[^\s\]\?]+)\?[^\s\]]+'), r'\1?[QUERY_REDACTED]'),
    (re.compile(r'(?i)(\b(?:UserID|SessionID)\s*[=:]\s*)[^\s,;\]\}"]+'), r'\1[REDACTED]'),
    (re.compile(r"(?i)\b(LoginId|EpicAccountId)\s*:\s*\S+"), r"\1: [REDACTED]"),
    (re.compile(r"(?i)(\b(?:api[_-]?key|access[_-]?token|password|secret)\s*[=:]\s*)[^\s,;]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(\bAuthorization:\s*Bearer\s+)\S+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(\b(?:refresh[_-]?token|client[_-]?secret|session[_-]?token)\s*[=:]\s*)[^\s,;]+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)([A-Z]:\\Users\\)[^\\\s]+"), r"\1[USER]"),
    (re.compile(r"(?i)(/home/)[^/\s]+"), r"\1[USER]"),
    (re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
]


def redact(value: str) -> str:
    for pattern, replacement in REDACTIONS:
        value = pattern.sub(replacement, value)
    return value


@dataclass(frozen=True)
class Finding:
    line: int
    severity: str
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


def analyze_file(path: Path, max_lines: int = 200_000, max_findings: int = 120) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"로그 파일이 없습니다: {path}")
    counts = {"crash": 0, "error": 0, "warning": 0, "test_passed": 0, "test_failed": 0}
    findings: list[Finding] = []
    events: dict[str, int] = {}
    gameplay_samples: list[dict] = []
    gameplay_sample_counts: dict[str, int] = {}
    total = 0
    truncated = False
    crash_contexts: list[dict] = []
    current_context = None
    context_remaining = 0
    with path.open("r", encoding="utf-8-sig", errors="replace") as stream:
        for number, raw in enumerate(stream, start=1):
            if number > max_lines:
                truncated = True
                break
            total = number
            line = redact(raw.strip())
            if CRASH.search(line):
                severity = "crash"
            elif ERROR.search(line):
                severity = "error"
            elif WARNING.search(line):
                severity = "warning"
            else:
                severity = ""
            if current_context is not None and context_remaining > 0:
                if line:
                    current_context["following_lines"].append({"line": number, "text": line[:500]})
                context_remaining -= 1
            if severity:
                counts[severity] += 1
                if len(findings) < max_findings:
                    findings.append(Finding(number, severity, line[:900]))
            # Small bounded context for the first crash records; a stack trace
            # often follows the Unhandled Exception line without severity tags.
            if severity == "crash" and len(crash_contexts) < 3:
                current_context = {"line": number, "message": line[:900], "following_lines": []}
                crash_contexts.append(current_context)
                context_remaining = 10
            match = TEST.search(line)
            if match:
                status = match.group(1).lower()
                if status in ("passed", "success", "succeeded"):
                    counts["test_passed"] += 1
                elif status in ("failed", "fail"):
                    counts["test_failed"] += 1
            event_names = set(EVENT.findall(line))
            if CHICKEN_CATEGORY.search(line):
                event_names.update(EVENT_BARE.findall(line))
            for key in event_names:
                events[key] = events.get(key, 0) + 1
            if CHICKEN_CATEGORY.search(line):
                group = sorted(event_names)[0] if event_names else "other_gameplay"
                if gameplay_sample_counts.get(group, 0) < 5 and len(gameplay_samples) < 55:
                    gameplay_samples.append({"line": number, "event": group, "text": line[:700]})
                    gameplay_sample_counts[group] = gameplay_sample_counts.get(group, 0) + 1
    return {
        "source_name": path.name,
        "lines_scanned": total,
        "truncated": truncated,
        "counts": counts,
        "events": events,
        "gameplay_samples": gameplay_samples,
        "crash_contexts": crash_contexts,
        "findings": [f.to_dict() for f in findings],
        "findings_limited": sum(counts[key] for key in ("crash", "error", "warning")) > len(findings),
    }
