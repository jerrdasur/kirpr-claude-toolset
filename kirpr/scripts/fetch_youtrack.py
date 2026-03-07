#!/usr/bin/env python3
"""Fetch a YouTrack issue and output formatted markdown.

Usage: python3 scripts/fetch_youtrack.py SAS-200

Requires YOUTRACK_URL and YOUTRACK_TOKEN environment variables.
"""

import json
import os
import sys
import urllib.request
import urllib.error

FIELDS = "$type,id,summary,description,reporter(login,name),estimation(presentation),comments(author(login,name),created,text),links(direction,linkType(name),issues(id,summary))"


def fetch_issue(issue_id: str, base_url: str, token: str) -> dict:
    url = f"{base_url}/api/issues/{issue_id}?fields={FIELDS}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


ACTIVITY_FIELDS = "author(login,name),timestamp,field(name,presentation),added(name),removed(name)"


def fetch_activities(issue_id: str, base_url: str, token: str) -> list:
    url = f"{base_url}/api/issues/{issue_id}/activities?fields={ACTIVITY_FIELDS}&categories=CustomFieldCategory,SprintCategory,IssueResolvedCategory"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Cache-Control": "no-cache",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return []


def format_activities(activities: list) -> list:
    from datetime import datetime, timezone

    lines = []
    if not activities:
        return lines
    lines.append("## Change History")
    lines.append("")
    for a in activities:
        author = a.get("author") or {}
        name = author.get("name") or author.get("login") or "Unknown"
        ts = a.get("timestamp")
        if isinstance(ts, (int, float)):
            ts_str = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        else:
            ts_str = str(ts or "")
        field = a.get("field") or {}
        field_name = field.get("presentation") or field.get("name") or "?"
        added = a.get("added")
        removed = a.get("removed")
        added_str = added.get("name") if isinstance(added, dict) else str(added) if added is not None else "—"
        removed_str = removed.get("name") if isinstance(removed, dict) else str(removed) if removed is not None else "—"
        lines.append(f"- {ts_str} — **{name}**: {field_name}: {removed_str} → {added_str}")
    lines.append("")
    return lines


def format_markdown(data: dict, base_url: str) -> str:
    lines = []
    lines.append(f"# {data.get('summary', 'No summary')}")
    lines.append("")
    lines.append(f"> [{data['id']}]({base_url}/issue/{data['id']})")
    lines.append("")

    reporter = data.get("reporter") or {}
    reporter_name = reporter.get("name") or reporter.get("login") or ""
    if reporter_name:
        lines.append(f"**Author:** {reporter_name}")
        lines.append("")

    estimation = data.get("estimation") or {}
    estimation_text = estimation.get("presentation") or ""
    if estimation_text:
        lines.append(f"**Estimation:** {estimation_text}")
        lines.append("")

    desc = data.get("description") or ""
    if desc:
        lines.append("## Description")
        lines.append("")
        lines.append(desc)
        lines.append("")

    links = data.get("links") or []
    if links:
        lines.append("## Linked Issues")
        lines.append("")
        for link in links:
            link_type = link.get("linkType", {}).get("name", "related to")
            direction = link.get("direction", "BOTH")
            issues = link.get("issues") or []
            for issue in issues:
                issue_id = issue.get("id", "?")
                issue_summary = issue.get("summary", "")
                lines.append(f"- **{link_type}** ({direction}): [{issue_id}]({base_url}/issue/{issue_id}) — {issue_summary}")
        lines.append("")

    comments = data.get("comments") or []
    if comments:
        lines.append("## Comments")
        lines.append("")
        for c in comments:
            author = c.get("author", {})
            name = author.get("name") or author.get("login") or "Unknown"
            created = c.get("created", "")
            if isinstance(created, (int, float)):
                from datetime import datetime, timezone
                created = datetime.fromtimestamp(created / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            text = c.get("text") or ""
            lines.append(f"### {name} ({created})")
            lines.append("")
            lines.append(text)
            lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/fetch_youtrack.py <ISSUE-ID>", file=sys.stderr)
        print("Example: python3 scripts/fetch_youtrack.py SAS-200", file=sys.stderr)
        sys.exit(1)

    issue_id = sys.argv[1].strip()
    base_url = os.environ.get("YOUTRACK_URL")
    if not base_url:
        print("Error: YOUTRACK_URL environment variable is not set.", file=sys.stderr)
        print("Example: export YOUTRACK_URL=https://youtrack.example.com", file=sys.stderr)
        sys.exit(1)
    base_url = base_url.rstrip("/")

    token = os.environ.get("YOUTRACK_TOKEN")
    if not token:
        print("Error: YOUTRACK_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    try:
        data = fetch_issue(issue_id, base_url, token)
        activities = fetch_activities(issue_id, base_url, token)
    except urllib.error.HTTPError as e:
        print(f"Error: YouTrack API returned HTTP {e.code}: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Could not connect to YouTrack: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    md = format_markdown(data, base_url)
    activity_lines = format_activities(activities)
    if activity_lines:
        md += "\n" + "\n".join(activity_lines)
    print(md)


if __name__ == "__main__":
    main()
