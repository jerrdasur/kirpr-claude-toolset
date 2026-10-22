#!/usr/bin/env python3
"""Fetch a Jira issue and output formatted markdown.

Usage: python3 scripts/fetch_jira.py PROJ-200

Requires JIRA_TOKEN and JIRA_URL environment variables.
JIRA_EMAIL is required for basic auth (Jira Cloud).
"""

import json
import os
import sys
import base64
import urllib.request
import urllib.error

from kirpr_fixture_transport import FIXTURE_BASE_URL, FIXTURE_TOKEN, transport_from_env

FIELDS = "summary,description,reporter,timetracking,comment,issuelinks,subtasks"


def fetch_issue(issue_id: str, base_url: str, token: str, email: str | None, transport=None) -> dict:
    url = f"{base_url}/rest/api/2/issue/{issue_id}?fields={FIELDS}&expand=changelog"

    if email:
        # Jira Cloud: basic auth with email:token
        credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
        auth_header = f"Basic {credentials}"
    else:
        # Jira Server: bearer token
        auth_header = f"Bearer {token}"

    headers = {
        "Accept": "application/json",
        "Authorization": auth_header,
        "Content-Type": "application/json",
    }
    if transport is not None:
        status, raw = transport("GET", url, headers, None)
        if status >= 400:
            raise RuntimeError(f"HTTP {status}")
        return json.loads(raw.decode())
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def format_changelog(data: dict) -> list:
    lines = []
    changelog = data.get("changelog", {})
    histories = changelog.get("histories") or []
    if not histories:
        return lines
    lines.append("## Change History")
    lines.append("")
    for h in histories:
        author = h.get("author", {})
        name = author.get("displayName") or author.get("name") or "Unknown"
        created = h.get("created", "")[:16].replace("T", " ")
        items = h.get("items") or []
        if not items:
            continue
        lines.append(f"### {created} — {name}")
        lines.append("")
        for item in items:
            field = item.get("field", "?")
            from_str = item.get("fromString") or "—"
            to_str = item.get("toString") or "—"
            lines.append(f"- **{field}**: {from_str} → {to_str}")
        lines.append("")
    return lines


def format_markdown(data: dict, base_url: str) -> str:
    lines = []
    fields = data.get("fields", {})
    key = data.get("key", "UNKNOWN")

    lines.append(f"# {fields.get('summary', 'No summary')}")
    lines.append("")
    lines.append(f"> [{key}]({base_url}/browse/{key})")
    lines.append("")

    reporter = fields.get("reporter") or {}
    reporter_name = reporter.get("displayName") or reporter.get("name") or ""
    if reporter_name:
        lines.append(f"**Author:** {reporter_name}")
        lines.append("")

    timetracking = fields.get("timetracking") or {}
    original = timetracking.get("originalEstimate") or ""
    if original:
        lines.append(f"**Estimation:** {original}")
        lines.append("")

    desc = fields.get("description") or ""
    if desc:
        lines.append("## Description")
        lines.append("")
        lines.append(desc)
        lines.append("")

    issuelinks = fields.get("issuelinks") or []
    if issuelinks:
        lines.append("## Linked Issues")
        lines.append("")
        for link in issuelinks:
            link_type = link.get("type", {}).get("name", "related to")
            if "outwardIssue" in link:
                issue = link["outwardIssue"]
                direction = link.get("type", {}).get("outward", link_type)
                issue_key = issue.get("key", "?")
                issue_summary = issue.get("fields", {}).get("summary", "")
                lines.append(f"- **{direction}**: [{issue_key}]({base_url}/browse/{issue_key}) — {issue_summary}")
            if "inwardIssue" in link:
                issue = link["inwardIssue"]
                direction = link.get("type", {}).get("inward", link_type)
                issue_key = issue.get("key", "?")
                issue_summary = issue.get("fields", {}).get("summary", "")
                lines.append(f"- **{direction}**: [{issue_key}]({base_url}/browse/{issue_key}) — {issue_summary}")
        lines.append("")

    comment_data = fields.get("comment", {})
    comments = comment_data.get("comments", [])
    if comments:
        lines.append("## Comments")
        lines.append("")
        for c in comments:
            author = c.get("author", {})
            name = author.get("displayName") or author.get("name") or "Unknown"
            created = c.get("created", "")[:16].replace("T", " ")
            body = c.get("body") or ""
            lines.append(f"### {name} ({created})")
            lines.append("")
            lines.append(body)
            lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/fetch_jira.py <ISSUE-KEY>", file=sys.stderr)
        print("Example: python3 scripts/fetch_jira.py PROJ-200", file=sys.stderr)
        sys.exit(1)

    issue_id = sys.argv[1].strip()
    transport = transport_from_env()
    if transport is not None:
        base_url, token, email = FIXTURE_BASE_URL, FIXTURE_TOKEN, None
    else:
        base_url, token, email = _env_credentials()

    try:
        data = fetch_issue(issue_id, base_url, token, email, transport)
    except urllib.error.HTTPError as e:
        print(f"Error: Jira API returned HTTP {e.code}: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Could not connect to Jira: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    md = format_markdown(data, base_url)
    changelog_lines = format_changelog(data)
    if changelog_lines:
        md += "\n" + "\n".join(changelog_lines)
    print(md)


def _env_credentials():
    base_url = os.environ.get("JIRA_URL")
    if not base_url:
        print("Error: JIRA_URL environment variable is not set.", file=sys.stderr)
        print("Example: export JIRA_URL=https://yourcompany.atlassian.net", file=sys.stderr)
        sys.exit(1)

    token = os.environ.get("JIRA_TOKEN")
    if not token:
        print("Error: JIRA_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    email = os.environ.get("JIRA_EMAIL")  # Optional, for Jira Cloud

    return base_url.rstrip("/"), token, email


if __name__ == "__main__":
    main()
