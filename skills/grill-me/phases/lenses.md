# Phase 0 — assembling the lenses

Ends with an agreed set of lenses, a created session directory and the first versions of `journal.md` and `state.md`. Until then not a single question is asked of the user.

## Step 1. The subject

The statement arrived as an argument or from a file. If it is shorter than one sentence or unclear — ask to expand it. One clarifying pass, not an interrogation: grilling begins after Phase 0, not inside it.

## Step 2. Project reconnaissance

Read `AGENTS.md`, `CLAUDE.md`, `README.md`, the contents of `docs/` if they exist, and look at the top-level directory structure. Grep for the subject's key terms — names of products, entities, services.

The goal is to understand what the product is and what it stands on. Do not read through the codebase: lenses are derived from the nature of the product, not from the implementation.

If there is no repository or it is empty — that is fine. A hypothesis can be grilled without code; the lenses will just be derived from the subject alone.

## Step 3. Existing lenses

First determine the active lens file:

- `.kirpr/grill-me/lenses.md` exists — read and write only it.
- Neither `.kirpr/grill-me/lenses.md` nor `.claude/grill-me/lenses.md` exists — ask the usual path confirmation before creating `.kirpr/grill-me/lenses.md`; do not create the file before confirmation.
- `.kirpr/grill-me/lenses.md` does not exist but `.claude/grill-me/lenses.md` does — show the user both paths and ask whether to copy the legacy file to `.kirpr/grill-me/lenses.md`.
  - Copy approved — copy once, then read and write the new file.
  - Copy declined — read the legacy file and do not write it.

Every `## <Имя>` section of the active file is a saved lens. For all new records use `.kirpr/grill-me/lenses.md`.

## Step 4. Deriving the set

Compose a set of lenses for this project and this subject. For each:

- **name** — one or two words;
- **what it checks** — one line;
- **why it is needed here specifically** — one line, referring to a fact from step 1 or 2.

**A lens without the third item is not proposed.** A textbook list of eight items, identical for any project, is not a set of lenses but a brush-off. If the product is internal, go-to-market and competitor lenses are not needed. If the hypothesis is about price, there is not one monetization lens but three.

A reasonable size is four to eight lenses. Fewer than four — the subject will not be covered; more than eight — the first pass will never end.

## Step 5. Agreement

Show the user two lists separately:

```
Из активного файла линз:
  • проблема — есть ли она у кого-то, кроме вас
  • сегмент — кто именно платит и почему он

Предлагаю добавить под этот предмет:
  • монетизация — гипотеза про цену, а тарифов в продукте пока нет
  • миграция — у вас 400 существующих команд на старом тарифе
```

First session in the project — there is no lens file, the first list is empty: show only the second.

Ask what to remove and what to add. **Rounds do not start without an answer.** The user is silent or answers ambiguously — ask again.

## Step 6. Recording the lenses

Write the agreed set to `.kirpr/grill-me/lenses.md`; create the `.kirpr/grill-me/` directory if it does not exist. If the user declined copying the legacy file, do not write the lenses: explain that writing is possible only after consent to the new path.

Section format:

```markdown
## Монетизация
Проверяет: кто платит, за что, и как цена связана с ценностью.
Добавлена: 2026-08-12, сессия «биллинг для команд».
```

Append new lenses at the end. Do not touch or delete existing ones — even those the user excluded from this session: excluding from the set and deleting from the project are different things. Delete only on an explicit request.

Take the date from the system environment.

## Step 7. Session directory

Propose a path and wait for confirmation:

```
Каталог сессии: docs/grill-me/2026-08-12-billing/
Годится или указать другой?
```

Derive the slug from the subject — short, Latin letters, hyphenated. The date — from the system environment.

**Create nothing without confirmation.** The directory may turn out to be someone else's repository.

After confirmation, create the directory and two files per the formats in `SKILL.md`:

- `journal.md` — title, date, directory, a `## Исходная формулировка` section with the user's input verbatim;
- `state.md` — subject, directory, slug, `**Проход:** 1`, the first lens as current, `**Раундов:** 0`, a `## Линзы` section listing the lenses with `[ ]` marks, empty sections `## Решено`, `## Открытые узлы`, `## Неизвестные`, `## Ожидают факта`, `## Пропущено в этом проходе`.

## Completion

Say in one line: the lens composition, the session directory, which lens we start with. Then go to the round loop in `SKILL.md` — do not ask for confirmation for that; step 5 already gave it.
