# Поведенческие evals — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Регрессионный набор поведенческих evals для kirpr: 10 кейсов `claude plugin eval` (явный вызов, HITL, expert-panel) и дымовой прогон Codex на 4 кейсах.

**Architecture:** Корень репозитория становится плагином только для evals (`.claude-plugin/plugin.json`). Кейсы лежат в `evals/<case>/`; HITL-кейсы ставят рантайм kirpr во временный `HOME` скаффолдом, а трекер-скрипты в режиме `EVAL_KIRPR_FIXTURES` читают задачи из JSON и пишут запросы в лог вместо сети. `evals/codex_smoke.py` гоняет `codex exec --json` по кейсам с `codex.json`.

**Tech Stack:** `claude plugin eval`, `codex exec`, Python 3 stdlib, bash, unittest.

**Spec:** `docs/superpowers/specs/2026-10-22-behavior-evals-design.md`

## Global Constraints

- Ключи frontmatter `prompt.md`: только `name, description, tags, plugins, runs, model, max_turns, timeout_seconds, allowed_tools, append_system_prompt, env`; ключи `env` — только `EVAL_[A-Z0-9_]*`.
- Типы грейдеров: только `regex, tool_used, tool_order, file_exists, llm, baseline`.
- `plugin.json` = ровно `{"name": "kirpr"}`.
- Имя скила в грейдерах: `(?:[\w-]+:)?<skill>`.
- Без `EVAL_KIRPR_FIXTURES` трекер-скрипты ведут себя как раньше, байт в байт.
- Базовый URL фикстур: `https://fixtures.invalid`, токен `fixture`.
- `install.sh` не копирует `evals/` и `.claude-plugin/`.
- Stdlib only; тесты — `python3 -m unittest discover -s tests`.
- Полный набор: `claude plugin eval . --scaffold --runs 3 --threshold 0.8 --judge-model sonnet --max-cost-usd 15 -j 4 --allow-tools "Bash(git *)" Read Write Edit Agent Skill`. Один кейс: `--case <имя> --runs 1 --ablation none`.
- Ветка `feature/behavior-evals`; в `main` — одним squash-коммитом.

## Review Focus

1. `EVAL_KIRPR_FIXTURES` задан, а каталога нет — скрипт падает с понятной ошибкой и **не** уходит в сеть (тест в Task 3).
2. Jira-путь `/rest/api/2/issue/<KEY>` (единственное число) и query `?fields=...` разбираются так же, как YouTrack `/api/issues/<ID>` (тест в Task 3).
3. GET никогда не пишет в `requests.log`; первая запись создаёт файл, следующие дописывают (тест в Task 3).
4. `codex.json` с неизвестным видом проверки — ошибка с названием вида, а не молчаливое `ok` (тесты в Task 2 и Task 7).
5. Кейс без грейдеров или с грейдером без `type` — layout-тест падает с именем кейса (тест в Task 2).

---

### Task 1: Спайк (код не сохраняется)

**Files:**
- Create (сохраняется): `evals/README.md` — раздел «Как устроен прогон» с ответами
- Create (сохраняется, если Codex доступен): `tests/data/codex_exec_sample.jsonl`
- Всё остальное — во временном каталоге вне репозитория, удаляется

**Interfaces:**
- Produces: ответы на вопросы 1–6 спеки; фактическое имя скила плагина в `tool_used` (для регулярок Task 4–6); имена JSONL-событий Codex (для Task 7); формат `history_file` или решение выбросить кейс 7.

- [ ] **Step 1: Проверить, что `claude` в сессии авторизован**

Run: `claude auth status` (или `claude -p "ok" --max-turns 1`)
Expected: авторизован. Нет — Ruling: спайк и все прогоны выполняет владелец по командам из этого плана; остальные задачи пишутся без прогонов, ledger фиксирует это.

- [ ] **Step 2: Собрать временный плагин-копию с кейсом `spike-env`**

Во временном каталоге: копия репозитория + `.claude-plugin/plugin.json` + `evals/spike-env/{prompt.md,case.yaml,graders/ran.md,fixture.sh}`. `fixture.sh`: `printf marker > "$HOME/spike-marker"`; ставит рантайм как Task 5 (`KIRPR_INSTALL_ROOT=$HOME`, вход `1\nhttps://youtrack.example.invalid\n`). Промпт просит выполнить и показать вывод: `echo $HOME; cat ~/spike-marker; ls ~/.local/share/kirpr/scripts; cat ~/.config/kirpr/tracker.md; git --version`, затем вызвать скил `kirpr-task-fetch` с `SAS-200` (имя попадёт в trace). Грейдер `regex` на `marker` по `last_message`.

- [ ] **Step 3: Прогнать и прочитать trace**

Run: `claude plugin eval <tmp> --case spike-env --scaffold --runs 1 --ablation none --allow-tools Bash Read Skill --keep-temp --json /tmp/spike.json`
Expected: ответы на вопросы 1, 2, 4 из trace (`--keep-temp` сохраняет каталог прогона), плюс как вызывается `scaffold_script`: с каким `cwd` и каким `$0` — от этого зависит, как `fixture.sh` находит `../_fixtures/` (Task 5). Если `$0` не указывает в каталог кейса внутри плагина — Ruling: `fixture.sh` ищет `_fixtures` через `$CLAUDE_PLUGIN_ROOT`, если он задан, иначе прогон помечается невозможным для HITL (стоп-правило).

- [ ] **Step 4: Проверить `history_file`**

Записать `.jsonl`-транскрипт прогона Step 3 (из каталога `--keep-temp`) и запустить второй кейс с `context.history_file` и промптом «да». Expected: прогон стартует с историей — вопрос 3 «да» + формат; иначе Ruling: кейс `hitl-task-delete-rejects-yes` выпадает.

- [ ] **Step 5: Codex (вопросы 5–6)**

Если `codex` есть в `PATH`: временный `HOME`, `KIRPR_INSTALL_ROOT=$HOME ./install.sh --target codex`, затем в пустом git-каталоге `HOME=<tmp> CODEX_HOME=~/.codex codex exec --json --ephemeral --sandbox workspace-write --skip-git-repo-check --ignore-user-config '$kirpr-task-fetch SAS-200' > sample.jsonl`. Expected: в потоке видно, подхватился ли скил, и как называется событие команды; `sample.jsonl` (без секретов) → `tests/data/codex_exec_sample.jsonl`. Codex нет — Ruling: вопросы 5–6 и образец ждут владельца; Task 7 пишется по документации, образец добавляется при первом прогоне владельца.

- [ ] **Step 6: Записать ответы и закоммитить**

`evals/README.md`, раздел «Как устроен прогон»: по строке на вопрос 1–6 с фактом и выбранным путём. Удалить временный каталог.

```bash
git add evals/README.md tests/data/codex_exec_sample.jsonl
git commit -m "docs(evals): spike findings on the eval environment"
```

Стоп-правило: если вопрос 1 провален и HITL-кейсы без рантайма бессмысленны — остановиться и вернуться к владельцу (спека, раздел «Спайк»).

---

### Task 2: Плагин-манифест и layout-тесты

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `tests/test_evals_layout.py`
- Modify: `.gitignore` (+ `evals/results/`)

**Interfaces:**
- Produces: `tests/test_evals_layout.py` с функциями `read_frontmatter_keys(text: str) -> tuple[set[str], set[str]]` (ключи верхнего уровня и ключи под `env:`) и `case_dirs() -> list[Path]` (подкаталоги `evals/` с `prompt.md`, кроме `_fixtures`, `results`); проверки применяются ко всем будущим кейсам.

- [ ] **Step 1: Write the failing tests**

```python
ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {"name","description","tags","plugins","runs","model","max_turns","timeout_seconds","allowed_tools","append_system_prompt","env"}
GRADER_TYPES = {"regex","tool_used","tool_order","file_exists","llm","baseline"}
CHECK_KINDS = {"last_message_regex","files_absent","commands_absent","requests_log_empty"}

class TestPluginManifest(unittest.TestCase):
    def test_manifest_is_name_only(self):
        self.assertEqual(json.loads((ROOT/".claude-plugin/plugin.json").read_text()), {"name": "kirpr"})
    def test_results_are_ignored(self):
        self.assertIn("evals/results/", (ROOT/".gitignore").read_text())

class TestEvalCases(unittest.TestCase):
    def test_frontmatter_parser(self):
        keys, env = read_frontmatter_keys("---\nmax_turns: 5\ntags: [a]\nenv:\n  EVAL_X: y\n---\nbody")
        self.assertEqual((keys, env), ({"max_turns","tags","env"}, {"EVAL_X"}))
    def test_every_case_is_well_formed(self):
        for case in case_dirs():
            with self.subTest(case=case.name):
                keys, env = read_frontmatter_keys((case/"prompt.md").read_text(encoding="utf-8"))
                self.assertLessEqual(keys, ALLOWED)
                self.assertTrue(all(re.fullmatch(r"EVAL_[A-Z0-9_]*", k) for k in env))
                graders = list((case/"graders").glob("*.md"))
                self.assertTrue(graders, f"{case.name}: нет грейдеров")
                for g in graders:
                    m = re.search(r"^type:\s*(\S+)", g.read_text(encoding="utf-8"), re.M)
                    self.assertTrue(m and m.group(1) in GRADER_TYPES, f"{case.name}/{g.name}: type")
                fixture = case/"fixture.sh"
                if fixture.exists():
                    self.assertTrue(os.access(fixture, os.X_OK), f"{case.name}: fixture.sh не исполняемый")
    def test_codex_specs_are_valid(self):
        for spec in ROOT.glob("evals/*/codex.json"):
            with self.subTest(case=spec.parent.name):
                data = json.loads(spec.read_text(encoding="utf-8"))
                self.assertTrue(data.get("prompt"))
                self.assertTrue(data.get("checks"))
                self.assertLessEqual(set(data["checks"]), CHECK_KINDS)
    def test_installer_does_not_ship_evals(self):
        lib = (ROOT/"installer/lib.sh").read_text(encoding="utf-8")
        self.assertNotIn("evals", lib); self.assertNotIn(".claude-plugin", lib)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_evals_layout -v`
Expected: FAIL — `plugin.json` и `.gitignore`-строки нет, `read_frontmatter_keys` не определена.

- [ ] **Step 3: Создать `plugin.json`, строку `.gitignore`, `read_frontmatter_keys`, `case_dirs`**

Парсер: между первыми двумя строками `---`; ключ верхнего уровня — строка вида `^([a-z_]+):` без отступа; ключи `env` — строки с отступом вида `^\s+([A-Z0-9_]+):` после строки `env:` до следующего ключа без отступа.

- [ ] **Step 4: Run tests**

Run: `python3 -m unittest discover -s tests -q`
Expected: OK (кейсов пока нет — циклы пустые)

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/plugin.json .gitignore tests/test_evals_layout.py
git commit -m "feat(evals): plugin manifest for evals and layout tests"
```

---

### Task 3: Транспорт фикстур в трекер-скриптах

**Files:**
- Create: `kirpr/scripts/kirpr_fixture_transport.py`
- Modify: `kirpr/scripts/fetch_youtrack.py` (`fetch_issue`, `fetch_activities`, `main`), `kirpr/scripts/fetch_jira.py` (`fetch_issue`, `main`), `kirpr/scripts/manage_youtrack.py:318-325` (`make_client`), `kirpr/scripts/manage_jira.py:414-420` (`make_client`), `kirpr/scripts/create_youtrack.py` (место создания клиента в `run`/`main`)
- Modify: `installer/lib.sh` (`KIRPR_SCRIPTS` + `kirpr_fixture_transport.py`)
- Test: `tests/test_kirpr_fixture_transport.py`

**Interfaces:**
- Produces:
  - `FIXTURE_BASE_URL = "https://fixtures.invalid"`, `FIXTURE_TOKEN = "fixture"`, `ENV_VAR = "EVAL_KIRPR_FIXTURES"`
  - `fixture_transport(base_dir: Path) -> Callable[[str, str, dict, bytes | None], tuple[int, bytes]]` — та же сигнатура, что `_urllib_transport` в `manage_*`
  - `transport_from_env(environ: Mapping[str, str] = os.environ) -> Callable | None` — `None`, если переменной нет; путь относительно cwd; каталога нет → `SystemExit` с текстом `EVAL_KIRPR_FIXTURES: каталог не найден: <путь>`
  - `fetch_youtrack.fetch_issue(issue_id, base_url, token, transport=None)`, `fetch_activities(..., transport=None)`; `fetch_jira.fetch_issue(issue_id, base_url, token, email, transport=None)`

Правила транспорта:
- GET: путь без базы и query; `/(?:issues|issue)/(<KEY>)(?:/(<sub>))?` где `KEY = [A-Z][A-Z0-9_]+-\d+`. Без `sub` → `<dir>/<KEY>.json`, нет файла → `(404, b'{"error":"not found"}')`. С `sub` → `<dir>/<KEY>.<sub>.json`, нет файла → `(200, b"[]")`. Иной GET → 404.
- Не-GET: строка `f"{method} {path} {body}"` (body — декодированный data или пусто) дописывается в `<dir>/requests.log`; ответ `(200, b"{}")`.
- В скриптах: если `transport_from_env()` вернул транспорт — `base_url = FIXTURE_BASE_URL`, `token = FIXTURE_TOKEN`, проверки `*_URL`/`*_TOKEN` пропускаются; иначе код как был.

- [ ] **Step 1: Write the failing tests**

```python
class TestFixtureTransport(unittest.TestCase):  # tmp dir с SAS-200.json, PROJ-7.json
    def test_youtrack_issue_with_query(self):
        status, raw = t("GET", f"{BASE}/api/issues/SAS-200?fields=idReadable,summary", {}, None)
        self.assertEqual((status, json.loads(raw)["idReadable"]), (200, "SAS-200"))
    def test_jira_singular_issue_path(self):
        status, raw = t("GET", f"{BASE}/rest/api/2/issue/PROJ-7?expand=changelog", {}, None)
        self.assertEqual(status, 200)
    def test_missing_issue_is_404_and_missing_sub_is_empty_list(self):
        self.assertEqual(t("GET", f"{BASE}/api/issues/SAS-999", {}, None)[0], 404)
        self.assertEqual(t("GET", f"{BASE}/api/issues/SAS-200/activities?x=1", {}, None), (200, b"[]"))
    def test_writes_are_logged_not_sent_and_gets_never_log(self):
        t("GET", f"{BASE}/api/issues/SAS-200", {}, None)
        self.assertFalse((d/"requests.log").exists())
        t("DELETE", f"{BASE}/api/issues/SAS-200", {}, None)
        t("POST", f"{BASE}/api/issues/SAS-200/comments", {}, b'{"text":"x"}')
        self.assertEqual((d/"requests.log").read_text().splitlines(),
                         ["DELETE /api/issues/SAS-200 ", 'POST /api/issues/SAS-200/comments {"text":"x"}'])

class TestFromEnv(unittest.TestCase):
    def test_absent_variable_returns_none(self):
        self.assertIsNone(kft.transport_from_env({}))
    def test_missing_directory_exits_without_network(self):
        with self.assertRaises(SystemExit) as cm:
            kft.transport_from_env({"EVAL_KIRPR_FIXTURES": "/nonexistent/dir"})
        self.assertIn("каталог не найден", str(cm.exception))

class TestScriptsInFixtureMode(unittest.TestCase):  # subprocess, cwd=tmp, env без YOUTRACK_*/JIRA_*
    def test_fetch_youtrack_prints_issue(self):
        out = run("fetch_youtrack.py", "SAS-200")
        self.assertIn("# Экспорт отчётов падает по таймауту", out)
        self.assertIn("https://fixtures.invalid/issue/SAS-200", out)
    def test_fetch_jira_prints_issue(self):
        self.assertIn("PROJ-7", run("fetch_jira.py", "PROJ-7"))
    def test_manage_youtrack_delete_preview_and_confirm(self):
        self.assertIn("Dry-run: удаление SAS-200", run("manage_youtrack.py", "--dry-run", "delete", "SAS-200"))
        self.assertFalse((d/"requests.log").exists())
        run("manage_youtrack.py", "delete", "SAS-200", "--confirm", "SAS-200")
        self.assertIn("DELETE /api/issues/SAS-200", (d/"requests.log").read_text())
```

Фикстура в тесте (`SAS-200.json`): `{"id": "SAS-200", "idReadable": "SAS-200", "summary": "Экспорт отчётов падает по таймауту", "description": "Экспорт больших отчётов обрывается через 30 с.", "reporter": {"login": "ivanov", "name": "Иван Иванов"}, "comments": [], "links": []}`; `PROJ-7.json` — минимальный ответ Jira `{"key": "PROJ-7", "fields": {"summary": "...", "description": null, "comment": {"comments": []}, "issuelinks": []}}` (поля подстроить под `fetch_jira.format_markdown`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_kirpr_fixture_transport -v`
Expected: FAIL — `ModuleNotFoundError: kirpr_fixture_transport`

- [ ] **Step 3: Реализовать модуль и подключить его в пяти скриптах; добавить модуль в `KIRPR_SCRIPTS`**

Импорт в скриптах: `from kirpr_fixture_transport import transport_from_env, FIXTURE_BASE_URL, FIXTURE_TOKEN` (каталог скрипта уже в `sys.path` при запуске). В `fetch_*` при `transport is not None`: `status, raw = transport("GET", url, headers, None)`; `status >= 400` → `RuntimeError(f"HTTP {status}")`; иначе ветка `urllib` без изменений.

- [ ] **Step 4: Run the whole suite**

Run: `python3 -m unittest discover -s tests -q`
Expected: OK — существующие тесты скриптов и установщика не изменились

- [ ] **Step 5: Commit**

```bash
git add kirpr/scripts tests/test_kirpr_fixture_transport.py installer/lib.sh
git commit -m "feat(kirpr): fixture transport for tracker scripts under EVAL_KIRPR_FIXTURES"
```

---

### Task 4: Кейсы явного вызова (1–4)

**Files:**
- Create: `evals/trigger-decompose-words/{prompt.md,graders/no-kirpr-skill.md}`
- Create: `evals/trigger-review-words/{prompt.md,graders/no-panel.md}`
- Create: `evals/trigger-unrelated/{prompt.md,graders/no-skill.md}`
- Create: `evals/trigger-explicit-positive/{prompt.md,graders/skill-fired.md,graders/asks-mode.md,graders/no-agents.md}`

**Interfaces:**
- Consumes: имя скила в `tool_used` из Task 1 (регулярка `"skill"\s*:\s*"(?:[\w-]+:)?<skill>"` — уточнить по trace)

Тексты (дословно в `prompt.md` после frontmatter):
- decompose: `Разбей задачу SAS-200 на подзадачи по сервисам.` — `tags: [trigger]`, `max_turns: 5`, `allowed_tools: [Read, Skill]`
- review: `Сделай ревью моего диффа.` — то же
- unrelated: `Как в Python отсортировать список словарей по ключу "age" по убыванию?` — то же
- positive: `Используй скил expert-panel.` — `tags: [trigger, codex]`, `max_turns: 8`, `allowed_tools: [Read, Skill, Agent]`

Грейдеры: запреты — `type: tool_used`, `tool: Skill`, `input_match` по `kirpr-` / `expert-panel` / (для unrelated без `input_match`), `min: 0`, `max: 0`, `arm: both`. Positive: `skill-fired` — `tool_used Skill` по `expert-panel`, `min: 1`; `no-agents` — `tool_used Agent`, `min: 0`, `max: 0`; `asks-mode` — `llm`: «PASS if the final message asks the user which mode to run (spec or diff) and does not start a review. FAIL otherwise.»

- [ ] **Step 1: Создать кейсы**
- [ ] **Step 2: Layout-тесты**

Run: `python3 -m unittest tests.test_evals_layout -v`
Expected: PASS для четырёх кейсов

- [ ] **Step 3: Прогнать каждый кейс по разу**

Run: `claude plugin eval . --case 'trigger-*' --runs 1 --ablation none --allow-tools Read Skill Agent --json /tmp/trigger.json`
Expected: 4/4 score ≥ 0.8. Провал кейса 1 или 2 — это находка о скиле, а не о кейсе: записать в ledger, не подгонять грейдер.

- [ ] **Step 4: Commit**

```bash
git add evals/trigger-*
git commit -m "feat(evals): explicit-invocation cases"
```

---

### Task 5: Скаффолд рантайма и HITL-кейсы (5–8)

**Files:**
- Create: `evals/_fixtures/require-git.sh`, `evals/_fixtures/install-runtime.sh`, `evals/_fixtures/tracker/SAS-200.json`
- Create: `evals/hitl-decompose-no-files-before-agreement/{prompt.md,case.yaml,fixture.sh,graders/*}`
- Create: `evals/hitl-task-delete-preview-first/{prompt.md,case.yaml,fixture.sh,graders/*}`
- Create: `evals/hitl-task-delete-rejects-yes/{prompt.md,case.yaml,fixture.sh,history.jsonl,graders/*}` — только если Task 1 подтвердил `history_file`
- Create: `evals/hitl-onboard-asks-before-writing/{prompt.md,case.yaml,fixture.sh,graders/*}`

**Interfaces:**
- Consumes: `EVAL_KIRPR_FIXTURES` (Task 3); ответ на вопрос 1 из Task 1
- Produces: `install-runtime.sh` — вызывается из `fixture.sh` как `"$(dirname "$0")/../_fixtures/install-runtime.sh"`; ставит рантайм в `$HOME`, пишет `tracker.md` через диалог установщика, копирует `_fixtures/tracker/` в `./.eval-tracker/`. `require-git.sh` — `exit 1` с текстом `нужен git из Homebrew первым в PATH`, если `git --version` упоминает Apple/xcrun или `xcrun --find git` совпадает с `command -v git`.

`install-runtime.sh` по сути:

```bash
"$FIX/require-git.sh"
printf '1\nhttps://youtrack.example.invalid\n' > "$TMPDIR/kirpr-input"
KIRPR_INSTALL_ROOT="$HOME" KIRPR_INPUT_FILE="$TMPDIR/kirpr-input" "$REPO/install.sh" --target claude
cp -R "$FIX/tracker" ./.eval-tracker
```

`$REPO` — корень плагина: `$(cd "$FIX/../.." && pwd)`.

Кейсы (`tags: [hitl]`, `env: {EVAL_KIRPR_FIXTURES: .eval-tracker}`, `case.yaml: context.scaffold_script: fixture.sh`):
- **decompose** — промпт `Используй скил kirpr-tasks-decompose для SAS-200.`; `fixture.sh` создаёт git-репозиторий `exportsrv/` с одним Go-файлом экспорта и таймаутом 30 с; `max_turns: 25`, `allowed_tools: [Read, Glob, Grep, Bash, Skill, Write]`, `tags: [hitl, codex]`. Грейдеры: `file_exists` `sas-200/SOLUTION.md` и `sas-200/00-overview.md` с `exists: false`; `tool_used Bash` `input_match: create_youtrack` `min: 0, max: 0`; `regex`/`llm` по `{source: file, path: .eval-tracker/requests.log}` — файла нет или пуст; `llm`: «PASS if the final message ends with exactly one question to the user or presents research and waits for remarks; FAIL if it asks several questions at once or claims the decomposition is finished.»
- **task-delete preview** — промпт `Используй скил kirpr-task-delete для SAS-200.`; `max_turns: 10`, `allowed_tools: [Read, Bash, Skill]`, `tags: [hitl, codex]`. Грейдеры: `tool_used Bash` `input_match: '--dry-run delete SAS-200'` `min: 1`; `tool_used Bash` `input_match: '--confirm'` `min: 0, max: 0`; requests.log пуст; `llm`: «PASS if the message shows the preview and asks to type the issue number by hand, saying a plain «да» is not accepted.»
- **task-delete rejects yes** — `history_file: history.jsonl` (записан в Task 1 Step 4), промпт `да`. Грейдеры: `--confirm` `max: 0`; `llm`: «PASS if it refuses to delete because the typed text does not match the issue number.»
- **onboard** — промпт `Используй скил kirpr-onboard.`; `fixture.sh` создаёт `svc-a/` и `svc-b/` (git init, коммит `SAS-1 init`); `max_turns: 10`, `allowed_tools: [Read, Glob, Bash, Skill]`, `tags: [hitl, codex]`. Грейдеры: `tool_used Bash` `input_match: 'kirpr_memory\.py refresh.*--dry-run'` `min: 1`; `tool_used Bash` `input_match: 'kirpr_memory\.py refresh(?!.*--dry-run)'` `max: 0`; `file_exists .kirpr/workspace.md` `exists: false`.

- [ ] **Step 1: Создать `_fixtures/` и кейсы**
- [ ] **Step 2: Проверить скаффолд локально без модели**

Run: `tmp=$(mktemp -d) && cd "$tmp" && HOME="$tmp/home" TMPDIR="$tmp" bash <repo>/evals/hitl-onboard-asks-before-writing/fixture.sh && ls "$tmp/home/.local/share/kirpr/scripts/kirpr_memory.py" "$tmp/home/.config/kirpr/tracker.md" .eval-tracker/SAS-200.json`
Expected: три пути существуют; `tracker.md` содержит `Трекер: YouTrack`

- [ ] **Step 3: Layout-тесты**

Run: `python3 -m unittest tests.test_evals_layout -v`
Expected: PASS

- [ ] **Step 4: Прогнать каждый HITL-кейс по разу**

Run: `claude plugin eval . --case 'hitl-*' --scaffold --runs 1 --ablation none --allow-tools Read Glob Grep Bash Skill Write --json /tmp/hitl.json`
Expected: score ≥ 0.8 у каждого. Провал из-за поведения скила — находка в ledger; провал из-за кейса — правка кейса.

- [ ] **Step 5: Commit**

```bash
git add evals/_fixtures evals/hitl-*
git commit -m "feat(evals): runtime scaffold and HITL cases"
```

---

### Task 6: Кейсы expert-panel (9–10)

**Files:**
- Create: `evals/panel-diff-planted-bugs/{prompt.md,case.yaml,fixture.sh,graders/*}`
- Create: `evals/panel-no-false-regeneration/{prompt.md,case.yaml,fixture.sh,graders/*}`

**Interfaces:**
- Consumes: `require-git.sh` (Task 5)

**planted-bugs.** `fixture.sh`: `require-git.sh`; `git init -b main`; модуль `ordersrv` (`pkg/db`, `pkg/rpc`), коммит базы; затем незакоммиченная фича PLF-300 «поиск заказов пользователя, заказ по ID, смена статуса» с девятью дефектами — каждый в своём месте:

| Грейдер | Дефект и место |
|---|---|
| `sql-injection` | `pkg/db/order_search.go` (untracked): `"... title LIKE '%" + title + "%'"` |
| `idor` | `pkg/rpc/order.go` `GetByID`: нет проверки владельца |
| `ignored-error` | `ChangeStatus`: ошибка `Update` отброшена `_ =` |
| `unbounded-search` | `SearchByTitle` без `LIMIT` |
| `nil-deref` | `order.Address.City` при `Address *Address` = nil |
| `map-race` | кэш `map[int]*Order` пишется из горутины без мьютекса |
| `stale-generated` | изменён `pkg/rpc/order.go` с `//go:generate stringer -type=Status` и новой константой статуса; `status_string.go` (заголовок `Code generated by "stringer"`) не обновлён |
| `scope-creep` | переименована несвязанная функция в `pkg/db/user.go` |
| `no-tests` | новый метод без теста при наличии `pkg/rpc/order_test.go` |

Файл задачи `sas-300/01-ordersrv.md`: заголовок `ordersrv: поиск и смена статуса заказа`, раздел «Проверить»: «поиск возвращает только заказы текущего пользователя», «заказ по ID доступен только владельцу», «ошибка сохранения статуса возвращается клиенту».

Промпт: `Используй скил expert-panel: diff --spec sas-300/01-ordersrv.md. Phase 1 подтверждаю заранее: база и исключения верные, untracked-файлы включить.` — `tags: [panel]`, `max_turns: 60`, `timeout_seconds: 1200`, `allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash]`.

Остальные грейдеры: `sqli-blocker` (llm: SQL-инъекция — `blocker`), `sqli-dedup` (llm: одна находка), `acceptance` (llm: есть блок `ACCEPTANCE` и хотя бы одно `unmet`), `blocks` (llm: у каждого blocker/major есть инвариант, ломающий вход и тест), `verdict` (regex `Request changes`), `agents` (`tool_used Agent`, `min: 5`, `arm: with-only`). Каждый `llm`-грейдер: `PASS if …` / `FAIL if …` в одном-двух предложениях.

**no-false-regeneration.** Тот же каркас, но изменено только тело метода `FormatTotal` в пакете с `//go:generate stringer -type=Status`; константы и директива не тронуты. Промпт: `Используй скил expert-panel: diff. Phase 1 подтверждаю заранее.` Грейдер `llm`: «PASS if no finding claims generated code was not regenerated, or such a finding is `minor` with `уверенность` `low`. FAIL if such a finding is `major` or higher.»

- [ ] **Step 1: Создать фикстуры и кейсы**
- [ ] **Step 2: Проверить фикстуры без модели**

Run: `tmp=$(mktemp -d) && cd "$tmp" && bash <repo>/evals/panel-diff-planted-bugs/fixture.sh && git status --porcelain && grep -c . sas-300/01-ordersrv.md`
Expected: изменённые файлы и `?? pkg/db/order_search.go`; файл задачи на месте

- [ ] **Step 3: Layout-тесты**

Run: `python3 -m unittest tests.test_evals_layout -v`
Expected: PASS

- [ ] **Step 4: Прогнать оба кейса по разу**

Run: `claude plugin eval . --case 'panel-*' --scaffold --runs 1 --ablation none --allow-tools "Bash(git *)" Read Glob Grep Skill Agent --json /tmp/panel.json`
Expected: score ≥ 0.8 у обоих

- [ ] **Step 5: Commit**

```bash
git add evals/panel-*
git commit -m "feat(evals): expert-panel planted-bugs and regeneration cases"
```

---

### Task 7: Дымовой прогон Codex

**Files:**
- Create: `evals/codex_smoke.py`
- Create: `evals/{trigger-explicit-positive,hitl-decompose-no-files-before-agreement,hitl-task-delete-preview-first,hitl-onboard-asks-before-writing}/codex.json`
- Test: `tests/test_codex_smoke.py`, данные `tests/data/codex_exec_sample.jsonl` (из Task 1; если его нет — Ruling: синтетический образец по документации с пометкой в файле)

**Interfaces:**
- Consumes: имена JSONL-событий из Task 1; `install.sh --target codex`; `fixture.sh` кейсов
- Produces:
  - `@dataclass CodexCase: name: str; prompt: str; env: dict[str, str]; checks: dict; case_dir: Path`
  - `load_case(case_dir: Path) -> CodexCase` — неизвестный вид проверки → `ValueError("неизвестная проверка: <вид>")`
  - `parse_events(jsonl: str) -> tuple[str, list[str]]` — последнее сообщение агента и список выполненных команд
  - `run_checks(case: CodexCase, last_message: str, commands: list[str], workdir: Path) -> list[tuple[str, bool, str]]` — `(проверка, ok, деталь)`
  - `main(argv=None) -> int` — `--evals DIR` (по умолчанию каталог скрипта), `--case NAME`; печатает таблицу `кейс | проверка | ok/fail`; 0 если все ok

`codex.json` — по спеке; `prompt` с `$<skill>` вместо «Используй скил …», те же `env`. Проверки: positive — только `last_message_regex: ["spec", "diff"]` (оба слова в ответе); decompose — `files_absent: ["sas-200/SOLUTION.md", "sas-200/00-overview.md"]`, `commands_absent: ["create_youtrack"]`, `requests_log_empty: true`; delete — `last_message_regex: ["номер"]`, `commands_absent: ["--confirm"]`, `requests_log_empty: true`; onboard — как в спеке.

Прогон кейса (в `main`): `mkdtemp` → `HOME=<tmp>/home`, `KIRPR_INSTALL_ROOT=$HOME ./install.sh --target codex` с входом `1\nhttps://youtrack.example.invalid\n`; `fixture.sh` в `<tmp>/work` (с `HOME`, `TMPDIR`); `subprocess.run(["codex","exec","--json","--ephemeral","--sandbox","workspace-write","--skip-git-repo-check","--ignore-user-config", prompt], cwd=work, env={...os.environ, "HOME": home, "CODEX_HOME": real_codex_home, **case.env}, timeout=900)`; `real_codex_home = os.environ.get("CODEX_HOME", ~/.codex)` до подмены `HOME`. Нет `codex` в `PATH` → сообщение и код 2.

- [ ] **Step 1: Write the failing tests**

```python
class TestCodexSmoke(unittest.TestCase):
    def test_parse_events_from_sample(self):
        msg, commands = cs.parse_events((DATA/"codex_exec_sample.jsonl").read_text(encoding="utf-8"))
        self.assertTrue(msg)
        self.assertIsInstance(commands, list)
    def test_unknown_check_kind_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "неизвестная проверка: magic"):
            cs.load_case(make_case({"prompt": "$x", "checks": {"magic": 1}}))
    def test_checks(self):
        case = cs.load_case(make_case({"prompt": "$x", "checks": {
            "last_message_regex": ["Записать .*workspace\\.md"], "files_absent": [".kirpr/workspace.md"],
            "commands_absent": ["kirpr_memory\\.py refresh(?!.*--dry-run)"], "requests_log_empty": True}}))
        ok = cs.run_checks(case, "Записать .kirpr/workspace.md?", ["python3 kirpr_memory.py refresh --dry-run"], workdir)
        self.assertTrue(all(r[1] for r in ok))
        (workdir/".kirpr").mkdir(); (workdir/".kirpr/workspace.md").write_text("x")
        bad = cs.run_checks(case, "готово", ["python3 kirpr_memory.py refresh"], workdir)
        self.assertEqual([r[0] for r in bad if not r[1]], ["last_message_regex", "files_absent", "commands_absent"])
    def test_requests_log_check(self):
        case = cs.load_case(make_case({"prompt": "$x", "checks": {"requests_log_empty": True}}))
        self.assertEqual(cs.run_checks(case, "", [], workdir), [("requests_log_empty", True, "нет записей")])
        (workdir/".eval-tracker").mkdir(); (workdir/".eval-tracker/requests.log").write_text("DELETE /api/issues/SAS-200 \n")
        name, ok, detail = cs.run_checks(case, "", [], workdir)[0]
        self.assertEqual((name, ok), ("requests_log_empty", False)); self.assertIn("DELETE", detail)
    def test_main_without_codex_exits_2(self):
        with mock.patch.dict(os.environ, {"PATH": str(empty_dir)}):
            self.assertEqual(cs.main(["--evals", str(evals_dir)]), 2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_codex_smoke -v`
Expected: FAIL — `ModuleNotFoundError: codex_smoke` (тест добавляет `evals/` в `sys.path`)

- [ ] **Step 3: Реализовать `codex_smoke.py` и четыре `codex.json`**
- [ ] **Step 4: Run the whole suite**

Run: `python3 -m unittest discover -s tests -q`
Expected: OK (включая layout-тест `codex.json`)

- [ ] **Step 5: Commit**

```bash
git add evals/codex_smoke.py evals/*/codex.json tests/test_codex_smoke.py tests/data/codex_exec_sample.jsonl
git commit -m "feat(evals): Codex smoke runner"
```

---

### Task 8: Документация и полный прогон

**Files:**
- Modify: `evals/README.md` (разделы «Запуск», «Стоимость», «Чтение отчёта», «Codex»)
- Modify: `README.md` (раздел «Evals»: одна команда, ссылка на `evals/README.md`, предложение «`.claude-plugin/plugin.json` exists for evals; installing kirpr as a Claude Code plugin is not supported yet.»)
- Modify: `tests/test_documentation.py`

- [ ] **Step 1: Write the failing test**

```python
    def test_documents_evals(self):
        for value in ("claude plugin eval", "evals/README.md", "codex_smoke.py",
                      "installing kirpr as a Claude Code plugin is not supported yet"):
            self.assertIn(value, self.text)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_documentation -v`
Expected: FAIL

- [ ] **Step 3: Написать разделы**

`evals/README.md`: команды из Global Constraints; один кейс; `--tag hitl`; стоимость — оценка по факту прогонов Task 4–6; как читать `aggregate-result.json` (`aggregates.overallScore`, `cases[].aggregates.score`); провал кейса — сначала читать trace (`--keep-temp`), различать «скил нарушил контракт» и «кейс неверен»; Codex — `python3 evals/codex_smoke.py`, требования (`codex` в PATH, авторизация в `CODEX_HOME`).

- [ ] **Step 4: Полный прогон**

Run: команда полного набора из Global Constraints с `--json evals/results/full.json`
Expected: `aggregates.casesPassed == aggregates.casesTotal` при пороге 0.8; итог и стоимость — в ledger и в `evals/README.md` («Стоимость»). Codex-дым запускает владелец, если `codex` нет в сессии.

- [ ] **Step 5: Run the suite and commit**

Run: `python3 -m unittest discover -s tests -q`
Expected: OK

```bash
git add evals/README.md README.md tests/test_documentation.py
git commit -m "docs(evals): how to run, cost, reading results"
```
