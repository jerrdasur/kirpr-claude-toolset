---
name: kirpr-onboard
description: "Use only when explicitly invoked to create or update kirpr project memory: workspace map and per-repository memory files."
---

# Project memory onboarding

Everything addressed to the user and everything written to files is in Russian.

You create or update the kirpr project memory: `.kirpr/workspace.md` in the workspace and `.kirpr/memory.md` in every service repository. Memory files are written only by the script; you prepare their content and get the user's consent.

## Initialization

1. Read `~/.local/share/kirpr/config/templates.md`, section «Project memory» — what the files hold, the budget, what must not be stored.
2. The workspace is the current directory. The script is `python3 ~/.local/share/kirpr/scripts/kirpr_memory.py`.

## Phase 1: Workspace map

1. Run `kirpr_memory.py refresh --dry-run` and show the table of services. If it reports that no services were found — say so and stop: the command runs from the directory that contains the service repositories.
2. Ask «Записать `.kirpr/workspace.md`?» — `да` / `нет`. On `да` run `kirpr_memory.py refresh`; on `нет` stop.
3. For every service with an empty «Роль», ask its role in one short phrase — one service per question. An empty answer leaves the role empty. Each answer is written with `kirpr_memory.py role --service {имя} --role "{ответ}"` right away: the user has just typed it, that is the consent.

## Phase 2: Repository memory

For every service in the table whose repository has no `.kirpr/memory.md`:

1. Read the repository for candidates for `## Как проверять`: `Makefile` targets `test`, `lint`, `generate`, `db-test`; CI files (`.gitlab-ci.yml`, `.github/workflows/*`). Show them as a list; the user strikes out what is wrong.
2. Ask at most three questions about `## Ловушки`, one at a time: generators and what not to review; generation order after a schema or annotation change; tests that need a database or a service. Skip a question if the answer is already visible in the repository.
3. Keep only what cannot be derived from the code. No architecture overview, no package list, no paths that `grep` finds.

A service whose `memory.md` already exists is not rewritten: say which sections are empty and suggest filling them by hand, then `kirpr_memory.py lint --file {путь}`.

## Phase 3: Writing

1. For every new file run `kirpr_memory.py init --file {сервис}/.kirpr/memory.md --name {имя} --check "<строка>" --check "<строка>" --traps "<строка>" --dry-run` (one `--check` / `--traps` per line; `## Уроки` stays empty — lessons are added only by `kirpr-tasks-review` and `kirpr-tasks-adapt` through the script) and show the printed file in full.
2. Ask per file: «Записать {путь}?» — `да` / `нет`. On `да` rerun the same `init` command without `--dry-run`; on `нет` skip the service.
3. Remind the user to commit the `.kirpr/` directories: memory lives in git.

A repeated invocation is incremental: only new services from the table and services without `memory.md` are processed.

## Rules

- **One question at a time.**
- **Do not write a file without the user's explicit «да»; every write goes through `kirpr_memory.py`, never by editing files directly.**
- **Do not add lessons by hand** — `## Уроки` is filled only through `kirpr_memory.py lesson add` by the review and adapt skills.
- **Do not ask about infrastructure** (monitoring, deploy, dashboards): no kirpr skill needs it.
- **Store only what cannot be derived from the code.**
