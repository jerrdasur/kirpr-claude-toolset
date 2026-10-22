# Wrap-up — assembling the document

Runs on the user's direct command. Ends with a `<slug>.md` file in the session directory; the slug is taken from the `state.md` header.

## Step 1. Outline

Read `journal.md` in full and `state.md`. Lay everything out in the structure from the «Document structure» section below.

This is not text yet but the complete set of facts in the right order. Do no editing here.

Per-lens sections are the lenses from `## Линзы` in `state.md`, in the same order. A lens the user excluded from the session gets no section: `.kirpr/grill-me/lenses.md` holds the lenses of the whole project, not of this session, and is not read here.

For every decision, name its basis as one of three kinds:

| Basis | What it looks like |
|---|---|
| the user's answer | `Ваш ответ (раунд 12)` |
| a found fact | `Факт: ARPU конкурента $8/место [ссылка]` |
| an assumption | `Допущение: конверсия из триала не ниже 12%` |

**The three kinds are not mixed.** An assumption that reached the document disguised as a fact is the main way to sink a product hypothesis. If the basis is unclear from the journal — it is an assumption, not a fact.

Save the outline to a temporary file in the session directory — `draft.md`.

## Step 2. Editing by a subagent

Check that the file `~/.local/share/kirpr/prompts/text.md` exists. If not — go to step 3.

Launch one subagent. The prompt includes:

- Role: «Прочитай файл `~/.local/share/kirpr/prompts/text.md` и следуй ему при работе с текстом.»
- Input: absolute path to `draft.md`.
- Output: absolute path to `<slug>.md` in the session directory.
- Task: edit the outline in the informational style and write the result.
- **Restriction: cuts words, not facts.** Not a single number, link, open question, unknown or discarded statement from the outline disappears or merges with a neighbor. No section is thrown out, even an empty one — an empty section is also a grilling result. The informational style here is about how it is said, not about how much is left.
- Restriction: do not change the section structure, do not rename headings.

A subagent, not you: the journal and the editing iterations must not settle in the main context where it is already filled with the whole session. If delegation is unavailable, edit `draft.md` into `<slug>.md` yourself and do the same five-category comparison of draft and final in the current session; tell the user plainly about the fallback.

When the subagent returns — compare the result with `draft.md` in five categories: sections, links, numbers, open questions and unknowns, discarded statements. You check not «does it look alike» but whether every element is present: a lost number and two open questions merged into one look like tidy text. Something is missing — restore it from `draft.md` into the result and list to the user what had to be restored. After the comparison, delete `draft.md`.

## Step 3. If text.md is not found

Say plainly: the `kirpr:text` prompt is not installed, there is nothing to produce the final text with. Rename `draft.md` to `<slug>.md` and suggest running Codex `$kirpr-text` or Claude Code `/kirpr:text` by hand on this file.

**Do not imitate the style from memory.** «Написан через kirpr:text» refers to the specific prompt, not to a general notion of the informational style.

## Step 4. Completion

Show the path to the document and the number of rounds. Do not commit.

Say that the session directory stays on disk and Codex `$grill-me <путь к каталогу>` or Claude Code `/grill-me <путь к каталогу>` resumes the conversation from the same point.

## Document structure

```markdown
# <Предмет>

2026-08-12 · 47 раундов · линзы: проблема, сегмент, ценность,
монетизация, метрики, риски

## Резюме

**Гипотеза.** Одна формулировка в том виде, до которого её довели.

**На чём держится.** 3–5 пунктов.

**Дыры.** 3–5 пунктов.

## Монетизация

**Решено.** Нижний тариф от трёх мест, цена за место.

**Основания.** Ваш ответ (раунд 12) · факт: Linear $8/место
[https://linear.app/pricing] · допущение: конверсия из триала не ниже 12%

**Неизвестно.** Как считать место в команде с гостевыми доступами.

## <остальные линзы в том же виде>

## Открытые вопросы

Всё из `## Неизвестные`, `## Открытые узлы`, `## Ожидают факта` и
`## Пропущено в этом проходе` в `state.md`, плюс пропущенные узлы
прошлых проходов — их держит журнал, состояние их не хранит. Узел, по
которому факт так и не вернулся, идёт сюда как неизвестное.

## Что развалилось по ходу

Формулировки, не пережившие прожарку, вместе с причиной и номером раунда.
```

The summary is at the top so that a stranger can read the document in a minute. It is written last, when all per-lens sections are already assembled.

The «Что развалилось по ходу» section keeps what was discarded together with the reason. A month later it is the only thing that prevents a return to what was already discarded — so it is not shortened or dropped, even if it looks like a list of someone else's mistakes.
