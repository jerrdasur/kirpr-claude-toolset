# Примеры стиля декомпозиции

> Используй эти примеры как образец стиля, гранулярности и формата при создании новых декомпозиций.
> Примеры взяты из sas-112/ (декомпозиция задачи SAS-112 "Страница Feed").
> **Примечание:** sas-111/ использует устаревший `sp-` префикс в именах файлов — это legacy, не повторяй.

---

## Пример 1: 00-overview.md (навигационный индекс)

```markdown
# Страница Feed (бэкенд) — Обзор и навигация

> Этот файл — навигационный индекс. Каждая задача самодостаточна и ссылается только на `SAS-112` и предыдущие задачи.

## Внешние зависимости

SAS-112 зависит от задач из SAS-111:
- **SAS-115** (DDL) — добавляет трёхслойные поля severity/status в issues, таблицу `issueHistory`
- **SAS-116** (codegen) — генерирует модели для расширенной схемы

## Граф зависимостей

[SAS-115] ──> [SAS-116] ──> 1.1 ──> 2.1 ──> 3.1 ──> 4.1
                                      │       │
                                      │       └──> 3.2 ──> 4.2
                                      │
                                      └──> 3.3 ──> 4.3

**Параллельные потоки** после 2.1:
- Поток A: 3.1 → 4.1 (Feed listing)
- Поток B: 3.2 → 4.2 (Issue detail + occurences)
- Поток C: 3.3 → 4.3 (Actions + comments)

## Карта задач по файлам

| Файл | Задача |
|------|--------|
| `01-schema.md` | 1.1 — DDL: расширение issues + repositories |
| `02-1-domain-models.md` | 2.1 — Codegen + domain models |
| `03-1-feed-listing.md` | 3.1 — Feed listing: manager |

## Итого

- **8 задач**, каждая <= 4 часов
- **~21 час** суммарно
```

---

## Пример 2: Простая подзадача (01-schema.md)

```markdown
## Задача 1.1 — DDL: расширение issues + repositories [apisrv, ~2ч]

Расширить схему БД для поддержки Snooze/Ignore действий и workspace-level Feed.

### 1. Расширение таблицы `issues`

Добавить колонки:

ALTER TABLE "public"."issues" ADD COLUMN "snoozedUntil" timestamptz;
ALTER TABLE "public"."issues" ADD COLUMN "snoozedByUserId" integer;
ALTER TABLE "public"."issues" ADD COLUMN "ignoreReason" varchar(500);

- `snoozedUntil` — до какого момента issue заснужен. NULL = не заснужен.
- `snoozedByUserId` — ID пользователя, который заснузил. NULL = не заснужен.
- `ignoreReason` — причина игнорирования. NULL = не заигнорен.

### 2. Добавить `defaultBranchId` в `repositories`

ALTER TABLE "public"."repositories" ADD COLUMN "defaultBranchId" integer;
ALTER TABLE "public"."repositories" ADD CONSTRAINT "fk_repositories_defaultBranch"
    FOREIGN KEY ("defaultBranchId") REFERENCES "public"."repositoryBranches"("repositoryBranchId");

### 3. Обновить `apisrv.dbs`

Внести все изменения в DBSchema файл, затем регенерировать `docs/apisrv.sql`.

Критерий готовности: `apisrv.sql` содержит новые колонки, FK constraint для `defaultBranchId`, схема валидна.
```

---

## Пример 3: Сложная подзадача (03-1-feed-listing.md)

```markdown
## Задача 3.1 — Feed listing: manager [apisrv, ~4ч]

Создать `apisrv/pkg/sast/manager_feed.go` — бизнес-логика для workspace-level Feed с группировкой issues по vulnerability.

**Зависимость:** задача 2.1 (domain models), SAS-111 задачи 3.1-3.2 (effective values, issueHistory).

### Ключевая идея

Feed показывает issues, сгруппированные по первому `vulnerabilityAlias` из `rule.vulnerabilityAliases`. Каждая строка Feed = одна vulnerability.

### 1. `ListFeed(ctx, user User, search FeedSearch, page int, pageSize int) (FeedItems, int, error)`

**Алгоритм:**
1. Валидация: `pageSize` в диапазоне 1-100.
2. Получить все `repositoryBranchIds` для workspace пользователя.
3. Выполнить агрегирующий SQL-запрос с GROUP BY vulnerability.
4. Загрузить `FullIssue` для каждого `latest_issue_id`.
5. Собрать `FeedItems` и вернуть с total count.

### 2. `SeveritySummary(ctx, user User, workspaceID int) (*SeveritySummary, error)`

Агрегация issues по effective severity для хедера.

### 3. `FeedFilters(ctx, user User, workspaceID int) (*FeedFilterOptions, error)`

type FeedFilterOptions struct {
    Severities []FilterOptionString
    IssueTypes []FilterOptionString
    Locations  []FilterOptionInt
}

Критерий готовности: `ListFeed` возвращает сгруппированные items, `SeveritySummary` считает Current issues, `FeedFilters` возвращает актуальные locations.
```
