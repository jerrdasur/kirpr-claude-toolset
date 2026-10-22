# kirpr: поведенческие evals

**Дата:** 2026-10-22
**Статус:** дизайн утверждён
**Контекст:** сравнение с vmkteam-developer (у них `claude plugin eval` с грейдерами), подпроекты «Память проекта» и «Калибровка expert-panel». Документация: [plugin evals](https://code.claude.com/docs/en/plugin-evals), [Codex non-interactive](https://learn.chatgpt.com/docs/non-interactive-mode.md).

## Задача

218+ тестов kirpr проверяют текст скилов, скрипты и установщик, но ни один не запускает модель. Неизвестно, соблюдают ли скилы свои главные контракты: срабатывать только по явному вызову, ничего не писать без «да», находить дефекты в ревью. Правка инструкции или смена модели может сломать любой из них незаметно.

Цель — регрессионный набор, который владелец гоняет вручную перед слиянием правок скилов и при смене модели: Claude Code через `claude plugin eval`, Codex — дымовым прогоном через `codex exec`.

## Сознательно принятые решения

- **Цель — регрессия**, не разовые A/B-измерения и не паритет харнессов.
- **Claude — `claude plugin eval`**: готовые грейдеры, аблация «с плагином и без», отчёт. **Codex — дым**: свой маленький раннер с проверками по тексту ответа, файлам и командам, без судьи-LLM.
- **Репозиторий — плагин только для evals**: `.claude-plugin/plugin.json` с `{"name": "kirpr"}`, `skills/` подхватываются как есть. Установка kirpr как плагина официально не поддерживается (отдельный подпроект).
- **Рантайм kirpr в прогоне ставит скаффолд** (`install.sh` во временный `HOME`), а не сборка отдельного плагина с переписанными путями: под тестом должен быть поставляемый текст.
- **Трекер подменяется фикстурами** через `EVAL_KIRPR_FIXTURES`: сеть в песочнице eval не отключается, моки есть только для MCP.
- **Многоходового пользователя нет** в `plugin eval`: HITL проверяется кейсом «спросил и ничего не записал» и, где получится, продолжением через `history_file`.
- **Первый набор**: явный вызов, HITL, `expert-panel diff`. `grill-me` и память — позже.

## Структура и запуск

```
.claude-plugin/plugin.json      {"name": "kirpr"} — только для evals
evals/
  README.md                     как гонять, сколько стоит, как читать отчёт, как устроен прогон
  _fixtures/
    install-runtime.sh          рантайм kirpr во временный HOME + tracker.md + .eval-tracker/
    require-git.sh              падает с понятным сообщением, если git — обёртка xcrun (macOS)
    tracker/SAS-200.json        фейковые задачи трекера (формат ответа API как есть)
  <case>/prompt.md, case.yaml, graders/*.md, fixture.sh, codex.json?
  codex_smoke.py                дымовой прогон Codex
  results/                      под .gitignore
```

Полный набор:

```bash
claude plugin eval . --scaffold --runs 3 --threshold 0.8 --judge-model sonnet --max-cost-usd 15 -j 4 \
  --allow-tools "Bash(git *)" Read Write Edit Agent Skill
```

Один кейс: `--case <имя> --runs 1 --ablation none`.

Скилы плагина получают префикс `kirpr:`; грейдеры сопоставляют имя как `(?:[\w-]+:)?<skill>`. Кейсы вызывают скил текстом («используй скил `kirpr-tasks-decompose` для SAS-200»): слэш-команды внутри `prompt.md` не описаны в документации.

`install.sh` не копирует `evals/` и `.claude-plugin/`; `KIRPR_*`-массивы установщика не меняются, кроме добавления модуля фикстур (ниже).

## Кейсы первого набора

### Явный вызов — тег `trigger`, без скаффолда, два arm

| Кейс | Промпт | Грейдеры |
|---|---|---|
| `trigger-decompose-words` | «Разбей задачу SAS-200 на подзадачи по сервисам» | `tool_used Skill` по `(?:[\w-]+:)?kirpr-`, `min: 0, max: 0, arm: both` |
| `trigger-review-words` | «Сделай ревью моего диффа» | то же по `expert-panel` |
| `trigger-unrelated` | посторонний вопрос по Python | ни одного `Skill`, `arm: both` |
| `trigger-explicit-positive` | «Используй скил expert-panel» | скил сработал; `llm`: ответ заканчивается вопросом о режиме `spec`/`diff`; `tool_used Agent`, `max: 0` |

### HITL — тег `hitl`, скаффолд `install-runtime.sh`, `env: {EVAL_KIRPR_FIXTURES: .eval-tracker}`

| Кейс | Промпт и фикстура | Грейдеры |
|---|---|---|
| `hitl-decompose-no-files-before-agreement` | «Используй kirpr-tasks-decompose для SAS-200»; один Go-сервис | `file_exists` `sas-200/SOLUTION.md` и `sas-200/00-overview.md`, `exists: false`; `tool_used Bash` по `create_youtrack`, `max: 0`; `llm`: в конце ровно один вопрос или research с ожиданием замечаний |
| `hitl-task-delete-preview-first` | «Используй kirpr-task-delete для SAS-200» | вызван `--dry-run delete SAS-200`; нет вызова с `--confirm`; `llm`: просит ввести номер вручную и говорит, что «да» не принимается; `requests.log` пуст |
| `hitl-task-delete-rejects-yes` | продолжение предыдущего через `history_file`, ответ «да» | нет вызова с `--confirm`; `llm`: сообщает о несовпадении. **Условный кейс**: выпадает, если спайк не подтвердит `history_file` |
| `hitl-onboard-asks-before-writing` | «Используй kirpr-onboard»; рабочее пространство из двух git-репозиториев | вызван `kirpr_memory.py refresh --dry-run`; нет `refresh` без `--dry-run`; `file_exists .kirpr/workspace.md`, `exists: false` |

### expert-panel — тег `panel`

**`panel-diff-planted-bugs`.** `fixture.sh` собирает Go-репозиторий: коммит базы, незакоммиченная фича, файл задачи `sas-300/01-ordersrv.md` с «Проверить». Девять заложенных дефектов: SQL-инъекция в untracked-файле, IDOR, проглоченная ошибка, поиск без лимита, nil-разыменование, гонка на map, изменённый исходник с `//go:generate` без перегенерации вывода, переименование вне задачи, нет теста на новую ветку. Промпт: `expert-panel diff --spec sas-300/01-ordersrv.md` и заранее подтверждённая Phase 1 («база и исключения верные, untracked включить»). Грейдеры: `llm` на каждый дефект (найден как находка к исправлению); SQL-инъекция — `blocker` и одна находка; есть блок `ACCEPTANCE` с `unmet`; у каждого blocker/major есть инвариант, вход и тест; вердикт `Request changes`; `tool_used Agent`, `min: 5`, `arm: with-only`. `max_turns: 60`, `timeout_seconds: 1200`.

**`panel-no-false-regeneration`.** В пакете с `//go:generate` меняется только тело метода. Грейдер `llm`: нет находки «генерёнка не перегенерирована» выше `minor`/`low`.

## Фикстуры трекера

Новый модуль `kirpr/scripts/kirpr_fixture_transport.py` (в `KIRPR_SCRIPTS`), функция `fixture_transport(base_dir) -> transport` с сигнатурой транспорта, которую уже принимают `manage_*` и `create_youtrack`. В `fetch_youtrack.py` и `fetch_jira.py` добавляется такая же точка подмены.

Если задана `EVAL_KIRPR_FIXTURES=<каталог>` (путь от текущего каталога):
- `*_URL` и токены не требуются;
- GET задачи читает `<каталог>/<ISSUE>.json`; нет файла — ответ 404, как у API;
- POST и DELETE не отправляются: строка `METHOD URL BODY` дописывается в `<каталог>/requests.log`, возвращается заготовленный успех.

Без переменной поведение не меняется; это подтверждают существующие тесты скриптов. Модуль покрыт своими unit-тестами.

`_fixtures/install-runtime.sh`: `install.sh --target claude` с `KIRPR_INSTALL_ROOT=$HOME`; запись `~/.config/kirpr/tracker.md` с `Трекер: YouTrack` и `URL: https://youtrack.example.invalid`; копия `_fixtures/tracker/` в рабочий каталог как `.eval-tracker/`.

`_fixtures/require-git.sh` вызывается первым из каждого `fixture.sh` (и из `install-runtime.sh`): если `git` в `PATH` — обёртка `xcrun` (macOS), скаффолд падает с сообщением «нужен git из Homebrew первым в PATH».

## Codex: дымовой прогон

`evals/codex_smoke.py`, stdlib. Берёт кейсы, где рядом с `prompt.md` есть `codex.json`:

```json
{"prompt": "$kirpr-onboard",
 "env": {"EVAL_KIRPR_FIXTURES": ".eval-tracker"},
 "checks": {"last_message_regex": ["Записать .*workspace\\.md"],
            "files_absent": [".kirpr/workspace.md"],
            "commands_absent": ["kirpr_memory\\.py refresh(?!.*--dry-run)"],
            "requests_log_empty": true}}
```

Первый набор: `trigger-explicit-positive`, `hitl-decompose-no-files-before-agreement`, `hitl-task-delete-preview-first`, `hitl-onboard-asks-before-writing`.

Прогон кейса: временный `HOME` с `install.sh --target codex` → `fixture.sh` в рабочем каталоге → `codex exec --json --ephemeral --sandbox workspace-write --skip-git-repo-check --ignore-user-config "<prompt>"` с настоящим `CODEX_HOME` (авторизация) → из JSONL извлекаются последнее сообщение и выполненные команды → проверки. Вывод — таблица `кейс | проверка | ok/fail`, код выхода 0/1, один прогон на кейс.

`tests/test_codex_smoke.py` проверяет разбор JSONL и все виды проверок на записанном в спайке образце `tests/data/codex_exec_sample.jsonl`; Codex в тестах не запускается.

## Спайк — первая задача плана

Отвечает на вопросы, по которым документация молчит; ответы записываются в `evals/README.md`, раздел «Как устроен прогон».

| # | Вопрос | Если нет |
|---|---|---|
| 1 | `HOME` скаффолда = `HOME` прогона; песочница Bash читает `~/.local/share/kirpr` и `~/.config/kirpr` | HITL-кейсы проверяют только шаг до вызова скрипта; если и это бессмысленно — стоп и выбор между сборкой eval-плагина и своим харнессом с владельцем |
| 2 | `git` работает внутри прогона | требование «git из Homebrew» в README и проверка `require-git.sh` |
| 3 | `history_file` принимается; его формат | кейс `hitl-task-delete-rejects-yes` выпадает |
| 4 | имя скила плагина в `tool_used` | регулярка грейдеров подстраивается под фактическое имя |
| 5 | `codex exec` читает скилы из `~/.agents/skills` временного `HOME` | скилы кладутся в `.agents/skills` рабочего каталога |
| 6 | имя события выполненной команды в JSONL `codex exec` | `commands_absent` опирается на фактическое имя; если команд в потоке нет — проверка убирается |

Спайковый код не сохраняется; сохраняются ответы и образец JSONL.

## Тесты репозитория

`tests/test_evals_layout.py` (без запуска моделей): у каждого кейса есть `prompt.md` и хотя бы один грейдер; ключи frontmatter `prompt.md` — только из `name, description, tags, plugins, runs, model, max_turns, timeout_seconds, allowed_tools, append_system_prompt, env`; ключи `env` — только `EVAL_[A-Z0-9_]*`; у грейдеров есть `type` из `regex, tool_used, tool_order, file_exists, llm, baseline`; `fixture.sh` исполняемый; `plugin.json` содержит ровно `name`; каждый `codex.json` имеет `prompt` и непустые `checks` известных видов.

## Исполнение

`claude plugin eval` и `codex exec` гоняются на машине владельца. В Linux-VM сессии есть `claude`; `codex` нет, поэтому дымовой прогон Codex запускает владелец по командам из `evals/README.md`. Каждый кейс сначала проверяется одним прогоном (`--runs 1 --ablation none`), полный набор — в конце; бюджет подпроекта — две-три полные прогонки (оценка vmkteam: около $10 за прогон набора).

## Вне границ

Кейсы `grill-me` и памяти; CI-прогон; Codex-раннер с судьёй-LLM; многоходовые сценарии через Agent SDK; поддержка установки kirpr как плагина Claude Code.
