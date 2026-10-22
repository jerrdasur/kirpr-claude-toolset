# Mode: spec review

A critical examination of a design document before moving on to planning. Ends with an updated spec, not a report.

## Determining the artifact

1. A path was passed as an argument — use it.
2. No path — take the newest file in `docs/superpowers/specs/`. If the directory does not exist or is empty, ask the user for a path.
3. Several candidates and the choice is not obvious — show the list and ask.

## Phase 1. Context

1. Read the spec in full.
2. Read the repository's `CLAUDE.md` or `AGENTS.md` and `.kirpr/memory.md` if they exist. `## Ловушки` and `## Уроки` from memory go to the agents as context. No memory file — say in one line that `$kirpr-onboard` in Codex or `/kirpr:onboard` in Claude Code creates it, and continue.
3. Find the affected code: grep by the spec's key terms — package, type, table and endpoint names. Collect a list of relevant paths, no more than 20.
4. If the spec has a `## Review log` section — read it. Findings rejected earlier with a reason are not raised again. Findings accepted earlier are checked: are they reflected in the current text.
5. Show the user a summary:
   - the spec's topic in one line;
   - affected packages and services;
   - what the spec mentions that was not found in the code;
   - previous panel runs, if any.

**Do not move to Phase 2 without the user's confirmation.** A panel launched on a spec in a vacuum produces findings about nonexistent code.

## Phase 2. Panel

Assemble the active panel and launch the agents per the protocol in `SKILL.md`. Mode — `спека`: the agent uses the «В спеке проверяет» block of its persona.

Pass to every agent: the spec path, the list of relevant paths from Phase 1, the Review log content if it exists, and `## Ловушки` / `## Уроки` from `.kirpr/memory.md` if it exists.

## Phase 3. Report

Synthesize per the protocol in `SKILL.md` and show the report:

1. **Панель** — who took part.
2. **Удачные решения** — combined, without a per-expert breakdown.
3. **Замечания** — all of them, by descending severity, each with `id`, place, substance, consequence, the proposed edit and `уверенность`.
4. **Конфликты** — pairs of mutually exclusive findings with each expert's position.

## Phase 4. Walkthrough

Ask the user to answer in one line in the format:

    accept C2,S1; reject F3 — причина; ? P4

- `accept` — the edit will be applied.
- `reject` — a reason is mandatory; it goes into the Review log.
- `?` — discussed one at a time, each until an `accept` or `reject` decision.

Group forms are allowed, because an unlimited report can hold dozens of findings:

- `accept all`, `accept all except F3,P5`;
- `accept blocker,major` — every finding of those severities;
- `reject nit — причина`, `reject minor — причина` — one reason for the whole group.

Explicit ids override a group form in the same answer: `accept blocker,major; reject C4 — причина` rejects `C4` even if it is a `major`.

Findings the answer does not mention are not applied. After parsing, list them in one line — «без решения: F4, P7» — and ask once whether to decide them now; if not, they stay without a decision. In spec mode they go to the Review log as «не рассмотрено» and may be raised again by the next run.

Conflicts require an explicit choice of a side — accepting both findings of a pair is not possible, also not through a group form: a group form leaves both findings of a conflict without a decision.

If the answer did not parse, or mentions an id that is not in the report — show what exactly you did not understand and ask again. Do not guess and do not apply a partially parsed answer.

Do not poll finding by finding: with dozens of findings that is dozens of rounds, more expensive than the review itself.

## Phase 5. Edits

1. Apply only the accepted findings, as targeted edits. Do not rewrite the spec as a whole — the user agreed on the text, not on a retelling of it.
2. If an edit requires a decision that is neither in the finding nor in the spec — ask, do not invent.
3. Show the diff of the changes.

## Phase 6. Log

Append a `## Review log` section to the end of the spec (or a new subsection to an existing one):

    ## Review log

    ### 2026-10-22 — expert-panel (Pike, Cheney, Ford, Stonebraker, Valsorda)
    Принято: C2 — добавлено поведение при недоступности каталога; S1 — схема
    переведена на составной ключ.
    Отклонено: F3 — вынос в отдельный сервис. Причина: преждевременно,
    объём не оправдан.
    Не рассмотрено: P6, V4.

Take the date from the system environment, the panel composition — the actual one.

Rejections with a reason matter more than acceptances: the next run reads the log and does not reopen closed questions.

## Completion

Do not commit. Tell the user the spec is updated and ready for planning. Do not invoke `writing-plans` yourself.
