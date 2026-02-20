#!/usr/bin/env python3
"""Validate service paths from the services map in CLAUDE.md.

Usage: python3 validate_services.py <path-to-CLAUDE.md>

Parses the `## ADR: services map` section, checks that paths and entry points
exist on disk, and outputs a structured report.
"""

import os
import re
import sys

ENTRY_POINT_KEYS = ["contracts", "configs", "migrations", "entrypoint", "tests"]


def find_services_section(content: str) -> str | None:
    pattern = r"^## ADR: services map\s*\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if match:
        return match.group(1)
    return None


def parse_table(section: str) -> list[dict]:
    lines = [l.strip() for l in section.strip().split("\n") if l.strip()]

    # Find header line
    header_line = None
    for i, line in enumerate(lines):
        if line.startswith("|") and "Service" in line:
            header_line = i
            break

    if header_line is None:
        return []

    headers = [h.strip() for h in lines[header_line].strip("|").split("|")]
    headers = [h.lower() for h in headers]

    services = []
    for line in lines[header_line + 2:]:  # skip header + separator
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < len(headers):
            continue

        row = dict(zip(headers, cells))
        # Clean path: remove backticks
        path = row.get("path", "").strip("`").strip()
        services.append({
            "name": row.get("service", "").strip(),
            "path": path,
            "type": row.get("type", "").strip(),
            "contracts": row.get("contracts", "none").strip(),
            "configs": row.get("configs", "none").strip(),
            "migrations": row.get("migrations", "none").strip(),
            "entrypoint": row.get("entrypoint", "none").strip(),
            "tests": row.get("tests", "none").strip(),
        })

    return services


def validate_service(service: dict) -> dict:
    name = service["name"]
    path = service["path"]
    result = {"name": name, "status": "OK", "issues": []}

    if path == "absent":
        result["status"] = "ABSENT"
        return result

    if not os.path.isdir(path):
        result["status"] = "WARNING"
        result["issues"].append(f"Service path does not exist: {path}")
        return result

    # Check entry points
    for key in ENTRY_POINT_KEYS:
        value = service.get(key, "none")
        if value in ("none", "generated", ""):
            continue
        full_path = os.path.join(path, value)
        if not os.path.exists(full_path):
            result["status"] = "WARNING"
            result["issues"].append(f"{key}: path not found — {full_path}")

    return result


def format_report(results: list[dict]) -> str:
    lines = []
    lines.append("# Services Map Validation Report")
    lines.append("")

    ok_count = sum(1 for r in results if r["status"] == "OK")
    warn_count = sum(1 for r in results if r["status"] == "WARNING")
    absent_count = sum(1 for r in results if r["status"] == "ABSENT")

    lines.append(f"Total: {len(results)} | OK: {ok_count} | WARNING: {warn_count} | ABSENT: {absent_count}")
    lines.append("")

    for r in results:
        icon = {"OK": "OK", "WARNING": "WARNING", "ABSENT": "ABSENT"}[r["status"]]
        lines.append(f"- [{icon}] **{r['name']}**")
        for issue in r["issues"]:
            lines.append(f"  - {issue}")

    lines.append("")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_services.py <path-to-CLAUDE.md>", file=sys.stderr)
        sys.exit(1)

    claude_md_path = sys.argv[1]
    if not os.path.isfile(claude_md_path):
        print(f"Error: File not found: {claude_md_path}", file=sys.stderr)
        sys.exit(1)

    with open(claude_md_path, "r", encoding="utf-8") as f:
        content = f.read()

    section = find_services_section(content)
    if section is None:
        print("Error: Section '## ADR: services map' not found in CLAUDE.md", file=sys.stderr)
        sys.exit(1)

    services = parse_table(section)
    if not services:
        print("Error: No services found in the services map table.", file=sys.stderr)
        sys.exit(1)

    results = [validate_service(s) for s in services]
    print(format_report(results))


if __name__ == "__main__":
    main()
