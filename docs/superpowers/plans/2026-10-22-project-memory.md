# Память проекта и уроки — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Дать скилам kirpr память о рабочем пространстве и репозиториях в git (`.kirpr/workspace.md`, `.kirpr/memory.md`) с уроками, которые пишутся только скриптом и только после подтверждения человека.

**Architecture:** Один stdlib-скрипт `kirpr/scripts/kirpr_memory.py` — единственная точка записи (команды `refresh`, `lesson add|amend`, `lint`, `stale`, все с `--dry-run`). Скилы `tasks-decompose`/`review`/`adapt` читают файлы памяти по правилу из `templates.md`; новый явный скил `kirpr-onboard` создаёт их. Модель никогда не редактирует файлы памяти напрямую.

**Tech Stack:** Python 3 stdlib (argparse, re, subprocess, tempfile, os.replace), unittest; bash-установщик (bash 3.2); Markdown-инструкции на английском с русским выводом.

**Spec:** `docs/superpowers/specs/2026-10-22-project-memory-design.md`

## Global Constraints

- Скрипт без зависимостей вне stdlib; совместим с Python 3.10+ (тесты гоняются на 3.10 и 3.14).
- Бюджет `memory.md`: 150 строк и 15 360 байт.
- Формат урока: `- [L-NNN] текст → как избежать (TASK-ID; YYYY-MM-DD; refs: a, b)`; `refs` необязателен; `NNN` — три цифры с ведущими нулями.
- Секции `memory.md` в фиксированном порядке: `## Как проверять`, `## Ловушки`, `## Уроки`.
- Запись в файлы памяти — только через временный файл в том же каталоге и `os.replace`.
- Все новые SKILL.md содержат строку `Everything addressed to the user and everything written to files is in Russian.`; инструкции по-английски; в канонических скилах запрещены `AskUserQuestion`, `TodoWrite`, `~/.claude/kirpr`, `.Codex` (тест `test_canonical_skills_have_no_platform_runtime_paths`).
- Коммиты — по одному на задачу, с префиксами как в истории репозитория (`feat(kirpr):`, `docs:`, `test:`).

## Review Focus

1. `memory.md` с секциями не по порядку или с пропущенной секцией — `lint` называет первую проблему и выходит с кодом 1, а `lesson add` отказывается писать (тест в Task 1 и Task 2).
2. Урок с «→» внутри текста refs или с запятой в пути — регулярка разбирает `refs` как список после последнего `refs:`; тест в Task 1.
3. `refresh` в каталоге, где нет ни одного git-репозитория, — печатает «сервисы не найдены», не создаёт файл; тест в Task 4.
4. `stale` для урока без `refs` и для `refs`, указывающих на каталог, — не помечается stale; тест в Task 3.
5. Повторный `lesson add` того же текста после `amend` — считается дублем уточнённого урока; тест в Task 2.

---

### Task 1: Парсер `memory.md` и команда `lint`

**Files:**
- Create: `kirpr/scripts/kirpr_memory.py`
- Create: `tests/test_kirpr_memory.py`
- Modify: `installer/lib.sh:26-29` (массив `KIRPR_SCRIPTS`)

**Interfaces:**
- Produces:
  - `SECTIONS = ("## Как проверять", "## Ловушки", "## Уроки")`, `MAX_LINES = 150`, `MAX_BYTES = 15360`
  - `@dataclass Lesson: number: int; text: str; task: str; date: str; refs: list[str]`
  - `LESSON_RE: re.Pattern` — разбирает строку урока; группы `number`, `text`, `task`, `date`, `refs` (refs — сырая строка или `None`)
  - `parse_memory(text: str) -> Memory` где `@dataclass Memory: title: str; sections: dict[str, list[str]]; lessons: list[Lesson]`; строки секции «Уроки», не прошедшие `LESSON_RE`, попадают в `sections["## Уроки"]` как есть и ловятся `lint`
  - `format_lesson(lesson: Lesson) -> str`
  - `lint_memory(text: str) -> list[str]` — список ошибок, пустой = ок
  - `write_atomic(path: Path, text: str) -> None`
  - `build_parser() -> argparse.ArgumentParser`, `main(argv=None) -> int`; подкоманда `lint --file F`: печатает ошибки по одной в строке, код 1 при ошибках, иначе `ok` и код 0

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_kirpr_memory.py
import os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "kirpr", "scripts"))
import kirpr_memory as km  # noqa: E402

GOOD = """# Память: scansrv

## Как проверять
- `make test`

## Ловушки
- `*_zenrpc.go` генерируется `make generate`

## Уроки
- [L-003] шаг ссылался на `Jobs().Summary`, в коде `Jobs().Info` → сверять сигнатуры с кодом (SAS-200; 2026-10-22; refs: pkg/rpc/scan.go, pkg/rpc/job.go)
- [L-004] задача без негативного сценария → добавлять «Проверить» с ошибкой (SAS-201; 2026-10-23)
"""

class TestParse(unittest.TestCase):
    def test_parses_lessons_with_and_without_refs(self):
        mem = km.parse_memory(GOOD)
        self.assertEqual(mem.title, "Память: scansrv")
        self.assertEqual([l.number for l in mem.lessons], [3, 4])
        self.assertEqual(mem.lessons[0].refs, ["pkg/rpc/scan.go", "pkg/rpc/job.go"])
        self.assertEqual(mem.lessons[0].task, "SAS-200")
        self.assertEqual(mem.lessons[1].refs, [])
        self.assertIn("→", mem.lessons[0].text)

    def test_format_roundtrip(self):
        mem = km.parse_memory(GOOD)
        self.assertEqual(km.format_lesson(mem.lessons[0]), GOOD.splitlines()[9])

class TestLint(unittest.TestCase):
    def test_good_file_has_no_errors(self):
        self.assertEqual(km.lint_memory(GOOD), [])

    def test_missing_section_and_wrong_order(self):
        errors = km.lint_memory(GOOD.replace("## Ловушки\n", ""))
        self.assertTrue(any("## Ловушки" in e for e in errors))
        swapped = GOOD.replace("## Как проверять", "## X").replace("## Ловушки", "## Как проверять").replace("## X", "## Ловушки")
        self.assertTrue(any("порядок" in e for e in km.lint_memory(swapped)))

    def test_bad_lesson_line_and_duplicate_id(self):
        errors = km.lint_memory(GOOD + "- [L-004] без стрелки и метаданных\n")
        self.assertTrue(any("L-004" in e and "дубл" in e for e in errors))
        self.assertTrue(any("формат" in e for e in errors))

    def test_budget(self):
        big = GOOD + "".join(f"- [L-{i:03d}] x → y (T-1; 2026-01-01)\n" for i in range(10, 170))
        errors = km.lint_memory(big)
        self.assertTrue(any("150" in e for e in errors))

class TestCli(unittest.TestCase):
    def test_lint_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "memory.md"
            p.write_text(GOOD, encoding="utf-8")
            self.assertEqual(km.main(["lint", "--file", str(p)]), 0)
            p.write_text(GOOD.replace("## Уроки\n", ""), encoding="utf-8")
            self.assertEqual(km.main(["lint", "--file", str(p)]), 1)

    def test_write_atomic_replaces_content(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "memory.md"
            p.write_text("old", encoding="utf-8")
            km.write_atomic(p, "new")
            self.assertEqual(p.read_text(encoding="utf-8"), "new")
            self.assertEqual(sorted(os.listdir(d)), ["memory.md"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_kirpr_memory -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'kirpr_memory'`

- [ ] **Step 3: Implement the parser, `lint_memory`, `write_atomic` and the CLI skeleton in `kirpr/scripts/kirpr_memory.py`**

`LESSON_RE`: `^- \[L-(?P<number>\d{3})\] (?P<text>.+?) \((?P<task>[A-Z][A-Z0-9]+-\d+); (?P<date>\d{4}-\d{2}-\d{2})(?:; refs: (?P<refs>[^)]+))?\)$`. `refs` режется по `, `. Сообщения `lint` по-русски: «нет секции `## Ловушки`», «нарушен порядок секций», «строка N: не соответствует формату урока», «L-004: дублирующийся id», «превышен бюджет: N строк из 150», «превышен бюджет: N байт из 15360». Остальные подкоманды регистрируются в Task 2–4; `build_parser` создаёт `subparsers` с `dest="command"`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_kirpr_memory -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Register the script in the installer and run the installer tests**

Add `kirpr_memory.py` to `KIRPR_SCRIPTS` in `installer/lib.sh`.
Run: `python3 -m unittest tests.test_installer -q`
Expected: OK

- [ ] **Step 6: Commit**

```bash
git add kirpr/scripts/kirpr_memory.py tests/test_kirpr_memory.py installer/lib.sh
git commit -m "feat(kirpr): memory file parser and lint"
```

---

### Task 2: `lesson add` и `lesson amend`

**Files:**
- Modify: `kirpr/scripts/kirpr_memory.py`
- Modify: `tests/test_kirpr_memory.py`

**Interfaces:**
- Consumes: `parse_memory`, `format_lesson`, `lint_memory`, `write_atomic`, `Lesson` (Task 1)
- Produces:
  - `normalize(text: str) -> str` — нижний регистр, только буквы/цифры/пробелы, схлопнутые пробелы
  - `find_duplicate(lessons: list[Lesson], text: str, refs: list[str]) -> Lesson | None` — совпадение `normalize(text)` или непустое пересечение `refs`
  - `add_lesson(path: Path, text: str, task: str, refs: list[str], today: str, dry_run: bool) -> tuple[int, str]` — `(exit_code, report)`; код 2 и отчёт «похоже на L-003 — уточните его: `lesson amend L-003`» при дубле; код 1 если `lint_memory` файла не пуст (ничего не пишется); иначе номер = max+1 (001 если уроков нет), строка добавляется в конец `## Уроки`
  - `amend_lesson(path: Path, number: int, text: str, today: str, dry_run: bool) -> tuple[int, str]` — код 1 если id не найден
  - CLI: `lesson add --file F --text T --task ID [--refs a,b] [--dry-run]`, `lesson amend L-NNN --file F --text T [--dry-run]`; отчёт `dry_run` начинается с `[dry-run]` и показывает итоговую строку урока

- [ ] **Step 1: Write the failing tests**

```python
class TestLessons(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.addCleanup(self.d.cleanup)
        self.p = Path(self.d.name) / "memory.md"; self.p.write_text(GOOD, encoding="utf-8")

    def test_add_assigns_next_number_and_appends(self):
        code, report = km.add_lesson(self.p, "нет сценария → добавить", "SAS-9", ["cmd/x.go"], "2026-10-24", dry_run=False)
        self.assertEqual(code, 0)
        self.assertIn("[L-005]", report)
        last = self.p.read_text(encoding="utf-8").rstrip().splitlines()[-1]
        self.assertEqual(last, "- [L-005] нет сценария → добавить (SAS-9; 2026-10-24; refs: cmd/x.go)")

    def test_dry_run_does_not_write(self):
        before = self.p.read_text(encoding="utf-8")
        code, report = km.add_lesson(self.p, "a → b", "SAS-9", [], "2026-10-24", dry_run=True)
        self.assertEqual((code, self.p.read_text(encoding="utf-8")), (0, before))
        self.assertTrue(report.startswith("[dry-run]"))

    def test_duplicate_by_text_and_by_refs(self):
        code, report = km.add_lesson(self.p, "Шаг ссылался на `Jobs().Summary`, в коде `Jobs().Info` → сверять сигнатуры с кодом", "SAS-9", [], "2026-10-24", dry_run=True)
        self.assertEqual(code, 2); self.assertIn("lesson amend L-003", report)
        code, _ = km.add_lesson(self.p, "другое → другое", "SAS-9", ["pkg/rpc/job.go"], "2026-10-24", dry_run=True)
        self.assertEqual(code, 2)

    def test_amend_replaces_text_and_date(self):
        code, _ = km.amend_lesson(self.p, 4, "новый текст → новый вывод", "2026-10-25", dry_run=False)
        self.assertEqual(code, 0)
        mem = km.parse_memory(self.p.read_text(encoding="utf-8"))
        self.assertEqual((mem.lessons[1].text, mem.lessons[1].date, mem.lessons[1].task), ("новый текст → новый вывод", "2026-10-25", "SAS-201"))
        code, _ = km.add_lesson(self.p, "новый текст → новый вывод", "SAS-9", [], "2026-10-26", dry_run=True)
        self.assertEqual(code, 2)

    def test_add_refuses_broken_file(self):
        self.p.write_text(GOOD.replace("## Ловушки\n", ""), encoding="utf-8")
        code, report = km.add_lesson(self.p, "a → b", "SAS-9", [], "2026-10-24", dry_run=False)
        self.assertEqual(code, 1); self.assertIn("## Ловушки", report)

    def test_cli_add_and_amend(self):
        self.assertEqual(km.main(["lesson", "add", "--file", str(self.p), "--text", "a → b", "--task", "SAS-9", "--refs", "x.go,y.go"]), 0)
        self.assertEqual(km.main(["lesson", "amend", "L-005", "--file", str(self.p), "--text", "c → d"]), 0)
        self.assertEqual(km.main(["lesson", "amend", "L-099", "--file", str(self.p), "--text", "c → d"]), 1)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_kirpr_memory.TestLessons -v`
Expected: FAIL — `AttributeError: module 'kirpr_memory' has no attribute 'add_lesson'`

- [ ] **Step 3: Implement `normalize`, `find_duplicate`, `add_lesson`, `amend_lesson` and the `lesson` subparser**

Дата по умолчанию в CLI — `datetime.date.today().isoformat()`. Запись — пересборка файла из `Memory` с теми же секциями, только строка урока добавлена/заменена; остальной текст не трогается.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_kirpr_memory -v`
Expected: PASS (13 tests)

- [ ] **Step 5: Commit**

```bash
git add kirpr/scripts/kirpr_memory.py tests/test_kirpr_memory.py
git commit -m "feat(kirpr): lesson add and amend with dedup"
```

---

### Task 3: `stale`

**Files:**
- Modify: `kirpr/scripts/kirpr_memory.py`
- Modify: `tests/test_kirpr_memory.py`

**Interfaces:**
- Consumes: `parse_memory`, `Lesson` (Task 1)
- Produces:
  - `stale_refs(path: Path, repo_root: Path) -> list[tuple[Lesson, str]]` — пары (урок, отсутствующий ref); пути считаются относительно `repo_root`; существующий файл или каталог — не stale; урок без `refs` пропускается
  - CLI: `stale --file F [--repo DIR]`; `DIR` по умолчанию — родитель каталога `.kirpr`, в котором лежит `F`; печатает `⚠ stale L-003: pkg/rpc/scan.go` по строке на пару, итог `N устаревших ссылок`; код 0 всегда (проверка, не гейт)

- [ ] **Step 1: Write the failing tests**

```python
class TestStale(unittest.TestCase):
    def test_reports_only_missing_paths(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / ".kirpr").mkdir(); (root / "pkg/rpc").mkdir(parents=True)
            (root / "pkg/rpc/scan.go").write_text("", encoding="utf-8")
            p = root / ".kirpr/memory.md"; p.write_text(GOOD, encoding="utf-8")
            result = km.stale_refs(p, root)
            self.assertEqual([(l.number, r) for l, r in result], [(3, "pkg/rpc/job.go")])
            self.assertEqual(km.main(["stale", "--file", str(p)]), 0)

    def test_directory_ref_is_not_stale(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / ".kirpr").mkdir(); (root / "pkg/rpc").mkdir(parents=True)
            text = GOOD.replace("refs: pkg/rpc/scan.go, pkg/rpc/job.go", "refs: pkg/rpc")
            p = root / ".kirpr/memory.md"; p.write_text(text, encoding="utf-8")
            self.assertEqual(km.stale_refs(p, root), [])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_kirpr_memory.TestStale -v`
Expected: FAIL — no attribute `stale_refs`

- [ ] **Step 3: Implement `stale_refs` and the `stale` subparser**

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_kirpr_memory -v`
Expected: PASS (15 tests)

- [ ] **Step 5: Commit**

```bash
git add kirpr/scripts/kirpr_memory.py tests/test_kirpr_memory.py
git commit -m "feat(kirpr): stale check for lesson refs"
```

---

### Task 4: `refresh` рабочего пространства и шаблоны

**Files:**
- Create: `kirpr/config/workspace.md.template`
- Create: `kirpr/config/memory.md.template`
- Modify: `kirpr/scripts/kirpr_memory.py`
- Modify: `installer/lib.sh:21-25` (массив `KIRPR_CONFIG_FILES`)
- Modify: `tests/test_kirpr_memory.py`

**Interfaces:**
- Consumes: `write_atomic` (Task 1)
- Produces:
  - `@dataclass Service: name: str; path: str; branch: str; tracker: str; role: str; status: str` — `status` ∈ `{"", "новый", "не найден"}`
  - `scan_workspace(root: Path) -> list[Service]` — для каждого подкаталога `root` с `.git`: `name` = имя каталога, `path` = `./<name>`, `branch` из `git symbolic-ref refs/remotes/origin/HEAD` без префикса `refs/remotes/origin/`, fallback `git rev-parse --abbrev-ref HEAD`; `tracker` = самый частый префикс `^([A-Z][A-Z0-9]+)-\d+` в `git log -50 --format=%s`, иначе `""`; `role=""`; отсортировано по имени
  - `parse_workspace(text: str) -> list[Service]` — читает таблицу; `status` восстанавливается из суффикса ` (новый)` / ` (не найден)` в колонке «Сервис»
  - `merge_services(scanned: list[Service], existing: list[Service]) -> list[Service]` — `role` и ручные строки из `existing` сохраняются; сервис только в `scanned` → `status="новый"`; только в `existing` → `status="не найден"`; у совпавших `status=""`
  - `render_workspace(name: str, services: list[Service], today: str) -> str` — по `workspace.md.template`; последняя строка `Обновлено скриптом: {today} (\`kirpr_memory.py refresh\`)`
  - `refresh_workspace(workspace: Path, today: str, dry_run: bool) -> tuple[int, str]` — пишет `<workspace>/.kirpr/workspace.md`; если сервисов нет и файла нет — код 1, отчёт «сервисы не найдены», файл не создаётся
  - `TEMPLATES_DIR` — `kirpr/config` относительно скрипта в репозитории, иначе `~/.local/share/kirpr/config`
  - CLI: `refresh [--workspace DIR] [--dry-run]`; `DIR` по умолчанию cwd

Шаблоны:

```markdown
# Рабочее пространство: {name}

| Сервис | Путь | Базовая ветка | Трекер | Роль |
|---|---|---|---|---|
{rows}

Обновлено скриптом: {today} (`kirpr_memory.py refresh`)
```

```markdown
# Память: {name}

## Как проверять
{check}

## Ловушки
{traps}

## Уроки
```

- [ ] **Step 1: Write the failing tests**

```python
import subprocess

def make_repo(root, name, branch="main", subjects=()):
    repo = root / name; repo.mkdir()
    def git(*a): subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=repo, check=True, capture_output=True)
    git("init", "-q", "-b", branch)
    for i, s in enumerate(subjects or ("init",)):
        (repo / f"f{i}").write_text("x", encoding="utf-8"); git("add", "."); git("commit", "-q", "-m", s)
    return repo

class TestRefresh(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory(); self.addCleanup(self.d.cleanup); self.root = Path(self.d.name)

    def test_scan_detects_branch_and_tracker(self):
        make_repo(self.root, "scansrv", "devel", ["SAS-1 a", "SAS-2 b", "WEB-3 c"])
        make_repo(self.root, "docs-only", "main")
        s = km.scan_workspace(self.root)
        self.assertEqual([(x.name, x.path, x.branch, x.tracker) for x in s],
                         [("docs-only", "./docs-only", "main", ""), ("scansrv", "./scansrv", "devel", "SAS")])

    def test_refresh_creates_and_merges(self):
        make_repo(self.root, "scansrv", "devel", ["SAS-1 a"])
        code, _ = km.refresh_workspace(self.root, "2026-10-24", dry_run=False)
        self.assertEqual(code, 0)
        p = self.root / ".kirpr/workspace.md"; text = p.read_text(encoding="utf-8")
        self.assertIn("| scansrv | ./scansrv | devel | SAS |  |", text)
        self.assertTrue(text.rstrip().endswith("Обновлено скриптом: 2026-10-24 (`kirpr_memory.py refresh`)"))
        text = text.replace("| scansrv | ./scansrv | devel | SAS |  |", "| scansrv | ./scansrv | devel | SAS | сканирование |\n| legacy | ../legacy | master | SAS | старый |")
        p.write_text(text, encoding="utf-8")
        make_repo(self.root, "upload", "main")
        km.refresh_workspace(self.root, "2026-10-25", dry_run=False)
        text = p.read_text(encoding="utf-8")
        self.assertIn("| scansrv | ./scansrv | devel | SAS | сканирование |", text)
        self.assertIn("| legacy (не найден) | ../legacy | master | SAS | старый |", text)
        self.assertIn("| upload (новый) | ./upload | main |  |  |", text)
        self.assertIn("2026-10-25", text)

    def test_empty_workspace(self):
        code, report = km.refresh_workspace(self.root, "2026-10-24", dry_run=False)
        self.assertEqual(code, 1); self.assertIn("сервисы не найдены", report)
        self.assertFalse((self.root / ".kirpr").exists())

    def test_cli_dry_run(self):
        make_repo(self.root, "scansrv")
        self.assertEqual(km.main(["refresh", "--workspace", str(self.root), "--dry-run"]), 0)
        self.assertFalse((self.root / ".kirpr/workspace.md").exists())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_kirpr_memory.TestRefresh -v`
Expected: FAIL — no attribute `scan_workspace`

- [ ] **Step 3: Create both templates in `kirpr/config/`, add them to `KIRPR_CONFIG_FILES`, implement the five functions and the `refresh` subparser**

Имя рабочего пространства — `workspace.name`. Статус в колонке «Сервис»: `name (новый)` / `name (не найден)`; при повторном `refresh` суффикс снимается, если сервис снова найден.

- [ ] **Step 4: Run all tests**

Run: `python3 -m unittest discover -s tests -q`
Expected: OK (218 + 19 новых)

- [ ] **Step 5: Commit**

```bash
git add kirpr/scripts/kirpr_memory.py tests/test_kirpr_memory.py kirpr/config/workspace.md.template kirpr/config/memory.md.template installer/lib.sh
git commit -m "feat(kirpr): workspace refresh and memory templates"
```

---

### Task 5: Правила памяти в `templates.md` и `.context.md`

**Files:**
- Modify: `kirpr/config/templates.md` (секции «Loading decomposition context», «.context.md template», новая «Project memory»)
- Modify: `tests/test_kirpr_config_consistency.py`

**Interfaces:**
- Produces (текст, на который ссылаются Task 6–8): секция `## Project memory` в `templates.md` с подсекциями `### Files` (пути, бюджет, что хранится и что нет), `### Lesson format` (формат из Global Constraints, правило «урок — ошибка процесса, не факт о коде»), `### Writing lessons (HITL)` (кандидаты → `lesson add --dry-run` → дифф → «да» по каждому файлу → запись; «нет» не переспрашивается); в «Loading decomposition context» — Option A и B: пункт «read `.kirpr/workspace.md` at the workspace root; for each affected service read `<path>/.kirpr/memory.md`; missing → one line suggesting `$kirpr-onboard` in Codex or `/kirpr:onboard` in Claude Code, continue»; в шаблоне `.context.md`, секция 7: строка `- **Версия памяти:** {дата из workspace.md или —}`

- [ ] **Step 1: Write the failing tests**

```python
class TestProjectMemory(unittest.TestCase):
    def setUp(self):
        self.text = (CONFIG / "templates.md").read_text(encoding="utf-8")

    def test_loading_section_mentions_memory_files(self):
        section = self.text.split("## Loading decomposition context", 1)[1].split("\n---", 1)[0]
        for name in ("workspace.md", "memory.md", "kirpr-onboard"):
            with self.subTest(name=name):
                self.assertIn(name, section)

    def test_memory_section_has_format_and_hitl(self):
        section = self.text.split("## Project memory", 1)[1].split("\n---", 1)[0]
        for needle in ("### Lesson format", "[L-NNN]", "### Writing lessons (HITL)", "--dry-run", "150"):
            with self.subTest(needle=needle):
                self.assertIn(needle, section)

    def test_context_template_has_memory_version(self):
        section = self.text.split("## .context.md template", 1)[1].split("\n---", 1)[0]
        self.assertIn("**Версия памяти:**", section)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_kirpr_config_consistency -v`
Expected: FAIL — `IndexError`/`AssertionError` on `## Project memory`

- [ ] **Step 3: Write the sections in `templates.md`**

Правило содержания — одной строкой в `### Files`: «Store only what cannot be derived from the code: test and lint commands, generators and what not to review, service ↔ tracker mapping, base branches, lessons. No architecture overviews, package lists, grep-able paths, secrets.»

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_kirpr_config_consistency -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add kirpr/config/templates.md tests/test_kirpr_config_consistency.py
git commit -m "docs(kirpr): project memory rules in templates"
```

---

### Task 6: Чтение памяти в `tasks-decompose`

**Files:**
- Modify: `kirpr/config/workflow.md` (Phase 1, Phase 2, Phase 5)
- Modify: `skills/kirpr-tasks-decompose/SKILL.md` (Initialization, Rules)
- Modify: `tests/test_kirpr_config_consistency.py`

**Interfaces:**
- Consumes: секция «Project memory» и правило загрузки (Task 5)

- [ ] **Step 1: Write the failing test**

```python
class TestDecomposeReadsMemory(unittest.TestCase):
    def test_workflow_phases_reference_memory(self):
        wf = (CONFIG / "workflow.md").read_text(encoding="utf-8")
        p1 = wf.split("## Phase 1", 1)[1].split("## Phase 2", 1)[0]
        p5 = wf.split("## Phase 5", 1)[1].split("## Phase 6", 1)[0]
        self.assertIn("workspace.md", p1); self.assertIn("memory.md", p1)
        self.assertIn("L-", p5)
        skill = (ROOT / "skills/kirpr-tasks-decompose/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Project memory", skill)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_kirpr_config_consistency.TestDecomposeReadsMemory -v`
Expected: FAIL

- [ ] **Step 3: Edit `workflow.md` and the skill**

Phase 1: новый пункт 0 — прочитать `.kirpr/workspace.md` по правилу из `templates.md` («Project memory»); пункт после фетча — прочитать `memory.md` сервисов на пути сценария по путям из таблицы. Phase 2: «Lessons and traps from memory are facts of research; cite them as `L-NNN`». Phase 5: пункт перед чеклистом — «no task repeats a situation recorded as a lesson L-NNN of its service; «Проверить» uses commands from `## Как проверять`, not invented ones». SKILL.md Initialization: пункт «Read the «Project memory» section of templates.md»; Rules: «Memory files are read, never edited by this skill».

- [ ] **Step 4: Run the full config and contract tests**

Run: `python3 -m unittest tests.test_kirpr_config_consistency tests.test_skill_contracts -q`
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add kirpr/config/workflow.md skills/kirpr-tasks-decompose/SKILL.md tests/test_kirpr_config_consistency.py
git commit -m "feat(kirpr): decompose reads project memory"
```

---

### Task 7: Память и запись уроков в `tasks-review` и `tasks-adapt`

**Files:**
- Modify: `skills/kirpr-tasks-review/SKILL.md` (Loading context, Phase 1, Phase 2 — категория 5, новая Phase 6)
- Modify: `skills/kirpr-tasks-adapt/SKILL.md` (Loading context, Phase C, новая Phase F)
- Modify: `tests/test_skill_contracts.py`

**Interfaces:**
- Consumes: секция «Project memory» (Task 5), CLI `lesson add --dry-run` / `lesson amend` (Task 2), путь скрипта `python3 ~/.local/share/kirpr/scripts/kirpr_memory.py`

- [ ] **Step 1: Write the failing test**

```python
class TestMemoryWriters(unittest.TestCase):
    def test_review_and_adapt_write_lessons_via_script_with_hitl(self):
        for name, phase in (("kirpr-tasks-review", "Phase 6"), ("kirpr-tasks-adapt", "Phase F")):
            text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            with self.subTest(skill=name):
                self.assertIn(phase, text)
                self.assertIn("kirpr_memory.py lesson add", text)
                self.assertIn("--dry-run", text)
                self.assertIn("Do not write a lesson without", text)
                self.assertNotIn("Edit memory.md", text)

    def test_review_has_lessons_category(self):
        text = (ROOT / "skills/kirpr-tasks-review/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("#### Category 5: Lessons", text)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_skill_contracts.TestMemoryWriters -v`
Expected: FAIL

- [ ] **Step 3: Edit both skills**

`tasks-review`: Loading context — после базового контекста прочитать `memory.md` сервисов в scope; Category 5 «Lessons»: чекбокс «the task does not repeat a lesson L-NNN of its service», находка — `Важно` с id; Phase 6 «Lessons (HITL)»: триггеры — находки категорий 2/3 с расхождением с кодом или файл со score < 8 после Phase 3.5; 0–3 кандидата; для каждого `python3 ~/.local/share/kirpr/scripts/kirpr_memory.py lesson add --file <svc>/.kirpr/memory.md --text "..." --task {номер} --refs ... --dry-run` (код 2 → показать предложенный `amend`); показать дифф по файлам; вопрос «Записать уроки в {файл}?» по одному файлу, `да`/`нет`; «нет» — не переспрашивать. Правило: «Do not write a lesson without the user's explicit «да»».
`tasks-adapt`: Phase C читает `memory.md` только сервисов из зоны влияния; Phase F «Lessons (HITL)» — триггер: выбран вариант 2 или 3 и причина — ошибка декомпозиции, а не новый ввод; дальше как в review. Секция 7 `.context.md` обновляет «Версия памяти».

- [ ] **Step 4: Run contract tests**

Run: `python3 -m unittest tests.test_skill_contracts -q`
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add skills/kirpr-tasks-review/SKILL.md skills/kirpr-tasks-adapt/SKILL.md tests/test_skill_contracts.py
git commit -m "feat(kirpr): review and adapt record lessons with confirmation"
```

---

### Task 8: Скил `kirpr-onboard`

**Files:**
- Create: `skills/kirpr-onboard/SKILL.md`
- Create: `skills/kirpr-onboard/agents/openai.yaml`
- Create: `commands/kirpr/onboard.md`
- Modify: `installer/lib.sh:6-14` (`KIRPR_SKILLS`, `KIRPR_COMMANDS`)
- Modify: `tests/test_skill_contracts.py` (`ALL_SKILLS`, `TestDecompositionSkills.CASES`), `tests/test_installer.py` (`ALL_SKILLS`), `tests/test_kirpr_config_consistency.py` (SKILLS glob уже `kirpr-tasks-*` — добавить onboard в `TEXTS`)

**Interfaces:**
- Consumes: CLI `refresh --dry-run`, `refresh` (Task 4); шаблон `memory.md.template`; секция «Project memory» (Task 5)
- Produces: frontmatter `name: kirpr-onboard`, `description: "Use only when explicitly invoked to create or update kirpr project memory: workspace map and per-repository memory files."`; `openai.yaml` по образцу `skills/kirpr-tasks-decompose/agents/openai.yaml`; адаптер по образцу `commands/kirpr/tasks-decompose.md`

- [ ] **Step 1: Write the failing tests**

Добавить `"kirpr-onboard"` в `ALL_SKILLS` обоих тестов и `("onboard", "kirpr-onboard")` в `TestDecompositionSkills.CASES`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_skill_contracts tests.test_installer -q`
Expected: FAIL — `test_exact_skill_set`, `assert_explicit_skill`, установщик — «Missing skill»

- [ ] **Step 3: Write the skill, `openai.yaml`, the adapter; add to `KIRPR_SKILLS` and `KIRPR_COMMANDS`**

SKILL.md фазы: Phase 1 — `refresh --dry-run` из текущего каталога, показать таблицу, спросить роль каждого сервиса по одному (пустой ответ — оставить пустой), затем `refresh` и дописать роли через показ файла целиком и «да»; Phase 2 — для каждого сервиса без `.kirpr/memory.md`: извлечь кандидаты «Как проверять» из `Makefile` (цели `test`, `lint`, `generate`), `go.mod`, `.gitlab-ci.yml`/`.github/workflows`; не больше трёх вопросов на сервис про ловушки (генераторы и что не ревьюить, порядок генерации, тесты с БД); Phase 3 — показать каждый файл целиком, записать из `memory.md.template` после «да» по файлу, напомнить закоммитить `.kirpr/`. Повторный вызов — только новые сервисы и пустые секции. Правила: один вопрос за раз; не спрашивать про инфраструктуру; не писать без «да»; уроки руками не добавлять.

- [ ] **Step 4: Run the whole suite**

Run: `python3 -m unittest discover -s tests -q`
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add skills/kirpr-onboard commands/kirpr/onboard.md installer/lib.sh tests/test_skill_contracts.py tests/test_installer.py tests/test_kirpr_config_consistency.py
git commit -m "feat(kirpr): onboard skill for project memory"
```

---

### Task 9: README

**Files:**
- Modify: `README.md` (таблица «Task decomposition», новый раздел «Project memory» после «Tracker configuration», «Repository layout»)
- Modify: `tests/test_documentation.py`

- [ ] **Step 1: Write the failing test**

```python
    def test_documents_project_memory(self):
        for value in ("/kirpr:onboard", "$kirpr-onboard", ".kirpr/workspace.md", ".kirpr/memory.md", "kirpr_memory.py"):
            with self.subTest(value=value):
                self.assertIn(value, self.text)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest tests.test_documentation -v`
Expected: FAIL

- [ ] **Step 3: Write the README section**

Содержание: где лежат файлы и что они в git; что хранится и что нет (одна строка правила содержания); бюджет 150 строк; команды `refresh`, `lesson add/amend`, `lint`, `stale` с одной строкой каждая; уроки пишутся только после подтверждения. Строка `/kirpr:onboard` / `$kirpr-onboard` — в таблицу «Task decomposition».

- [ ] **Step 4: Run the whole suite**

Run: `python3 -m unittest discover -s tests -q`
Expected: OK

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_documentation.py
git commit -m "docs: project memory section"
```
