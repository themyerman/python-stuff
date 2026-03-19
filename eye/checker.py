#!/usr/bin/env python3
"""Scan configured folders/files for risky patterns."""

import argparse
import copy
import importlib.util
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    from conf import rules as DEFAULT_RULES
except ModuleNotFoundError:
    conf_path = Path(__file__).resolve().parent / "conf.py"
    spec = importlib.util.spec_from_file_location("eye_conf_runtime", conf_path)
    conf_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conf_module)
    DEFAULT_RULES = conf_module.rules

VALID_SEVERITIES = ("high", "medium", "low", "specific")
DEFAULT_EXCLUDE_DIRS = {".git", ".hg", ".svn", "node_modules", "vendor", "__pycache__"}
COMMENT_PREFIXES = {
    ".py": ("#",),
    ".php": ("#", "//", "/*", "*"),
    ".module": ("#", "//", "/*", "*"),
    ".inc": ("#", "//", "/*", "*"),
    ".js": ("//", "/*", "*"),
}


@dataclass
class Finding:
    """Structured output for one rule match."""

    file: str
    line: int
    severity: str
    rule_id: str
    pattern: str
    snippet: str
    message: str = ""


@dataclass
class ScanResult:
    """Aggregate scan result."""

    files_scanned: int
    findings: list[Finding]
    compile_errors: list[str]


def _csv_list(value):
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def parse_args(argv):
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Scan source code for risky patterns.")
    parser.add_argument("-t", "--topdir", default=DEFAULT_RULES.get("topdir", "."))
    parser.add_argument(
        "-f",
        "--folders",
        default=",".join(DEFAULT_RULES.get("scan_folders", [])),
        help="Comma-separated folder names to include (match on path part).",
    )
    parser.add_argument(
        "-s",
        "--scan-levels",
        default=",".join(DEFAULT_RULES.get("scan_level", ["high"])),
        help="Comma-separated severities: high,medium,low",
    )
    parser.add_argument(
        "-i",
        "--ignore",
        default=",".join(DEFAULT_RULES.get("ignore", [])),
        help="Comma-separated rule patterns to ignore.",
    )
    parser.add_argument("-q", "--quick", action="store_true", help="Scan only HIGH checks.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Include pass summary.")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--fail-on",
        choices=VALID_SEVERITIES,
        default="high",
        help="Exit non-zero if findings at or above this severity exist.",
    )
    parser.add_argument("--max-findings", type=int, default=0, help="Stop after N findings (0=all).")
    parser.add_argument(
        "--exclude-dirs",
        default=",".join(sorted(DEFAULT_EXCLUDE_DIRS)),
        help="Comma-separated directory names to skip while walking.",
    )
    parser.add_argument(
        "--scan-comments",
        action="store_true",
        help="Also scan comment-only lines.",
    )
    return parser.parse_args(argv)


def is_comment_or_blank(line, extension):
    """Return True if line is blank or starts with a known comment prefix."""
    stripped = line.strip()
    if not stripped:
        return True
    prefixes = COMMENT_PREFIXES.get(extension, ("#", "//", "/*", "*"))
    return any(stripped.startswith(prefix) for prefix in prefixes)


def _compile_rules(rule_map, active_levels, ignored_patterns):
    """Compile generic/specific regex rules once."""
    generic = {}
    specific = {}
    errors = []
    for extension, ext_rules in rule_map.items():
        generic[extension] = []
        specific[extension] = {}

        for severity, patterns in ext_rules.get("general", {}).items():
            if severity not in active_levels:
                continue
            for pattern in patterns:
                if pattern in ignored_patterns:
                    continue
                try:
                    compiled = re.compile(pattern, re.IGNORECASE)
                except re.error as exc:
                    errors.append(f"[{extension}:{severity}] invalid regex `{pattern}`: {exc}")
                    continue
                generic[extension].append((severity, pattern, compiled))

        for filename, checks in ext_rules.get("specific", {}).items():
            compiled_checks = []
            for rule_id, rule_def in checks.items():
                for pattern, expected in rule_def.items():
                    try:
                        compiled = re.compile(pattern, re.IGNORECASE)
                    except re.error as exc:
                        errors.append(
                            f"[{extension}:{filename}:{rule_id}] invalid regex `{pattern}`: {exc}"
                        )
                        continue
                    compiled_checks.append((rule_id, pattern, expected, compiled))
            specific[extension][filename] = compiled_checks
    return generic, specific, errors


def _iter_target_files(topdir, include_folders, valid_extensions, exclude_dirs):
    """Yield file paths filtered by extension and included folder names."""
    base = Path(topdir).resolve()
    include_set = set(include_folders)
    exclude_set = set(exclude_dirs)

    for root, dirs, files in os_walk(base):
        dirs[:] = [d for d in dirs if d not in exclude_set]
        root_path = Path(root)
        if include_set:
            root_parts = set(root_path.parts)
            if not (include_set & root_parts):
                continue
        for filename in files:
            extension = Path(filename).suffix
            if extension in valid_extensions:
                yield root_path / filename


def os_walk(path):
    """Wrapper for os.walk to simplify testing/mocking."""
    import os

    return os.walk(path)


def scan_with_rules(
    rule_config,
    topdir,
    include_folders,
    active_levels,
    ignored_patterns,
    exclude_dirs,
    scan_comments=False,
    max_findings=0,
):
    """Execute scanner and return structured findings."""
    rule_set = rule_config["rule_set"]
    extensions = set(rule_config["extensions"])
    compiled_generic, compiled_specific, compile_errors = _compile_rules(
        rule_set,
        set(active_levels),
        set(ignored_patterns),
    )

    findings = []
    files_scanned = 0
    for file_path in _iter_target_files(topdir, include_folders, extensions, exclude_dirs):
        files_scanned += 1
        extension = file_path.suffix
        file_specific = compiled_specific.get(extension, {}).get(file_path.name, [])
        file_generic = compiled_generic.get(extension, [])
        try:
            with file_path.open("r", encoding="utf-8", errors="replace") as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not scan_comments and is_comment_or_blank(line, extension):
                        continue
                    for rule_id, pattern, expected, regex in file_specific:
                        if regex.search(line):
                            findings.append(
                                Finding(
                                    file=str(file_path),
                                    line=line_number,
                                    severity="specific",
                                    rule_id=rule_id,
                                    pattern=pattern,
                                    snippet=line[:140].strip(),
                                    message=f"FAIL! should be {expected}",
                                )
                            )
                    for severity, pattern, regex in file_generic:
                        # Keep historical behavior: require leading whitespace before check.
                        if re.search(rf"\s{pattern}", line, flags=re.IGNORECASE):
                            findings.append(
                                Finding(
                                    file=str(file_path),
                                    line=line_number,
                                    severity=severity,
                                    rule_id=pattern,
                                    pattern=pattern,
                                    snippet=line[:140].strip(),
                                )
                            )
                    if max_findings and len(findings) >= max_findings:
                        return ScanResult(files_scanned, findings, compile_errors)
        except OSError as exc:
            compile_errors.append(f"Unable to read {file_path}: {exc}")
    return ScanResult(files_scanned, findings, compile_errors)


def severity_rank(severity):
    order = {"low": 1, "medium": 2, "high": 3, "specific": 4}
    return order.get(severity, 0)


def has_failing_findings(findings, fail_on):
    """Return True if any finding meets/exceeds fail_on severity."""
    threshold = severity_rank(fail_on)
    return any(severity_rank(item.severity) >= threshold for item in findings)


def render_text(result, show_ok=False):
    """Render text output compatible with terminal usage."""
    lines = [
        "=====================================================",
        "==         EYE OF SAURON                           ==",
        '==       "the eye sees all"                        ==',
        "=====================================================",
        "",
    ]
    if result.compile_errors:
        lines.append("CONFIG/RUNTIME ERRORS:")
        lines.extend(f"- {err}" for err in result.compile_errors)
        lines.append("")

    if not result.findings:
        lines.append("No findings.")
    else:
        for item in result.findings:
            if item.message:
                lines.append(
                    f"[{item.severity.upper()}]\t{item.file}:{item.line}\t{item.rule_id}\t{item.message}"
                )
            else:
                lines.append(
                    f"[{item.severity.upper()}]\t{item.file}:{item.line}\t{item.rule_id}\t{item.snippet}"
                )
    if show_ok:
        lines.append("")
        lines.append(f"Files scanned: {result.files_scanned}")
        lines.append(f"Findings: {len(result.findings)}")
    return "\n".join(lines)


def render_json(result):
    """Render machine-readable output."""
    payload = {
        "files_scanned": result.files_scanned,
        "findings_count": len(result.findings),
        "compile_errors": result.compile_errors,
        "findings": [asdict(item) for item in result.findings],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def main(argv=None):
    """CLI entrypoint."""
    args = parse_args(argv or sys.argv[1:])
    runtime_rules = copy.deepcopy(DEFAULT_RULES)

    if args.quick:
        active_levels = ["high"]
    else:
        active_levels = [level.lower() for level in _csv_list(args.scan_levels)]
    active_levels = [level for level in active_levels if level in ("high", "medium", "low")]
    if not active_levels:
        active_levels = ["high"]

    include_folders = _csv_list(args.folders)
    ignored_patterns = _csv_list(args.ignore)
    exclude_dirs = _csv_list(args.exclude_dirs)

    result = scan_with_rules(
        rule_config=runtime_rules,
        topdir=args.topdir,
        include_folders=include_folders,
        active_levels=active_levels,
        ignored_patterns=ignored_patterns,
        exclude_dirs=exclude_dirs,
        scan_comments=args.scan_comments,
        max_findings=max(0, args.max_findings),
    )

    if args.format == "json":
        print(render_json(result))
    else:
        print(render_text(result, show_ok=args.verbose))

    if result.compile_errors:
        return 2
    if has_failing_findings(result.findings, args.fail_on):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
