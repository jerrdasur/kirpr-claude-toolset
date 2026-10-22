# Поведенческие evals kirpr

Регрессионный набор: проверяет, что скилы соблюдают свои контракты — срабатывают только по явному вызову, ничего не пишут без «да», находят дефекты в ревью. Гоняется вручную перед слиянием правок скилов и при смене модели. Дизайн: `docs/superpowers/specs/2026-10-22-behavior-evals-design.md`.

| Группа | Кейсы | Что проверяют |
|---|---|---|
| `trigger` | `trigger-decompose-words`, `trigger-review-words`, `trigger-unrelated`, `trigger-explicit-positive` | без явного вызова скилы kirpr не срабатывают; явный вызов панели без режима спрашивает режим |
| `hitl` | `hitl-decompose-no-files-before-agreement`, `hitl-task-delete-preview-first`, `hitl-onboard-asks-before-writing` | ни файлов, ни записей в трекер до согласия; удаление только по введённому номеру |
| `panel` | `panel-diff-planted-bugs`, `panel-no-false-regeneration` | полнота, severity, дедуп, ACCEPTANCE, проверка генерёнки без ложных срабатываний |

## Запуск

Из корня репозитория (он — плагин только для evals, `.claude-plugin/plugin.json`):

```bash
claude plugin eval . --scaffold --runs 3 --threshold 0.8 --judge-model sonnet --max-cost-usd 15 -j 4 \
  --allow-tools Bash Read Glob Grep Write Edit Agent Skill
```

- Один кейс: `claude plugin eval . --case hitl-onboard-asks-before-writing --scaffold --runs 1 --ablation none --allow-tools Read Glob Bash Skill`.
- Группа: `--tag hitl` (или `trigger`, `panel`).
- Все кейсы требуют `Bash` целиком: HITL — для скриптов kirpr, панель — для `git` и чтения проекта; панели нужны ещё `Glob`, `Grep` и `Agent`.
- Результаты пишутся в `evals/results/` (под `.gitignore`).

Скаффолд HITL-кейсов (`_fixtures/install-runtime.sh`) ставит kirpr во временный `HOME` прогона, отвечает установщику «YouTrack, `https://youtrack.example.invalid`» и копирует `_fixtures/tracker/` в рабочий каталог как `.eval-tracker/`. Кейсы задают `EVAL_KIRPR_FIXTURES=.eval-tracker`: трекер-скрипты читают задачу оттуда, а любую запись дописывают в `.eval-tracker/requests.log` вместо сети.

## Стоимость

Каждый кейс идёт `--runs` раз в двух arm (с плагином и без), плюс три вызова судьи на каждый `llm`-грейдер. Кейсы панели дороже остальных: пять параллельных агентов. Ориентир vmkteam для сопоставимого набора — около $10 за полный прогон; фактическая цена этого набора записывается сюда после первого полного прогона. Ограничитель — `--max-cost-usd`.

## Чтение отчёта

- `aggregate-result.json`: `aggregates.overallScore`, `aggregates.casesPassed` / `aggregates.casesTotal`, по кейсам — `cases[].aggregates.score` и `cases[].aggregates.delta` (разница с прогоном без плагина).
- `report.html` — тот же отчёт для браузера.
- Провал кейса — сначала прочитать trace (`--keep-temp` сохраняет каталог прогона) и решить, кто виноват: **скил нарушил контракт** (это находка — чинить скил, грейдер не подгонять) или **кейс неверен** (фикстура, регулярка, формулировка критерия `llm`).
- `delta` около нуля у кейса `trigger` — норма: без плагина скилов kirpr нет вовсе, кейс проверяет, что с плагином они не срабатывают зря.

## Codex

```bash
python3 evals/codex_smoke.py            # все кейсы с codex.json
python3 evals/codex_smoke.py --case hitl-onboard-asks-before-writing
```

Нужны `codex` в `PATH` и авторизация в `CODEX_HOME` (по умолчанию `~/.codex`). Скрипт ставит kirpr для Codex во временный `HOME`, запускает `fixture.sh` кейса и `codex exec --json --ephemeral --sandbox workspace-write --skip-git-repo-check --ignore-user-config`, затем проверяет последнее сообщение, созданные файлы, выполненные команды и `requests.log` по `codex.json` кейса. Один прогон на кейс, без судьи. Код выхода: 0 — всё ok, 1 — есть провалы, 2 — нет `codex`.

`tests/data/codex_exec_sample.jsonl` — синтетический образец потока, написанный по документации. При первом реальном прогоне замените его настоящим выводом `codex exec --json` (без секретов) и проверьте `python3 -m unittest tests.test_codex_smoke`.

## Как устроен прогон

Документация не отвечает на несколько вопросов; ответы фиксируются здесь после первого прогона (раздел ниже).

| # | Вопрос | Статус | Если нет |
|---|---|---|---|
| 1 | `HOME` скаффолда = `HOME` прогона; Bash в песочнице видит `~/.local/share/kirpr` и `~/.config/kirpr` | не проверено | HITL-кейсы теряют смысл — пересмотреть подход (сборка eval-плагина или свой харнесс) |
| 2 | `git` работает внутри прогона (на macOS — не обёртка `xcrun`) | не проверено | git из Homebrew первым в `PATH`; `_fixtures/require-git.sh` падает заранее |
| 3 | `context.history_file` принимается; его формат | не проверено | кейс `hitl-task-delete-rejects-yes` не добавляется |
| 4 | имя скила плагина в `tool_used` | не проверено | поправить регулярки `input_match` в грейдерах |
| 5 | `codex exec` читает скилы из `~/.agents/skills` временного `HOME` | не проверено | класть скилы в `.agents/skills` рабочего каталога |
| 6 | имена событий в JSONL `codex exec` (сообщение, команда) | не проверено | поправить `parse_events` по реальному образцу |
| 7 | с каким `cwd` и `$0` вызывается `scaffold_script` | не проверено | `fixture.sh` ищет `_fixtures` через `dirname "$0"`; если скрипт копируется отдельно — встроить нужное в сам `fixture.sh`, как в кейсах панели |
| 8 | `--allow-tools` принимает голые имена, а `Bash` разрешает любые команды (скрипты kirpr, `git`) | не проверено | перечислить шаблоны `Bash(python3 *)`, `Bash(git *)` явно |
| 9 | `env` кейса с ключами `EVAL_*` доходит до Bash агента (скаффолд получает только `PATH`, `HOME`, `TMPDIR`, `TERM`) | не проверено | трекер-скрипты уходят на `youtrack.example.invalid` и падают — передавать каталог фикстур файлом рядом с `tracker.md` |
| 10 | скилы читают `~/.local/share/kirpr/config/tracker-runtime.md` из временного `HOME`, поставленного скаффолдом | не проверено | HITL-кейсы проверяют не тот runtime — пересмотреть установку в скаффолде |

## Первый прогон

Отвечает на вопросы таблицы выше настоящими кейсами, без отдельного спайка:

1. `claude plugin eval . --case hitl-task-delete-preview-first --scaffold --runs 1 --ablation none --allow-tools Read Bash Skill --keep-temp` — в trace: прошёл ли `manage_youtrack.py --dry-run delete SAS-200` с превью (вопросы 1, 7, 8, 9, 10) и как записан вызов `Skill` (вопрос 4).
2. `claude plugin eval . --case panel-no-false-regeneration --scaffold --runs 1 --ablation none --allow-tools Bash Read Glob Grep Skill Agent --keep-temp` — в trace: отработал ли `git diff` (вопрос 2).
3. Из каталога `--keep-temp` первого прогона взять транскрипт; если он в `.jsonl` — попробовать кейс с `context.history_file` и промптом «да» (вопрос 3), при успехе добавить кейс `hitl-task-delete-rejects-yes`.
4. `python3 evals/codex_smoke.py --case hitl-onboard-asks-before-writing`, вывод `codex exec --json` сохранить (вопросы 5, 6).
5. Обновить таблицу «Как устроен прогон», затем полный прогон и цену — в «Стоимость».
