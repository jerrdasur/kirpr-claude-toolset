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

FIELDS = "summary,description,comment,issuelinks,subtasks"


def fetch_issue(issue_id: str, base_url: str, token: str, email: str | None) -> dict:
    url = f"{base_url}/rest/api/2/issue/{issue_id}?fields={FIELDS}"

    if email:
        # Jira Cloud: basic auth with email:token
        credentials = base64.b64encode(f"{email}:{token}".encode()).decode()
        auth_header = f"Basic {credentials}"
    else:
        # Jira Server: bearer token
        auth_header = f"Bearer {token}"

    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": auth_header,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def format_markdown(data: dict, base_url: str) -> str:
    lines = []
    fields = data.get("fields", {})
    key = data.get("key", "UNKNOWN")

    lines.append(f"# {fields.get('summary', 'No summary')}")
    lines.append("")
    lines.append(f"> [{key}]({base_url}/browse/{key})")
    lines.append("")

    desc = fields.get("description") or ""
    if desc:
        lines.append("## Description")
        lines.append("")
        lines.append(desc)
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

    base_url = base_url.rstrip("/")

    try:
        data = fetch_issue(issue_id, base_url, token, email)
    except urllib.error.HTTPError as e:
        print(f"Error: Jira API returned HTTP {e.code}: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Could not connect to Jira: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(format_markdown(data, base_url))


if __name__ == "__main__":
    main()
