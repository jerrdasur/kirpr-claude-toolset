# Tracker runtime selection

1. Read `~/.config/kirpr/tracker.md`, section `## Активный трекер`; find
   `URL:` and remember it as the base URL for issue links.
2. `Трекер: YouTrack` uses:
   - fetch: `python3 ~/.local/share/kirpr/scripts/fetch_youtrack.py`
   - create/update/delete: `python3 ~/.local/share/kirpr/scripts/manage_youtrack.py`
   - push: `python3 ~/.local/share/kirpr/scripts/create_youtrack.py`
3. `Трекер: Jira` uses:
   - fetch: `python3 ~/.local/share/kirpr/scripts/fetch_jira.py`
   - create/update/delete: `python3 ~/.local/share/kirpr/scripts/manage_jira.py`
4. If there is no configuration, no tracker is set, or the operation is not
   supported by the selected tracker, stop before running the script and name
   the exact file that needs to be configured.
