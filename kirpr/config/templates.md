# Decomposition templates and rules

## Critical rules (common to all commands)

- **One question at a time.** Do not ask several questions in one message.
- **Offer options.** Where possible, give numbered answer options.
- **Show before writing.** Do not write a file without showing its content to the user. For `source.md`, `research.md` and `SOLUTION.md` showing is enough; files of Phase 6 need an explicit «да». Exception — `.context.md`: it is a cache and is written without showing.
- **The codebase is the source of truth.** If a task describes a path/structure that does not exist in the code — that is `критично`.
- **Every claim is verified.** Against code, data (metrics, logs, alerts) or the vendor's documentation and sources. Anything unverified is marked «подтвердить на dev».
- **Do not invent problems.** If a task is clearly written and matches the code — do not look for findings for the sake of a report.
- **Use the templates below.** New sections and files follow these templates.

---

## Loading decomposition context

Loading pattern for `$kirpr-tasks-review` and `$kirpr-tasks-adapt` in Codex, or `/kirpr:tasks-review` and `/kirpr:tasks-adapt` in Claude Code:

### Option A: `.context.md` exists (fast path)
1. Read `{dir}/.context.md` — the context cache from the previous session.
2. Read `{dir}/SOLUTION.md` and `{dir}/00-overview.md`.
3. Further files as needed (depends on the command's scope); facts and sources are in `{dir}/research.md`.
4. **Do not query the tracker API** — the data is already in `.context.md`. If you need details of the tracker description — read `{dir}/source.md`.

### Option B: `.context.md` does not exist (fallback)
1. Read `{dir}/source.md`, `{dir}/SOLUTION.md` and `{dir}/00-overview.md`.
2. Read all `{dir}/*.md` files.
3. Read `~/.config/kirpr/tracker.md` to determine the tracker script. Load the task data.
4. Tell the user: "Файл `.context.md` не найден — загружаю полный контекст."

---

## File naming

- **Directory:** lowercase task number (e.g. `sas-200/`)
- **Source:** `source.md`
- **Research:** `research.md`
- **Solution:** `SOLUTION.md`
- **Overview:** `00-overview.md`
- **Tasks:** `NN-service.md`, where `NN` is the ordinal in deployment order (01, 02…) and `service` is the service or repository in kebab-case. Examples: `01-scansrv.md`, `02-upload-callback.md`, `03-devops.md`.
- **File language:** names in English, content in Russian

---

## source.md template

```markdown
# {Название задачи}

> [{Номер задачи}]({URL задачи в трекере})
```

---

## research.md template

Facts, not opinions. Every fact about code comes with `file:function`, every fact about production with a source (metric, alert, log), every fact about a vendor with a link. Justifications of decisions live here, not in `SOLUTION.md`.

```markdown
# {Номер задачи} — Research

## Задача
- **Summary:** {summary}
- **Связано:** {связанные задачи, дочерние задачи в трекере}

## Как устроено сейчас
{По компонентам: точки входа, путь данных, статусная машина, обработка ошибок и повторов, тесты, инфраструктурные спеки. Таблицы там, где есть что сравнивать.}

## Что показали данные
{Таблица «время / компонент / событие» по инциденту. Количественная картина за период: сколько, какие исходы.}

## Вендор и prior art
{Что говорит документация и исходники используемых систем; известные issue; как решают аналоги. Со ссылками.}

## Решения
{Нумерованный список решений с датой; отвергнутые варианты — одной строкой с фактом, который их закрыл.}

## Непроверенное
{Что подтверждается только на dev или в проде, и как именно.}
```

---

## SOLUTION.md template

Problem statement, one sentence for the mechanism, and the changes per service. In the per-service sections every sentence is either a change or a decision inside a change. No «Принцип», «Эффект», «Что не меняем», «Порядок деплоя», «Проверить» sections, no how-to, no «как сейчас» phrases. The «Проблема» section is the only place where current behavior is described; the sentence-by-sentence cleanup does not touch it.

```markdown
# {Номер задачи} — Техническое решение

## Проблема

{Один абзац в терминах контракта или инварианта между компонентами, без следствий.}

## Решение

{Одна фраза: какой механизм вводится или меняется.}

## {сервис A}

- {Изменение: где, что, с решениями внутри — имена RPC, сигнатуры, условия, границы.}

## {сервис B}

- {Изменение.}
```

Check before writing, for every sentence of the per-service sections (the «Проблема» section is not checked): is it a change? is it a decision inside a change? does it repeat another sentence? is it true? If a sentence can be deleted and the developer would do the same thing — delete it.

---

## 00-overview.md template

```markdown
# {Название задачи} — Обзор

> Решение — в `SOLUTION.md`, факты — в `research.md`. Порядок задач задаёт очередность деплоя.

## Задачи

| # | Файл | Задача | Зависит от |
|---|------|--------|------------|
| 1 | `01-{service}.md` | {сервис}: {название} | — |
| 2 | `02-{service}.md` | {сервис}: {название} | 1 |

## Зависимости

{Только технические зависимости, по одной строке: `1 → 2` — клиент генерируется из схемы сервера.}

## Внешние зависимости

{Другие команды, внешние системы, задачи вне этой декомпозиции — по одной строке, или «нет».}
```

---

## Task file template (NN-service.md)

```markdown
# {сервис}: {название}

1. {Шаг-глагол: что сделать, где, с решением внутри.}
2. {Шаг.}
3. {Шаг.}

Проверить:
- {Конкретная проверка: вход → ожидаемый результат.}
- {Проверка.}
```

**Rules for task content:**
- One task — one service or repository — one MR.
- Heading is `{сервис}: {название}` without numbers, estimates or bracketed labels.
- 3–6 steps, each starting with a verb and naming the place in the code (RPC, function, file) and the decision that cannot be unambiguously reconstructed from `SOLUTION.md`.
- «Проверить» lists verifiable conditions, including negative scenarios and what can only be confirmed on dev.
- No metadata (SP, stage, dependencies — those are tracker fields), no justifications, no «Техническое решение / AC / Миграции» sections.
- Identifiers in backticks exactly as in the code.

---

## .context.md template

The `.context.md` file is created at the end of Phase 6 of `$kirpr-tasks-decompose` in Codex or `/kirpr:tasks-decompose` in Claude Code and caches the session context.

**Rules:**
- The file is created automatically and is not shown to the user for review (exception to the «Show before writing» rule).
- The file is in `.gitignore` — it is a cache, not an artifact.
- On adaptation via `$kirpr-tasks-adapt` in Codex or `/kirpr:tasks-adapt` in Claude Code the file is updated, not recreated.

```markdown
# .context.md — Кэш контекста декомпозиции {Номер задачи}

> Автоматически сгенерирован. Не редактируйте вручную.
> Последнее обновление: {YYYY-MM-DD HH:MM}

## 0. TL;DR

- **Задача:** {ID} — {summary одной строкой}
- **Проблема:** {формулировка из SOLUTION.md}
- **Решение:** {фраза механизма из SOLUTION.md}
- **Итого:** {N} задач по сервисам: {список сервисов}

## 1. Данные трекера

### Основная задача
- **ID:** {XXX}
- **Summary:** {summary из API}
- **Полное описание:** см. `source.md`

### Связанные задачи

| ID | Summary | Тип связи |
|----|---------|-----------|
| {YYY} | {summary} | {subtask / parent / linked} |

## 2. Разведка

### Исследованные пути
- `{путь}` — {краткое описание находки}

### Данные
- {источник} — {что показал, одной строкой}

### Вендор и prior art
- {ссылка} — {факт}

## 3. Решения

### Принятые решения
1. **{решение}:** {факт, на котором оно держится}
   - Отвергнуто: {вариант} — {факт, который его закрыл}

### Ответы пользователя
- {вопрос}: {ответ}

### Непроверенное
- {что и как подтвердить}

### Решения review
- {принято / отклонено}: {находка} — {обоснование}

## 4. Структура декомпозиции

{Таблица задач и зависимости — копия из 00-overview.md}

## 5. Карта файлов

| Файл | Задача | Статус |
|------|--------|--------|
| `SOLUTION.md` | решение | generated |
| `research.md` | разведка | generated |
| `{NN-service.md}` | {сервис}: {название} | generated |

## 5.5. Quality Scores (последний review)

| Файл | К1 | К2 | К3 | К4 | К5 | Score | Статус |
|------|----|----|----|----|----| ------|--------|
| `{NN-service.md}` | {0-2} | {0-2} | {0-2} | {0-2} | {0-2} | {0-10} | {✅ pass / ⚠️ accepted at N} |

**Общий score: {X.X}/10** (target: 8.0)
**Решение:** {пройдено / не пройдено — пункты ...}
**Дата review:** {YYYY-MM-DD}

## 6. Результаты верификации

{Чеклист с отметками [x]}

## 7. Метаданные

- **Дата декомпозиции:** {YYYY-MM-DD}
- **Дата последней адаптации:** —
- **Версия context:** 1
- **Кол-во адаптаций:** 0
```

---

## Verification checklist

Used in `$kirpr-tasks-decompose` (Phase 5) and `$kirpr-tasks-adapt` (Phase D) in Codex, or `/kirpr:tasks-decompose` (Phase 5) and `/kirpr:tasks-adapt` (Phase D) in Claude Code:

```
Чеклист завершённости:
[ ] Формулировка проблемы согласована и не содержит следствий
[ ] Каждое утверждение SOLUTION.md проверено по коду, данным или вендору, либо помечено «подтвердить на dev»
[ ] В разделах SOLUTION.md по сервисам нет предложений, которые описывают существующее поведение или повторяют другие
[ ] Одна задача — один сервис — один MR; все изменения из SOLUTION.md покрыты задачами
[ ] Заголовок каждой задачи — `{сервис}: {название}`, 3–6 шагов-глаголов, список «Проверить»
[ ] Зависимости в 00-overview.md — только технические и непротиворечивы; внешние зависимости перечислены или помечены «нет»
[ ] Отвергнутые варианты зафиксированы в research.md одной строкой с фактом
```

If at least one item is not passed — **return to editing**.

---

## Quality scoring rubric

Used in `$kirpr-tasks-review` in Codex or `/kirpr:tasks-review` in Claude Code to score every task. 5 criteria, 0–2 points each = max 10.

**Quality threshold: 8/10.** Files with score < 8 require iteration.

### K1: Specificity (К1, конкретность; 0–2)

Scores unambiguity of wording and absence of vague expressions.

- **0** — Wording is abstract ("добавить логику обработки", "реализовать валидацию"). The developer has to interpret the scope.
- **1** — Main steps are specific but there are gaps (1–2 places with "и т.д.", "аналогично", "как сейчас").
- **2** — Every step is unambiguous. Two developers would implement it the same way.

### K2: Completeness of decisions (К2, полнота решений; 0–2)

Scores whether the steps name the decisions that determine the implementation: RPC names and signatures, branching conditions, boundaries (what is not changed inside the change), data sources.

- **0** — No decisions, only a direction ("сообщать о падении").
- **1** — Key decisions are named, but the developer will have to make some on their own.
- **2** — Every decision that cannot be unambiguously reconstructed from `SOLUTION.md` is named in the steps. No extra details (how-to, justifications).

### K3: Verifiability (К3, проверяемость; 0–2)

Scores the «Проверить» list.

- **0** — No list, or conditions are unverifiable ("всё работает").
- **1** — Conditions are verifiable, but there are no negative scenarios or no items that can only be confirmed on dev.
- **2** — Every condition is «вход → ожидаемый результат», with negative scenarios and edge cases.

### K4: Self-sufficiency (К4, самодостаточность; 0–2)

Scores whether a developer can complete the task from this file and `SOLUTION.md` without reading the others.

- **0** — Other tasks or correspondence must be read to understand the scope.
- **1** — The scope is clear, but some decisions have to be looked up in other tasks or in `research.md`.
- **2** — The file together with `SOLUTION.md` is sufficient.

### K5: Codebase conformance (К5, соответствие кодовой базе; 0–2)

Scores whether the described paths, structures and conventions match the real code.

- **0** — 2+ nonexistent paths/packages, or a contradiction with real conventions.
- **1** — Paths exist, but the style (naming, tests, patterns) does not match the existing code.
- **2** — All paths, structures and conventions match the codebase.
