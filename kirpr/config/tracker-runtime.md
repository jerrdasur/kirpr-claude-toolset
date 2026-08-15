# Выбор runtime трекера

1. Прочитай `~/.config/kirpr/tracker.md`, секцию `## Активный трекер`.
2. `Трекер: YouTrack` использует:
   - fetch: `python3 ~/.local/share/kirpr/scripts/fetch_youtrack.py`
   - create/update/delete: `python3 ~/.local/share/kirpr/scripts/manage_youtrack.py`
   - push: `python3 ~/.local/share/kirpr/scripts/create_youtrack.py`
3. `Трекер: Jira` использует:
   - fetch: `python3 ~/.local/share/kirpr/scripts/fetch_jira.py`
   - create/update/delete: `python3 ~/.local/share/kirpr/scripts/manage_jira.py`
4. Если конфигурации нет, трекер не указан или операция не поддерживается
   выбранным трекером, остановись до запуска скрипта и назови точный файл,
   который нужно настроить.
