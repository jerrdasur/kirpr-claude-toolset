# kirpr: перевод инструкций на английский — план реализации (этап B)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Перевести тела всех инструкций репозитория на английский, оставив русскими образцы вывода, литералы для пользователя и доменную терминологию, и закрепить строку о языке вывода тестом.

**Architecture:** Перевод ручной, файл за файлом, по группам из спеки; code-блоки, цитаты в «…», идентификаторы в бэктиках и `style-examples.md` не переводятся. Каждый SKILL.md получает одну и ту же строку о языке вывода, её наличие проверяет `test_skill_contracts`. Полнота перевода проверяется ревью и grep-отчётом доли кириллицы вне code-блоков (информационно, не тестом).

**Tech Stack:** Markdown, Python 3 `unittest`; `tiktoken` (в облачном контейнере) для подсчёта токенов до/после.

**Spec:** `docs/superpowers/specs/2026-10-22-kirpr-solution-first-design.md`, раздел «Этап B — перевод».

## Global Constraints

- Строка о языке вывода, дословно, в каждом SKILL.md сразу после заголовка первого уровня: `Everything addressed to the user and everything written to files is in Russian.`
- Остаются на русском: всё содержимое `kirpr/config/style-examples.md`; цитаты заказчика; доменная терминология в бэктиках; литералы, которые скил произносит пользователю или пишет в файлы (вопросы, тексты отчётов, шаблоны `research.md`/`SOLUTION.md`/задач/`.context.md`, примеры таблиц). Правило отличия: переводится то, что читает модель как инструкцию; не переводится то, что модель воспроизводит.
- Перевод ручной; машинный перевод целиком запрещён. Термины единообразны: task, parent issue, child issues in the tracker, decomposition, research, solution, phase, checklist, rubric, score.
- Frontmatter `name` не меняется. `description` — английский; у `grill-me` и `expert-panel` после английского описания добавляются русские trigger-фразы через «Triggers: …». `agents/openai.yaml` не меняется.
- Имена файлов, пути `~/.local/share/kirpr/...`, формы вызова `$skill` / `/kirpr:skill` не меняются.
- Все тесты зелёные после каждой задачи: `python3 -m unittest discover -s tests`. `TestNoLegacyFormat` ищет русские маркеры — после перевода они исчезнут сами; тест остаётся как есть.
- Ветка `kirpr-english`; один коммит на задачу (`i18n: …`), без squash — спека допускает серию по скилу.

## Review Focus

1. Литерал, который скил произносит пользователю, случайно переведён — пользователь получит английскую реплику внутри русского диалога (например, вопрос гейта в `push`). Проверка в Task 8: grep по `«` и `"` внутри переведённых файлов, каждая кавычка-литерал — русская.
2. Переведена подпись раздела, на которую другой файл ссылается по-русски (например, `templates.md` секция «Загрузка контекста декомпозиции», на которую ссылаются `review`/`adapt`; `TestContextLoading` и `TestTemplates` режут файл по русским заголовкам). Тест: `tests/test_kirpr_config_consistency.py` обновляется в Task 2 на английские заголовки, и Task 3 падает, если ссылка в скиле не совпала.
3. `description` без русских trigger-фраз у `grill-me`/`expert-panel` — пользователь, вызывающий по-русски, не получит подсказку; проверка в Task 6/7 — `assertIn("Triggers:", description)` добавляется в `test_skill_contracts`.
4. Команда-адаптер переведена, но `test_claude_commands_are_thin_adapters` ищет русскую фразу — тест читается в Task 3 до перевода адаптеров.
5. `style-examples.md` затронут переводом — проверяется `git diff --stat` в Task 8: файл не должен попадать в diff ветки.

---

### Task 1: Тест на строку о языке вывода

**Files:**
- Modify: `tests/test_skill_contracts.py`

**Interfaces:**
- Produces: константа `OUTPUT_LANGUAGE_LINE = "Everything addressed to the user and everything written to files is in Russian."` в `test_skill_contracts.py`; тест `test_every_skill_declares_output_language`.

- [ ] **Step 1: Написать тест**

В класс, который перебирает `ALL_SKILLS` (рядом с `test_all_skills_are_explicit`):

```python
OUTPUT_LANGUAGE_LINE = "Everything addressed to the user and everything written to files is in Russian."

def test_every_skill_declares_output_language(self):
    for name in ALL_SKILLS:
        text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        with self.subTest(skill=name):
            self.assertIn(OUTPUT_LANGUAGE_LINE, text)
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `python3 -m unittest tests.test_skill_contracts -v 2>&1 | grep -c "FAIL: test_every_skill_declares_output_language"`
Expected: `11` (все скилы).

- [ ] **Step 3: Commit**

```bash
git add tests/test_skill_contracts.py
git commit -m "i18n: test that every skill declares Russian output language"
```

---

### Task 2: `kirpr/config` — `workflow.md`, `templates.md`, `tracker-runtime.md`, шаблоны `.template`

**Files:**
- Modify: `kirpr/config/workflow.md`, `kirpr/config/templates.md`, `kirpr/config/tracker-runtime.md`, `kirpr/config/tracker.md.template`, `kirpr/config/custom-experts.md.template`
- Modify: `tests/test_kirpr_config_consistency.py`

**Interfaces:**
- Produces: английские заголовки секций `templates.md`, на которые ссылаются скилы в Task 3: `## Critical rules`, `## Loading decomposition context`, `## File naming`, `## research.md template`, `## SOLUTION.md template`, `## 00-overview.md template`, `## Task file template (NN-service.md)`, `## .context.md template`, `## Verification checklist`, `## Quality scoring rubric`; заголовки фаз `workflow.md`: `## Phase 1: Fetch from the tracker` … `## Phase 6: Generate files`, подфазы `2a`–`2d`, `4a`–`4e` сохраняют буквы.
- Produces: в `test_kirpr_config_consistency.py` разрезы по `## SOLUTION.md template`, `## 00-overview.md template`, `## Loading decomposition context`; `TestPhaseReferences` ищет `Phase (\d+)` и определения `^## Phase (\d+)`; `TestTemplates` ищет `## Problem` и `## External dependencies`.

- [ ] **Step 1: Обновить тест консистентности под английские заголовки и запустить**

Run: `python3 -m unittest tests.test_kirpr_config_consistency -v`
Expected: FAIL в `TestContextLoading`, `TestTemplates`, `TestPhaseReferences` (английских заголовков ещё нет).

- [ ] **Step 2: Перевести `workflow.md`**

Инструкции — на английский; шаблонные фразы, которые модель записывает в `SOLUTION.md` (пример «между A и B одно сообщение X…»), вопрос «суть в чём?», литералы вида «подтвердить на dev», «Чеклист пройден. Генерирую файлы?» — оставить русскими в кавычках. Заголовки фаз — по Interfaces.

- [ ] **Step 3: Перевести `templates.md`**

Инструкции и заголовки секций — на английский; содержимое всех ```markdown```-блоков (шаблоны файлов) и чеклист в ```-блоке — русские без изменений; текст рубрики К1–К5 (описания баллов) — на английский, названия критериев `K1 … K5` латиницей с русской расшифровкой в скобках один раз.

- [ ] **Step 4: Перевести `tracker-runtime.md` и два `.template`**

`tracker.md.template` и `custom-experts.md.template` — это файлы, которые пользователь правит руками: комментарии-подсказки перевести, примеры значений оставить.

- [ ] **Step 5: Проверка**

Run: `python3 -m unittest discover -s tests`
Expected: `TestContextLoading`, `TestTemplates`, `TestPhaseReferences` PASS; падают только `test_every_skill_declares_output_language` (11) и, возможно, тесты, читающие русские заголовки `templates.md` из скилов — их чинит Task 3.
Run: `git diff --stat -- kirpr/config/style-examples.md`
Expected: пусто.

- [ ] **Step 6: Commit**

```bash
git add kirpr/config tests/test_kirpr_config_consistency.py
git commit -m "i18n: translate kirpr config instructions to English"
```

---

### Task 3: `kirpr-tasks-*` (decompose, review, adapt, push) и command-адаптеры

**Files:**
- Modify: `skills/kirpr-tasks-decompose/SKILL.md`, `skills/kirpr-tasks-review/SKILL.md`, `skills/kirpr-tasks-adapt/SKILL.md`, `skills/kirpr-tasks-push/SKILL.md`
- Modify: `commands/kirpr/*.md` (все 9)
- Modify: `tests/test_skill_contracts.py` (только если `test_claude_commands_are_thin_adapters` ищет русскую фразу — проверить первым шагом)

**Interfaces:**
- Consumes: английские заголовки секций `templates.md` и фаз `workflow.md` из Task 2.
- Produces: текст адаптера `commands/kirpr/*.md`: `# kirpr compatibility entry point` / `Read \`~/.claude/skills/<name>/SKILL.md\` in full and follow it.` / `Explicit invocation arguments:` + блок `$ARGUMENTS`.

- [ ] **Step 1: Прочитать `test_claude_commands_are_thin_adapters` и `test_create_skill_cross_workflow_reference_shows_both_invocation_forms`**

Если они ищут русские фразы — обновить ожидания на английские формулировки из Produces, запустить, увидеть FAIL.

- [ ] **Step 2: Перевести четыре SKILL.md**

Добавить строку о языке вывода после `# …`. Инструкции — на английский. Русскими остаются: все ```-блоки с примерами отчётов, таблиц влияния, diff; вопросы пользователю в кавычках («Что изменилось? …», «Создаю N задач …?», «Начинаю итерацию …», «Все файлы обработаны. Применяю исправления?»); сообщения об ошибках в кавычках («Декомпозиция для {номер} не найдена. …»); строки `Решение: пройдено`, `Решение: см. {parent}`, «уже было опубликовано»; названия категорий review можно перевести, пункты чеклистов — перевести.

- [ ] **Step 3: Перевести 9 адаптеров**

- [ ] **Step 4: Проверка**

Run: `python3 -m unittest discover -s tests`
Expected: падает только `test_every_skill_declares_output_language` для 7 ещё не переведённых скилов.
Run: `grep -n "«\|\"" skills/kirpr-tasks-*/SKILL.md | grep -v '[А-Яа-яЁё]' | grep -v '^.*description:'`
Expected: только строки без литералов для пользователя (пути, идентификаторы).

- [ ] **Step 5: Commit**

```bash
git add skills/kirpr-tasks-* commands/kirpr tests/test_skill_contracts.py
git commit -m "i18n: translate kirpr-tasks skills and command adapters"
```

---

### Task 4: `kirpr-task-*` (fetch, create, update, delete) и `kirpr-text` + `prompts/text.md`

**Files:**
- Modify: `skills/kirpr-task-fetch/SKILL.md`, `skills/kirpr-task-create/SKILL.md`, `skills/kirpr-task-update/SKILL.md`, `skills/kirpr-task-delete/SKILL.md`, `skills/kirpr-text/SKILL.md`, `kirpr/prompts/text.md`

**Interfaces:**
- Consumes: `test_text_requires_confirmed_destination_before_every_edit`, `test_create_skill_obtains_issue_link_base_url_from_runtime` — прочитать, какие фразы они ищут, и сохранить их смысл; если фразы русские — обновить тест на английские в том же коммите.

- [ ] **Step 1: Прочитать два теста выше, при необходимости обновить ожидания и увидеть FAIL**

- [ ] **Step 2: Перевести пять SKILL.md**

Строка о языке вывода после `# …`. Гейты подтверждения удаления/создания (вопросы пользователю, ввод номера задачи повторно) — русские литералы в кавычках.

- [ ] **Step 3: Перевести `kirpr/prompts/text.md`**

Это правила редактуры русского текста: правила — на английский; примеры плохих/хороших русских фраз («качественный», «лучший» …) — оставить русскими как примеры.

- [ ] **Step 4: Проверка**

Run: `python3 -m unittest discover -s tests`
Expected: падает только `test_every_skill_declares_output_language` для `expert-panel` и `grill-me`.

- [ ] **Step 5: Commit**

```bash
git add skills/kirpr-task-* skills/kirpr-text kirpr/prompts tests/test_skill_contracts.py
git commit -m "i18n: translate task CRUD and text skills"
```

---

### Task 5: `expert-panel` — SKILL, `modes/`, `experts/`

**Files:**
- Modify: `skills/expert-panel/SKILL.md`, `skills/expert-panel/modes/diff.md`, `skills/expert-panel/modes/spec.md`, `skills/expert-panel/experts/{cheney,ford,pike,stonebraker}.md`
- Modify: `tests/test_skill_contracts.py` (тест на `Triggers:`)

**Interfaces:**
- Produces: `description` формата `"<English description>. Triggers: <русские фразы через запятую>."`; тест `test_russian_trigger_phrases_present` для `expert-panel` и `grill-me`: `assertIn("Triggers:", frontmatter)` и `assertRegex(frontmatter, "[А-Яа-я]")`.

- [ ] **Step 1: Написать тест на `Triggers:` для обоих скилов, запустить — FAIL для обоих**

- [ ] **Step 2: Перевести SKILL.md и `modes/`**

Строка о языке. Формат ответа пользователя (`accept 1,3,5; reject 2 — причина; ? 4`) и примеры отчётов — русские. `description` по формату из Produces.

- [ ] **Step 3: Перевести четыре персоны в `experts/`**

Персона — инструкция («Как ревьюит», «На что смотрит»), переводится. Цитаты и примеры замечаний, которые эксперт выдаёт пользователю, — русские.

- [ ] **Step 4: Проверка**

Run: `python3 -m unittest discover -s tests`
Expected: падает только `test_every_skill_declares_output_language` и `test_russian_trigger_phrases_present` для `grill-me`.

- [ ] **Step 5: Commit**

```bash
git add skills/expert-panel tests/test_skill_contracts.py
git commit -m "i18n: translate expert-panel skill, modes and personas"
```

---

### Task 6: `grill-me` — SKILL и `phases/`

**Files:**
- Modify: `skills/grill-me/SKILL.md`, `skills/grill-me/phases/lenses.md`, `skills/grill-me/phases/wrapup.md`

**Interfaces:**
- Consumes: `test_grill_me_discovers_both_project_guidance_files` — прочитать, сохранить искомые пути; тест на `Triggers:` из Task 5.

- [ ] **Step 1: Перевести три файла**

Строка о языке. Команды пользователя по ходу («стоп», «дальше», «итог» — какие есть) и формат документа wrap-up — русские. `description` по формату Task 5.

- [ ] **Step 2: Проверка**

Run: `python3 -m unittest discover -s tests`
Expected: все PASS.

- [ ] **Step 3: Commit**

```bash
git add skills/grill-me
git commit -m "i18n: translate grill-me skill and phases"
```

---

### Task 7: Доля кириллицы и токены до/после

**Files:**
- Create: `tests/tools/cyrillic_report.py` (не тест; скрипт отчёта)

**Interfaces:**
- Produces: `python3 tests/tools/cyrillic_report.py <files…>` печатает для каждого файла долю кириллицы вне ```-блоков и вне строк, содержащих «…» или "…", в процентах.

- [ ] **Step 1: Написать скрипт и прогнать по всем переведённым файлам**

Run: `python3 tests/tools/cyrillic_report.py kirpr/config/workflow.md kirpr/config/templates.md kirpr/config/tracker-runtime.md kirpr/prompts/text.md skills/*/SKILL.md skills/expert-panel/*/*.md skills/grill-me/phases/*.md commands/kirpr/*.md`
Expected: каждая строка ≤ 10 %; строки выше — прочитать файл и либо перевести остаток, либо подтвердить, что это литералы для пользователя.

- [ ] **Step 2: Токены до/после**

В облачном контейнере: `pip install tiktoken --break-system-packages`; посчитать `o200k_base` (прокси Codex) и `cl100k_base` для `kirpr/config/{workflow,templates}.md` и четырёх `kirpr-tasks-*/SKILL.md` на `main` (до) и на ветке (после). Записать таблицу «файл / до / после / %» в сообщение коммита Task 8.
Expected: суммарно по `o200k_base` минус 15 % и больше; по `cl100k_base` минус 40 % и больше. Если меньше — это не блокер, но число идёт в отчёт.

- [ ] **Step 3: Commit**

```bash
git add tests/tools/cyrillic_report.py
git commit -m "i18n: cyrillic share report script"
```

---

### Task 8: Ревью перевода и smoke

**Files:**
- Нет новых.

- [ ] **Step 1: Вычитка**

Прочитать каждый переведённый файл целиком против версии на `main` (`git diff main -- <file>`): смысл правил не изменился, литералы для пользователя не переведены, термины единообразны по списку из Global Constraints.

- [ ] **Step 2: Review Focus 1 и 5**

Run: `git diff --stat main -- kirpr/config/style-examples.md`
Expected: пусто.
Run: grep из Task 3 Step 4 по всем SKILL.md.

- [ ] **Step 3: Smoke (владелец)**

`./install.sh --target all`; `decompose` → `review` на той же задаче, что и в smoke этапа A; сравнить результат: русский диалог и русские файлы, никаких английских реплик пользователю.

- [ ] **Step 4: Финальный прогон тестов**

Run: `python3 -m unittest discover -s tests`
Expected: все PASS.
