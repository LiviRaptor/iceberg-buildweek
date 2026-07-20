#!/usr/bin/env python3
"""Fail fast when a public Iceberg submission contains private material."""

from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parent
REQUIRED_FILES = {
    ".gitignore",
    "README.md",
    "config.demo.json",
    "live_dashboard_server.py",
    "livka_dashboard_core.py",
    "livka_dashboard_refactor_codex.py",
    "start_iceberg_live.sh",
    "submission_audit.py",
}
FORBIDDEN_TRACKED = {
    "config.json",
    "livka_dashboard.html",
}
TEXT_SUFFIXES = {".css", ".html", ".js", ".json", ".md", ".py", ".sh", ".txt"}
SECRET_PATTERNS = {
    "OpenAI-style API key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "private key": re.compile("-----BEGIN " + r"(?:[A-Z]+ )?PRIVATE KEY-----"),
    "absolute macOS user path": re.compile("/" + "Users/" + r"[^/\s]+/"),
}


def public_candidate_files():
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return {line for line in result.stdout.splitlines() if line}


def main():
    tracked = public_candidate_files()
    errors = []

    missing = sorted(REQUIRED_FILES - tracked)
    if missing:
        errors.append("missing required files: " + ", ".join(missing))

    forbidden = sorted(
        path for path in tracked
        if path in FORBIDDEN_TRACKED or path.startswith("private_not_for_github/")
    )
    if forbidden:
        errors.append("private/generated files are tracked: " + ", ".join(forbidden))

    for relative_path in sorted(tracked):
        path = ROOT / relative_path
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                errors.append(f"{relative_path}: possible {label}")

    if errors:
        print("Iceberg submission audit FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Iceberg submission audit passed ({len(tracked)} public candidate files checked).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
