#!/usr/bin/env python3
"""Report the share of Cyrillic letters outside fenced code blocks and quoted literals.

Usage: python3 tests/tools/cyrillic_report.py FILE [FILE...]

Lines inside ``` fences and lines containing «…» or "…" quotes are skipped, so the
number approximates how much *instruction* text (not user-facing literals) is Russian.
"""
import re
import sys

QUOTE = re.compile(r'«[^»]*»|"[^"]*"')
CYR = re.compile(r"[А-Яа-яЁё]")
LAT = re.compile(r"[A-Za-z]")


def share(path: str) -> float:
    cyr = lat = 0
    in_fence = False
    for line in open(path, encoding="utf-8"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or line.startswith("    "):
            continue
        line = QUOTE.sub("", line)
        line = re.sub(r"`[^`]*`", "", line)
        cyr += len(CYR.findall(line))
        lat += len(LAT.findall(line))
    return 100.0 * cyr / (cyr + lat) if (cyr + lat) else 0.0


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    for path in argv:
        print(f"{share(path):5.1f}% ru  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
