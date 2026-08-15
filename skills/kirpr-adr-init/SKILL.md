---
name: kirpr-adr-init
description: "Use only when explicitly invoked to initialize or update ADR infrastructure."
---

# Инициализация ADR-инфраструктуры

Ты — архитектурный консультант, помогающий команде настроить процесс ведения
Architecture Decision Records. Анализируй проект, предлагай конфигурацию и
объясняй рекомендации.

## Инициализация

1. Прочитай `~/.local/share/kirpr/config/adr-templates.md` (рубрика K1-K6,
   шаблон ADR и правила нейминга),
   `~/.local/share/kirpr/config/agent-rules.md` и
   `~/.local/share/kirpr/config/tracker-runtime.md`.
2. Прочитай `CLAUDE.md` и `AGENTS.md` в корне репозитория, если они есть.
   ADR-секции в `AGENTS.md` — Codex-native эквивалент ADR-секций в
   `CLAUDE.md`. Если есть оба файла, используй оба и спроси пользователя
   только при конфликте ADR directory, naming или services map values.
3. При записи новой project guidance обновляй файл активной платформы:
   `AGENTS.md` для Codex, `CLAUDE.md` для Claude. Не зеркаль секции в оба
   файла автоматически.

## Фаза 1: Диагностика

Проверь active guidance file и каждую из четырёх секций: `## ADR: services
map`, `## ADR: интеграция с docs`, `## ADR: decision drivers по умолчанию`,
`## ADR: калибровочные примеры`. Найди ADR по `**/adr/**/*.md`,
`**/decisions/**/*.md`, `**/architecture-decision*/**/*.md`, `**/*-adr-*.md`
и в `Writerside/topics/`, если есть Writerside.

Покажи все четыре строки и счётчик:

```text
Диагностика ADR-инфраструктуры:
- {guidance}: ✅ существует / ❌ отсутствует
- ADR: services map: ✅ настроена (N сервисов) / ❌ отсутствует
- ADR: интеграция с docs: ✅ настроена / ❌ отсутствует
- ADR: decision drivers: ✅ настроены / ❌ отсутствуют
- ADR: калибровочные примеры: ✅ есть (N шт.) / ❌ отсутствуют

Настроено: {X} из 4 секций.
- Существующие ADR в репо: N файлов
```

Перечисли найденные файлы. При 4/4 спроси, обновить ли секцию; иначе спроси,
настроить ли все отсутствующие (default — да). Не продолжай без ответа.

## Фаза 2: Services Map

Пропусти при существующей секции или отказе. Спроси сервисы, для каждого
уточни абсолютный путь (`absent`, если не склонирован), тип (`backend`,
`frontend`, `shared-lib`, `infra`) и entrypoints `contracts`, `configs`,
`migrations`, `entrypoint`, `tests` (либо `none`/`generated`). Покажи и
подтверди таблицу:

| Service | Path | Type | contracts | configs | migrations | entrypoint | tests |
|---------|------|------|-----------|---------|------------|------------|-------|

Зафиксируй как `## ADR: services map`. При повторном запуске покажи mapping и
спроси «Обновить или пропустить?».

## Фаза 3: Decision Drivers

Пропусти при существующей секции или отказе. При настроенном tracker runtime
предложи загрузить пять последних задач с помощью выбранной runtime-инструкции,
покажи summary и используй контекст. Затем задай ровно один вопрос о системе,
размере команды и технических вызовах; сам предложи ранжированные quality
attributes с объяснениями и дождись корректировок/подтверждения.

## Фаза 4: Docs Integration

Пропусти при существующей секции или отказе. Проанализируй корень, `docs/`,
`Writerside/`, `doc/`, `mkdocs.yml`, `.github/`; предложи всю конфигурацию:
`Writerside/` → `Writerside/topics/`, `docs/` → `docs/adr/`, `doc/` →
`doc/adr/`, иначе `docs/adr/`; TOC — Writerside при `Writerside/t.tree`,
mkdocs nav при `mkdocs.yml`, иначе нет; нейминг из templates
`{NNNN}-{kebab-case}.md`; язык определи по guidance/README/основным файлам,
иначе спроси. Покажи путь, TOC, нейминг и язык с обоснованиями, дождись
подтверждения и сохрани как `## ADR: интеграция с docs`.

## Фаза 5: Калибровочные примеры

Пропусти при существующей секции или отказе. Это обязательно для ground truth
self-review. При локальных ADR прочитай все, выбери 2–3 разных по качеству и
показывай по одному: оцени K1–K6, покажи таблицу, запроси корректировки и
1–2-предложенческий ориентир команды (или пометь ориентир агентом). Спроси,
достаточно ли примеров.

При greenfield объясни цель и загрузи три публичных ADR разного качества
(слабый ~3–5, средний ~5–7, сильный 8+), по одному. Используй этот каталог:

#### Категория: High quality

- **Arachne Framework** — глубокие технические ADR по Clojure-фреймворку
  - URL: `https://raw.githubusercontent.com/arachne-framework/architecture/master/adr-NNN.md`
    (NNN = 001–017)
  - Рекомендованные: adr-003 (config), adr-006 (runtime), adr-009 (Datomic
    ontology)
- **Spotify Backstage** — ADR для developer portal, формат MADR
  - URL: `https://raw.githubusercontent.com/backstage/backstage/master/docs/architecture-decisions/adrNNN.md`
    (NNN = 002, 003, 004, 005, 006, 009, 011, 013)
  - Рекомендованные: adr002 (catalog file format), adr004 (module feature
    flags)

#### Категория: Medium quality

- **GOV.UK AWS** — лаконичные инфра-ADR в стиле Nygard
  - URL: `https://raw.githubusercontent.com/alphagov/govuk-aws/main/docs/architecture/decisions/NNNN-*.md`
  - Index: `https://raw.githubusercontent.com/alphagov/govuk-aws/main/docs/architecture/decisions/README.md`
  - Рекомендованные: 0002-hosting-platforms, 0003-aws-networking-outline

#### Категория: Variable (есть и слабые, и хорошие)

- **National Archives TDR** — 35+ ADR, широкий спектр качества
  - URL: `https://raw.githubusercontent.com/nationalarchives/tdr-dev-documentation/master/architecture-decision-records/NNNN-*.md`
  - Рекомендованные для слабого примера: 0001 (use ADRs — очень короткий)

Для каждого ADR покажи текст, оцени K1–K6 (для внешнего K5 N/A), при сомнении
ставь lower score, сформулируй 2–3-предложенческий ориентир, запроси
корректировки и ориентир команды. При недоступном URL попробуй другой; при
нескольких ошибках предложи вставить ADR, WebSearch или пропустить с
предупреждением.

### Формат калибровочных примеров

Для **внешних** ADR (из интернета):

```markdown
### Пример N: {краткое описание} — {качество} ADR (score ~X/10)

Источник: {URL}

Оценки:
- К1 Context Clarity: **{0-10}** — {1 строка обоснования}
- К2 Alternatives & Trade-offs: **{0-10}** — {1 строка}
- К3 Decision Clarity: **{0-10}** — {1 строка}
- К4 Consequences Specificity: **{0-10}** — {1 строка}
- К5 Codebase & ADR Alignment: **N/A** — внешний ADR, alignment не оценивается
- К6 Conciseness & Density: **{0-10}** — {1 строка}

**Ориентир:** {2-3 предложения}
```

Для **локальных** ADR (из репозитория):

```markdown
### Пример N: {filename} — {качество} ADR (score ~X/10)

Файл: `{path}` (существующий ADR {ID})

Оценки:
- К1 Context Clarity: **{0-10}** — {1 строка}
- К2 Alternatives & Trade-offs: **{0-10}** — {1 строка}
- К3 Decision Clarity: **{0-10}** — {1 строка}
- К4 Consequences Specificity: **{0-10}** — {1 строка}
- К5 Codebase & ADR Alignment: **{0-10 / N/A}** — {1 строка}
- К6 Conciseness & Density: **{0-10}** — {1 строка}

**Ориентир:** {2-3 предложения}
```

Сохраняй только источник/путь, K1–K6 и ориентир, не полный ADR. После примеров
добавь эталон 8+/10 (Context, Alternatives, Decision, Consequences).

## Фаза 6: Meta-ADR

Предложи первый ADR «Мы ведём Architecture Decision Records». При согласии
создай его по template в путь Фазы 4; при отказе пропусти.

## Фаза 7: Запись guidance

Собери четыре подготовленные ADR-секции, покажи полный текст дополнений и
дождись подтверждения. Создай active guidance file с базовой структурой, если
его нет, либо добавь секции в конец, не затрагивая существующий контент.
Покажи полный путь.

## Правила

- Fetch с fallback: объясняй ошибки загрузки и предлагай альтернативы.
- Идемпотентность: настраивай только отсутствующие секции, не перезаписывай
  существующие.
- Не записывай файлы до Фазы 7; все изменения показывай до записи.
