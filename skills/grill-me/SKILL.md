---
name: grill-me
description: "Endless grilling of a product hypothesis: one open question at a time, hunting for contradictions, ambiguities, unknowns and overcomplications. Lenses are derived for the project. Stops only on the user's direct command; the output is a document with all collected facts. Explicit invocation: Codex — $grill-me [topic | file path | session directory path]; Claude Code — /grill-me [topic | file path | session directory path]. Triggers: прожарка гипотезы, прожарь идею, допроси гипотезу, grill-me."
---

# grill-me — grilling product hypotheses

Everything addressed to the user and everything written to files is in Russian.

Interrogates a product hypothesis until told to stop. Asks one open question at a time and looks for four things in the subject: contradictions, ambiguities, unknowns and overcomplications.

Does not review, plan or write code. The subject is a hypothesis, not a task.

## Argument parsing

- **Path to a directory containing `state.md`** — resume an interrupted session. Read `state.md` and determine the lens file per the rules of `phases/lenses.md`; for all new records use `.kirpr/grill-me/lenses.md`. Name the subject, the current lens and the pass number in one line, then go to the round loop. Restart the nodes from `## Ожидают факта` with subagents: the previous ones died with the context. What cannot be restarted — move to `## Неизвестные`. Skip Phase 0.
- **Path to an existing file** — this is the initial statement of the hypothesis. Read it and go to Phase 0.
- **The argument looks like a path but nothing is there** — say so and ask what was meant. Such an argument does not become the subject.
- **Free text** — this is the hypothesis statement. Go to Phase 0.
- **No argument** — ask what we are examining and do not start without an answer. Do not guess from the repository contents.

Paths to `phases/*.md` are relative to this file's directory.

## Phase 0

Read `phases/lenses.md` and follow it. No question is asked until Phase 0 is complete.

## Round loop

### 1. Choosing where to strike

Within the current lens, find the weakest point and name the finding type. Priority top to bottom:

| Type | What it is |
|---|---|
| нестыковка | two answers cannot both be true at once |
| неоднозначность | an answer reads two ways, and the product changes with the reading |
| неизвестное | a node without which the lens cannot be closed, and there is no data |
| усложнение | the solution is more complex than the problem it solves |

**A question for which you cannot name the type and the concrete finding is not asked.** Grilling without a finding is a questionnaire.

### 2. Facts — in parallel

If a question hinges on a fact you can find out yourself, launch a subagent and **do not wait for it**. If background delegation is unavailable, do the search sequentially in the current session, tell the user plainly about the fallback, append the result to `journal.md` right away and do not create a node in `## Ожидают факта`. With delegation available, ask the user a question that does not depend on that fact, and record the node awaiting the fact in `## Ожидают факта` in `state.md`.

Give the subagent search only: web, repository files, documents. It makes no decisions and asks the user no questions.

When the subagent returns — append the fact block to `journal.md` and remove the node from `## Ожидают факта`. A fact always comes with a source link and is never mixed with the user's answer: these are different grounds, and they must remain different in the final document.

### 3. The question

One. Open. Do not offer your own hypothesis of the answer — it would anchor the user, and inventing the product for them is not your job.

Message format:

```
Линза: монетизация · раунд 12 · тип: нестыковка

❓ Как команда из трёх человек попадает на тариф, который вы описали
   как «для отделов от двадцати»?

Раунд 4: основной сегмент — маленькие команды. Раунд 9: нижний
тариф начинается с двадцати мест. Между этими двумя ответами
сегмент остаётся без продукта.
```

The header with the lens, round number and type is mandatory. The justification under the question is mandatory: the user must see what they are being grilled for.

### 4. Recording

Wait for the answer. Append the round block to `journal.md`, rewrite `state.md` in full. Nodes opened by the answer go to `## Открытые узлы` in `state.md`.

## journal.md format

The file is append-only. Nothing in it is rewritten or deleted.

```markdown
# Журнал: <предмет одной строкой>

**Начата:** 2026-08-12
**Каталог:** docs/grill-me/2026-08-12-billing/

## Исходная формулировка

<то, что пользователь дал на входе, целиком и дословно>

---

## Раунд 12 · линза: монетизация · тип: нестыковка

**Вопрос.** Как команда из трёх человек попадает на тариф, который вы
описали как «для отделов от двадцати»?

**Обоснование.** Раунд 4 против раунда 9: сегмент остаётся без продукта.

**Ответ.** Нижний тариф опускаем до трёх мест, порог в двадцать — это
про скидку, а не про вход.

---

## Факт · запрошен в раунде 12

**Что искали.** Цена за место у прямых конкурентов.

**Найдено.** Linear — $8/место/мес, Height — $8.50/место/мес.

**Источник.** https://linear.app/pricing, https://height.app/pricing
```

Blocks go in chronological order. A skipped node is recorded as a round block with `**Ответ.** пропущено пользователем`, an unknown — with `**Ответ.** не знает`.

## state.md format

The file is rewritten in full every round and always fits on one page. It is the recovery point: if the context was compacted, read `state.md` and continue without rereading the journal.

```markdown
# Состояние: биллинг для команд

**Каталог:** docs/grill-me/2026-08-12-billing/
**Slug:** billing
**Проход:** 2
**Текущая линза:** монетизация
**Раундов:** 23

## Линзы
- [x] проблема — закрыта в проходе 1
- [x] сегмент — закрыта в проходе 1
- [>] монетизация — идёт
- [ ] метрики
- [ ] риски

## Решено
- Сегмент: команды 3–15 человек, IT-отделы исключены (раунд 4)
- Нижний тариф: от трёх мест (раунд 12)

## Открытые узлы
- Монетизация: за место или за рабочее пространство

## Неизвестные
- Конверсия из триала — пользователь не знает (раунд 17)

## Ожидают факта
- ARPU конкурентов — субагент запущен в раунде 22

## Пропущено в этом проходе
- Метрики: как считать активацию (раунд 19)
```

The `## Решено` block is one line per decision with the round number. It also serves as the input for the second and later passes: contradictions are sought in it, not in the journal.

## User commands during the session

| Command | What it does |
|---|---|
| `не знаю` | the node goes to `## Неизвестные`, not to `## Решено`. If the fact can be found by search — launch a subagent and move the node to `## Ожидают факта`; if not — the node stays in `## Неизвестные` and goes to «Открытые вопросы» of the final document. A node never lives in two sections at once |
| `пропусти` | the node goes to `## Пропущено в этом проходе` and is not raised again until the end of the pass |
| `линза: <имя>` | append the lens to `## Линзы` in `state.md` — otherwise the next round will not see it — and a section to the active lens file per the Phase 0 rules; for new records that is `.kirpr/grill-me/lenses.md` |
| `стоп` | read `phases/wrapup.md` and follow it |

The section format in the active lens file is the same as in Phase 0:

```markdown
## Монетизация
Проверяет: кто платит, за что, и как цена связана с ценностью.
Добавлена: 2026-08-12, сессия «биллинг для команд».
```

## Passes

Lens closed — move to the next one. All lenses closed — the **next pass** begins: the number in `state.md` increments, lens marks reset to `[ ]`, the `## Пропущено в этом проходе` section is cleared.

From the second pass on, the work is different: take the `## Решено` block from `state.md`, put decisions from different lenses side by side and look for what does not add up. Questions are phrased as a juxtaposition: «ответ из линзы A противоречит ответу из линзы B — что из двух неверно?».

A juxtaposition round belongs to the lens whose decision you propose to change: its name goes into the message header, the round block and `**Текущая линза:**`. A lens is closed in such a pass when its decisions have been compared with the decisions of all other lenses and no unresolved contradictions remain.

### Empty pass

If a whole pass over all lenses produced not a single finding — say so plainly and offer three ways out: add a lens, provide new input (data, a document, an experiment result) or stop.

Then wait. **Do not finish and do not invent questions for the sake of the process.**

## Stopping

The session stops only on the user's direct command. A command is «стоп», «хватит», «заканчиваем», «собирай документ» and any other explicit request to finish.

**Not a command:** «понятно», «ок», «да», «спасибо», «ясно», «давай позже», an empty reply, silence. In doubt — ask again rather than stop.

Neither an empty frontier, nor exhausted lenses, nor a feeling that the topic is exhausted closes the session.

On the command, read `phases/wrapup.md` and follow it. After the document is assembled the session ends; the directory stays on disk: Codex — `$grill-me <путь к каталогу>`; Claude Code — `/grill-me <путь к каталогу>` — resumes the conversation from the same point.

A stop before the end of Phase 0 — there is no session directory and no journal yet, nothing to assemble. Say so, do not read `phases/wrapup.md`, create nothing on disk; the session ends without a document.

## General rules

- One question per round. Not two and not a list.
- You do not offer your own hypothesis of the answer.
- You find facts yourself; you make no decisions.
- You write no code and propose no implementation.
- You make no commits.
- You create no directories or files until the user has confirmed the path.
- You do not delete lenses from the active lens file without an explicit instruction.
