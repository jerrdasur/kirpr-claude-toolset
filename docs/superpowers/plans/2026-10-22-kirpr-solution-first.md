# kirpr solution-first — план реализации (этап A)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Довести незакоммиченные правки solution-first декомпозиции до состояния, где `decompose`, `review`, `adapt`, `push`, конфиг и тесты описывают один формат, и закрепить это тестами.

**Architecture:** Источник правды для формата — `kirpr/config/templates.md`; четыре скила `kirpr-tasks-*` ссылаются на него. Новый тест на консистентность ловит остатки старого формата и рассинхрон номеров фаз. Публикация `SOLUTION.md` в родительскую задачу живёт целиком в `create_youtrack.py` (опция `--solution-file`, идемпотентность через `.created.json`).

**Tech Stack:** Markdown-инструкции (русский), Python 3 stdlib (`argparse`, `json`, `urllib`), `unittest`.

**Spec:** `docs/superpowers/specs/2026-10-22-kirpr-solution-first-design.md`

**Этап B (перевод на английский)** в этот план не входит: по спеке он начинается после мержа этапа A и получает отдельный план.

## Global Constraints

- Все инструкции и литералы остаются на русском (перевод — этап B).
- Термины: «задача» — `NN-service.md`; «родительская задача» — трекерная задача, которую декомпозируем; «дочерние задачи в трекере» — то, что уже висит под родителем. Слово «подзадача» в `skills/kirpr-tasks-*` и `kirpr/config` не используется.
- Правило записи файлов (одна формулировка в `templates.md` и SKILL декомпозиции): «Не записывай файл, не показав его содержимое пользователю. Для `source.md`, `research.md` и `SOLUTION.md` достаточно показа; для файлов Фазы 6 нужно явное "да"».
- В `workflow.md` и `templates.md` нет упоминаний Nomad, SMD, `.sarif`, скриптов сканеров и правила «прямой вызов вместо транзита параметров»; иллюстрации с ними — только в `style-examples.md`.
- `manage_youtrack.py` и формат `create-plan.json` не меняются.
- Существующие 16 тестов `test_skill_contracts` + `test_documentation` и все тесты `test_create_youtrack` остаются зелёными. Запуск: `python3 -m unittest discover -s tests -v` из корня репо.
- Ветка `kirpr-solution-first`; промежуточные коммиты `wip:`; при завершении — squash в один коммит `refactor(kirpr): solution-first decomposition`. Коммит из сессии Cowork требует разрешения на удаление в папке (lock-файлы git); без него коммитит владелец.

## Review Focus

1. `--solution-file` указывает на отсутствующий файл → `PlanError` с путём, ничего не создано (тест в Task 5).
2. `.created.json` старого формата (только `key → issue`) + `--solution-file` → решение публикуется, поле добавляется, задачи не дублируются (тест в Task 5).
3. Повторный `push` после `adapt` с изменённым `SOLUTION.md` → публикация пропускается, в отчёте строка «уже опубликовано {дата}» — это задокументированное поведение, не баг (тест в Task 5, текст в `push` SKILL в Task 6).
4. Ключ задачи в плане совпадает с зарезервированным `solution_comment` → `PlanError` (тест в Task 5).
5. `review` получает декомпозицию старого формата (`XX-Y-name.md`, оценки) → скил не должен падать; в Task 3 добавляется инструкция «если файлы не соответствуют шаблонам `templates.md`, сообщи и предложи `adapt`», тестом не покрывается.

---

### Task 1: Тест на консистентность конфига и скилов

**Files:**
- Create: `tests/test_kirpr_config_consistency.py`

**Interfaces:**
- Produces: тест-класс `TestNoLegacyFormat`, `TestPhaseReferences`, `TestContextLoading`; остальные задачи делают его зелёным.

- [ ] **Step 1: Написать тест**

```python
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "kirpr" / "config"
SKILLS = sorted((ROOT / "skills").glob("kirpr-tasks-*/SKILL.md"))
TEXTS = [CONFIG / n for n in ("workflow.md", "templates.md")] + SKILLS

LEGACY = [
    r"XX-Y", r"~\dч", r"<= 4 час", r"Параллельные потоки",
    r"граф зависимостей", r"\d\d-\d-[a-z-]+\.md",
]


class TestNoLegacyFormat(unittest.TestCase):
    def test_no_legacy_markers(self):
        for path in TEXTS:
            text = path.read_text(encoding="utf-8")
            for pat in LEGACY:
                with self.subTest(file=path.name, marker=pat):
                    self.assertIsNone(re.search(pat, text, re.IGNORECASE))


class TestPhaseReferences(unittest.TestCase):
    def test_skill_phase_numbers_exist_in_workflow(self):
        workflow = (CONFIG / "workflow.md").read_text(encoding="utf-8")
        defined = set(re.findall(r"^## Фаза (\d+)", workflow, re.MULTILINE))
        referenced = set()
        for path in SKILLS + [CONFIG / "templates.md"]:
            referenced |= set(re.findall(r"Фаз[аы] (\d+)", path.read_text(encoding="utf-8")))
        self.assertTrue(referenced <= defined, referenced - defined)


class TestContextLoading(unittest.TestCase):
    def test_loading_section_mentions_all_artifacts(self):
        text = (CONFIG / "templates.md").read_text(encoding="utf-8")
        section = text.split("## Загрузка контекста декомпозиции", 1)[1].split("\n---", 1)[0]
        for name in ("source.md", "research.md", "SOLUTION.md", "00-overview.md"):
            with self.subTest(name=name):
                self.assertIn(name, section)
```

Примечание: `review`, `adapt`, `push` содержат собственные «Фаза 1…6» — это их внутренние фазы, а не фазы workflow. `TestPhaseReferences` должен игнорировать заголовки `### Фаза N` и `## Фаза N` внутри самих SKILL.md: перед поиском удалить строки, начинающиеся с `#`. Добавить это в тест.

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python3 -m unittest tests.test_kirpr_config_consistency -v`
Expected: FAIL в `test_no_legacy_markers` минимум для `kirpr-tasks-adapt/SKILL.md` (`03-1-feed-listing.md`, `~3ч`, «граф зависимостей») и `kirpr-tasks-review/SKILL.md` (`02-1-domain-model.md`, «Параллельные потоки»). Остальные два теста — PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_kirpr_config_consistency.py
git commit -m "wip: consistency test for kirpr decomposition format"
```

---

### Task 2: `templates.md`, `workflow.md`, SKILL декомпозиции — терминология, правило записи, домен

**Files:**
- Modify: `kirpr/config/templates.md`
- Modify: `kirpr/config/workflow.md`
- Modify: `kirpr/config/style-examples.md` (только добавление)
- Modify: `skills/kirpr-tasks-decompose/SKILL.md`

**Interfaces:**
- Produces: секции `templates.md`, на которые ссылаются Task 3–4: «Критические правила», «Загрузка контекста декомпозиции», «Шаблон задачи NN-service.md», «Чеклист верификации», «Рубрика Quality Scoring».

- [ ] **Step 1: Терминология в `templates.md`**

Заменить все вхождения «подзадач*» (строки 8, 10, 40, 64, 127, 141–142, 171, 251–252, 263, 295 на момент написания): «Шаблон подзадачи NN-service.md» → «Шаблон задачи NN-service.md», «Правила для содержимого подзадач» → «…задач», «существующие подзадачи» (в `research.md`) → «дочерние задачи в трекере», «{N} подзадач по сервисам» → «{N} задач по сервисам». В `workflow.md`: строка 3 — «не список задач, а проверенное техническое решение, из которого задачи следуют сами»; Фаза 1 п. 4 и 6 — «дочерние задачи в трекере». В SKILL декомпозиции строка 8 — «…и задачи по сервисам. Задачи — следствие решения…».

- [ ] **Step 2: Единое правило записи файлов**

В `templates.md`, критическое правило «Покажи diff перед записью» заменить на: «**Покажи перед записью.** Не записывай файл, не показав его содержимое пользователю. Для `source.md`, `research.md` и `SOLUTION.md` достаточно показа; для файлов Фазы 6 нужно явное "да"». В SKILL декомпозиции правило «Не генерируй файлы до Фазы 6, кроме…» заменить на ту же формулировку (одно предложение, ссылкой: «Правило записи файлов — в `templates.md`, критические правила»).

- [ ] **Step 3: Домен из правил в примеры**

В `workflow.md`: Фаза 2a — «инфраструктурные спеки (job-спеки оркестратора, CI, правила алертинга), генерируемые артефакты (клиенты, SMD)» → «инфраструктурные спеки (оркестрация, CI, алертинг), генерируемые артефакты (клиенты, схемы API)»; Фаза 4b второй пункт → «Границы ответственности, принятые пользователем, не нарушаются: механизм, принадлежащий другому слою (повторы, оркестрация), не дублируется и не обходится, пока есть решение внутри своего слоя»; из третьего пункта 4b удалить предложение «Данные берутся прямым вызовом…». В `templates.md`: пример зависимости «`1 → 2` — клиент генерируется из SMD сервера» → «`1 → 2` — клиент генерируется из схемы сервера»; пример имени файла `03-devops-nomad.md` → `03-devops.md`. В `style-examples.md` добавить в конец раздел «## Пример 5: границы слоёв» с двумя строками из удалённого: «Повторы остаются за Nomad; скрипты сканеров не меняются» как иллюстрация правила 4b.

- [ ] **Step 4: Проверка**

Run: `grep -niE "nomad|smd|sarif|сканер|подзадач" kirpr/config/workflow.md kirpr/config/templates.md skills/kirpr-tasks-decompose/SKILL.md`
Expected: пусто.
Run: `python3 -m unittest tests.test_kirpr_config_consistency tests.test_skill_contracts -v`
Expected: `TestPhaseReferences`, `TestContextLoading`, все `test_skill_contracts` — PASS; `test_no_legacy_markers` всё ещё FAIL только по `adapt` и `review`.

- [ ] **Step 5: Commit**

```bash
git add kirpr/config skills/kirpr-tasks-decompose/SKILL.md
git commit -m "wip: unify terminology, write rule and remove domain from kirpr config"
```

---

### Task 3: `kirpr-tasks-review` под новые артефакты

**Files:**
- Modify: `skills/kirpr-tasks-review/SKILL.md`

**Interfaces:**
- Consumes: из `templates.md` — секция «Чеклист верификации» (7 пунктов), «Рубрика Quality Scoring» (К1–К5), «Загрузка контекста декомпозиции».
- Produces: формат сводного отчёта со строкой «Решение: …», на который ссылается `adapt` (Task 4) в секции 5.5 `.context.md`.

- [ ] **Step 1: Инициализация и scope**

Пример аргумента: `SAS-200 01-scansrv.md`. «Review конкретной подзадачи» → «review одной задачи». Загрузка: при scope = один файл читать его, `SOLUTION.md` и строку его зависимостей из таблицы `00-overview.md` (не «из графа»). Добавить правило: «Если файлы директории не соответствуют шаблонам `templates.md` (нет `SOLUTION.md`, заголовки вида `## Задача X.Y`), сообщи об этом и предложи `$kirpr-tasks-adapt` в Codex или `/kirpr:tasks-adapt` в Claude Code; review не выполняй».

- [ ] **Step 2: Фаза 1.5 — проверка `SOLUTION.md`**

Между Фазой 1 и Фазой 2 добавить «### Фаза 1.5: Проверка решения»: пройти чеклист из `templates.md` (секция «Чеклист верификации») по `SOLUTION.md` и `research.md`; результат — одна строка для сводного отчёта: `Решение: пройдено` или `Решение: не пройдено — пункты {номера}`.

- [ ] **Step 3: Четыре категории**

Переписать Фазу 2 по таблице спеки (раздел «`kirpr-tasks-review`»): Категория 1 «Неоднозначности» — однозначность шагов и условий «Проверить», без пункта про код-примеры; Категория 2 «Противоречия» — между задачами, `SOLUTION.md` и `00-overview.md`, зависимости только технические, нет дублирования работы; Категория 3 «Пропуски» — все изменения из `SOLUTION.md` покрыты задачами, в «Проверить» есть отрицательные сценарии, непроверенное помечено «подтвердить на dev», интеграции между сервисами учтены; Категория 4 «Границы и риски» — один сервис — один MR, внешние зависимости и другие команды, bottleneck в порядке деплоя, технические риски. Пункты про задачи на тесты/миграции/ADR, оценки, параллельные потоки, граф — удалить.

- [ ] **Step 4: Примеры отчётов**

В таблице scores (Фаза 2.5) и сводном отчёте (Фаза 3) заменить имена на `01-scansrv.md`, `02-upload-callback.md`, `03-devops.md`; замечания — согласованные с К1–К5: «К3: в "Проверить" нет отрицательного сценария», «К2: не названо, что делать со сканом в статусе `canceled`», «К5: RPC `scan.ReportMissing` нет в `scansrv/api`», «К1: шаг "обработать ошибку" без условия». В сводный отчёт добавить строку `Решение: …` после «Общий score». Пример `[00-overview.md] Задача 4.2 зависит от 4.1, но в графе…` → `[00-overview.md] 02-upload-callback зависит от 01-scansrv (клиент из схемы), но в таблице зависимость не указана`.

- [ ] **Step 5: Проверка**

Run: `python3 -m unittest tests.test_kirpr_config_consistency -v`
Expected: `test_no_legacy_markers` FAIL только по `kirpr-tasks-adapt/SKILL.md`.
Run: `grep -nE "подзадач|оценк|SQL-прим|критери[яй] готовности" skills/kirpr-tasks-review/SKILL.md`
Expected: пусто.

- [ ] **Step 6: Commit**

```bash
git add skills/kirpr-tasks-review/SKILL.md
git commit -m "wip: rewrite kirpr-tasks-review for solution-first artifacts"
```

---

### Task 4: `kirpr-tasks-adapt` под новые артефакты

**Files:**
- Modify: `skills/kirpr-tasks-adapt/SKILL.md`

**Interfaces:**
- Consumes: `templates.md` — «Загрузка контекста декомпозиции», «Чеклист верификации», шаблон `.context.md` (секции 0, 3, 4, 5, 7); `workflow.md` — пункт 4e «Чистка по предложениям».

- [ ] **Step 1: Фаза A**

Резюме: «проблема (из `.context.md` секция 0), механизм, список задач по сервисам, дата последней декомпозиции/адаптации». Варианты «что изменилось»: 1) обновилось описание в трекере; 2) изменились требования; 3) **изменилось решение** (механизм или изменения по сервису); 4) добавить/удалить/объединить задачи; 5) изменился порядок деплоя или технические зависимости; 6) другое. Удалить «переоценить».

- [ ] **Step 2: Фаза B**

Если выбран вариант 3 — зона влияния включает `SOLUTION.md` и `research.md`, и для них действует: «Правка `SOLUTION.md` проходит чистку по предложениям (`workflow.md`, 4e); отвергнутый прежний вариант фиксируется в `research.md` одной строкой с фактом». Пример таблицы влияния:

```
[обновить]        SOLUTION.md — изменён механизм: исход передаётся RPC, а не exit-кодом
[обновить]        01-scansrv.md — добавлен шаг с новым RPC
[обновить]        00-overview.md — порядок деплоя: scansrv раньше upload-callback
[новый]           03-devops.md — правило алертинга на новый статус
[удалить]         02-upload-callback.md — изменение ушло в scansrv
[без изменений]   research.md, source.md
```

- [ ] **Step 3: Фаза E**

Пример итогового diff без часов и графа:

```
[ОБНОВИТЬ] SOLUTION.md
  - scansrv: добавлен RPC `scan.ScanReportMissing`
[ОБНОВИТЬ] 01-scansrv.md
  - Шаг 1: новый RPC; «Проверить»: + сценарий со статусом `canceled`
[ОБНОВИТЬ] 00-overview.md
  - Порядок: 01-scansrv → 02-upload-callback
[СОЗДАТЬ] 03-devops.md
  - devops: алерт на `lastError` без смены статуса
[УДАЛИТЬ] 02-upload-callback.md
```

Шаг 3 «Обнови `00-overview.md` (граф, карта файлов, итоги)» → «(таблица задач, зависимости)». Шаг 4: «Секция 3: добавь новые решения и строку "Отвергнуто: {вариант} — {факт}"». Остальные секции `.context.md` — как сейчас.

- [ ] **Step 4: Терминология**

Заменить «подзадач*» (строки 22, 35, 49, 71) на «задач*».

- [ ] **Step 5: Проверка**

Run: `python3 -m unittest tests.test_kirpr_config_consistency tests.test_skill_contracts -v`
Expected: все PASS.

- [ ] **Step 6: Commit**

```bash
git add skills/kirpr-tasks-adapt/SKILL.md
git commit -m "wip: rewrite kirpr-tasks-adapt for solution-first artifacts"
```

---

### Task 5: `create_youtrack.py --solution-file`

**Files:**
- Modify: `kirpr/scripts/create_youtrack.py`
- Test: `tests/test_create_youtrack.py`

**Interfaces:**
- Produces:
  - `SOLUTION_KEY = "solution_comment"` — зарезервированный ключ в `.created.json`, значение — дата `YYYY-MM-DD`.
  - `load_solution(path: str) -> str` — текст файла; `PlanError(f"Solution file not found: {path}")` при отсутствии.
  - `YouTrackClient.add_comment(issue_id: str, text: str) -> None` — `POST /api/issues/{issue_id}/comments`, body `{"text": text}`.
  - `run(plan_path, dry_run, client=None, mapping_path=None, solution_path=None, today=None) -> str`; `today` — строка даты для тестов, по умолчанию `datetime.date.today().isoformat()`.
  - Текст комментария: `f"## Техническое решение, {today}\n\n{solution_text}"`.
  - CLI: `--solution-file PATH` (необязательный).
  - `validate_plan` дополнительно бросает `PlanError`, если `t["key"] == SOLUTION_KEY`.
  - Dry-run при `solution_path`: секция `## Решение в родителя` со строкой `- будет опубликовано комментарием к {parent}` или `- уже опубликовано ({date})`.
  - Отчёт при `solution_path`: строка `Решение опубликовано комментарием к {parent}.` или `Решение уже было опубликовано ({date}).`
  - В `render_report` «Итого» считает `len(plan["tasks"])`, не `len(mapping)`.

- [ ] **Step 1: Тесты клиента и валидации**

В `TestYouTrackClient`:

```python
def test_add_comment_posts_text(self):
    tr = FakeTransport([(200, {})])
    c = cy.YouTrackClient("https://yt.example.com", "tok", transport=tr)
    c.add_comment("SAS-200", "hello")
    call = tr.calls[0]
    self.assertEqual(call["method"], "POST")
    self.assertTrue(call["url"].endswith("/api/issues/SAS-200/comments"))
    self.assertEqual(json.loads(call["data"]), {"text": "hello"})
```

В `TestValidatePlan`:

```python
def test_reserved_key_raises(self):
    tasks = [{"key": cy.SOLUTION_KEY, "summary": "s", "description": "d"}]
    with self.assertRaises(cy.PlanError):
        cy.validate_plan(make_plan(tasks=tasks, edges=[]))
```

- [ ] **Step 2: Тесты `run`**

В `FakeClient` добавить `self.comments = []` и `def add_comment(self, issue_id, text): self.comments.append((issue_id, text))`. В `TestRun` добавить помощник `_write_solution(d, text="mechanism")`, пишущий `SOLUTION.md`, и тесты:

```python
def test_solution_posted_and_recorded(self):
    # run с solution_path и today="2026-10-22" → fc.comments == [("SAS-200", "## Техническое решение, 2026-10-22\n\nmechanism")],
    # mapping[cy.SOLUTION_KEY] == "2026-10-22", "Решение опубликовано" in out

def test_solution_skipped_when_recorded(self):
    # mapping заранее содержит SOLUTION_KEY: "2026-10-01"; после run fc.comments == [], "уже было опубликовано (2026-10-01)" in out

def test_solution_with_legacy_mapping(self):
    # mapping = {"01-schema": "SAS-201"} (старый формат); после run создана только 02-model, комментарий один, SOLUTION_KEY записан

def test_solution_dry_run_shows_step_without_writes(self):
    # dry_run=True с solution_path → "будет опубликовано комментарием к SAS-200" in out, fc.comments == []

def test_missing_solution_file_raises_before_writes(self):
    # solution_path на несуществующий файл → PlanError, fc.created == []
```

Исправить `test_full_run_creates_and_links`: `set(mapping.keys())` остаётся `{"01-schema", "02-model"}` (без `solution_path` ключ не добавляется) — тест не меняется, это проверка.

- [ ] **Step 3: Запустить — убедиться, что падает**

Run: `python3 -m unittest tests.test_create_youtrack -v`
Expected: 7 новых тестов FAIL (`AttributeError`/`TypeError`), остальные PASS.

- [ ] **Step 4: Реализация**

Порядок в `run`: `load_solution` вызывается сразу после `validate_plan` (до любых сетевых вызовов); публикация — после Pass 2b, перед `render_report`; `save_mapping` сразу после `add_comment`. Pass 1 и 2 итерируют только `plan["tasks"]`, поэтому зарезервированный ключ в `mapping` им не мешает. `render_dry_run` и `render_report` получают дополнительные аргументы `solution_state: str | None` (`None` — опция не передана; иначе `"pending"` или дата).

- [ ] **Step 5: Запустить — убедиться, что проходит**

Run: `python3 -m unittest tests.test_create_youtrack -v`
Expected: все PASS.

- [ ] **Step 6: Commit**

```bash
git add kirpr/scripts/create_youtrack.py tests/test_create_youtrack.py
git commit -m "wip: publish SOLUTION.md to parent issue from create_youtrack"
```

---

### Task 6: `kirpr-tasks-push` — description, `--solution-file`, примеры

**Files:**
- Modify: `skills/kirpr-tasks-push/SKILL.md`

**Interfaces:**
- Consumes: из Task 5 — опция `--solution-file`, тексты dry-run и отчёта.

- [ ] **Step 1: Фаза 1**

Строка 8: «создаёт подзадачи в YouTrack» → «создаёт задачи в YouTrack под родительской». П. 2: «`NN-service.md` — задачи». П. 3: «Тело файла без заголовка плюс последняя строка `Решение: см. {parent}` → `description`» (где `{parent}` — номер родительской задачи из аргументов).

- [ ] **Step 2: Фаза 2 и 3**

Пример `key` → `01-scansrv`; «по одному объекту на файл задачи». Команды dry-run и создания получают `--solution-file sas-200/SOLUTION.md`. В Фазе 3 добавить: «Dry-run покажет и шаг публикации решения комментарием к родительской задаче». «Явно покажи граф зависимостей» → «Явно покажи зависимости».

- [ ] **Step 3: Фаза 4–6 и правила**

Гейт Фазы 4: «Создаю N задач в проекте {PROJECT} с иерархией и зависимостями и публикую решение комментарием к {parent}?». В Фазе 6 добавить: «Решение публикуется один раз; при повторном вызове скрипт сообщит "уже было опубликовано". После `$kirpr-tasks-adapt` в Codex или `/kirpr:tasks-adapt` в Claude Code обновляй родительскую задачу через `$kirpr-task-update` / `/kirpr:task-update` с `--comment`».

- [ ] **Step 4: Проверка**

Run: `python3 -m unittest discover -s tests -v`
Expected: все PASS (включая `test_claude_commands_are_thin_adapters`, `test_no_legacy_markers`).
Run: `grep -n "подзадач\|02-1-domain" skills/kirpr-tasks-push/SKILL.md`
Expected: пусто.

- [ ] **Step 5: Commit**

```bash
git add skills/kirpr-tasks-push/SKILL.md
git commit -m "wip: push publishes SOLUTION.md and links tasks to it"
```

---

### Task 7: Smoke на реальной задаче и финальный коммит

**Files:**
- Нет новых; возможны точечные правки по итогам smoke в любом файле Task 2–6.

- [ ] **Step 1: Установить ветку локально**

Run: `./install.sh --target all` (или команда из README для локальной установки).
Expected: в `~/.local/share/kirpr/config/` лежат новые `workflow.md`, `templates.md`, `style-examples.md`.

- [ ] **Step 2: Прогнать `decompose`**

В репозитории проекта с настроенным `~/.config/kirpr/tracker.md`: `$kirpr-tasks-decompose {реальный номер}` (Codex) или `/kirpr:tasks-decompose {номер}` (Claude Code). Пройти все 6 фаз. Проверить: директория содержит `source.md`, `research.md`, `SOLUTION.md`, `00-overview.md`, `NN-service.md`, `.context.md`; заголовки задач — `# {сервис}: {название}`; в `SOLUTION.md` нет разделов «Принцип/Эффект/Что не меняем».

- [ ] **Step 3: Прогнать `review` по результату**

`$kirpr-tasks-review {номер}`. Ожидание: отчёт содержит строку «Решение: …», таблицу scores без замечаний вида «нет оценки», «нет SQL-примера», «критерий готовности».

- [ ] **Step 4: Прогнать `push --dry-run`**

Через скил или напрямую: `python3 ~/.local/share/kirpr/scripts/create_youtrack.py --plan {dir}/create-plan.json --solution-file {dir}/SOLUTION.md --dry-run`.
Expected: секция «Решение в родителя» присутствует; сетевых записей нет.

- [ ] **Step 5: Исправить найденное, перепрогнать тесты**

Run: `python3 -m unittest discover -s tests -v`
Expected: все PASS.

- [ ] **Step 6: Squash и коммит**

```bash
git rebase -i main   # squash всех wip: в один
git commit --amend -m "refactor(kirpr): solution-first decomposition

Decomposition now produces research.md, SOLUTION.md and one task per
service; review, adapt and push follow the same format; create_youtrack
publishes SOLUTION.md to the parent issue (--solution-file). Consistency
test guards against the old format."
```

(Интерактивный rebase недоступен из сессии Cowork — выполнить `git reset --soft main && git commit` с тем же сообщением.)
