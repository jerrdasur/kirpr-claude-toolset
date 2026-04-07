# kirpr -- slash-команды для Claude Code

Набор из 8 команд для Claude Code. Решают две задачи: декомпозиция задач из трекера (YouTrack, Jira) на подзадачи со спецификациями и работа с Architecture Decision Records.

Команды устанавливаются в `~/.claude/` и становятся доступны через `/kirpr:*` в любом проекте.

## Что внутри

### Декомпозиция задач

| Команда | Что делает |
|---------|-----------|
| `/kirpr:task-fetch SAS-200` | Загружает данные задачи из трекера: описание, комментарии, связанные задачи, историю изменений |
| `/kirpr:tasks-decompose SAS-200` | Разбивает задачу на подзадачи через 5 фаз: загрузка данных, анализ контекста с разработчиком, дискуссия по структуре, верификация по чеклисту, генерация md-файлов |
| `/kirpr:tasks-review SAS-200` | Проверяет готовую декомпозицию по 4 категориям (неоднозначности, противоречия, пропуски, риски), выставляет quality score каждой подзадаче и итеративно поднимает качество |
| `/kirpr:tasks-adapt SAS-200` | Обновляет декомпозицию при изменении требований. Находит затронутые файлы, предлагает правки, не трогает остальное |

### Architecture Decision Records

| Команда | Что делает |
|---------|-----------|
| `/kirpr:adr-init` | Настраивает ADR-инфраструктуру в репозитории: services map, decision drivers, интеграция с документацией, калибровочные примеры для self-review. Результат записывается в `CLAUDE.md` |
| `/kirpr:adr-write SAS-200` | Пишет ADR через архитектурную дискуссию: сбор контекста из трекера и кодовой базы, анализ альтернатив, генерация драфта, обязательный self-review по рубрике K1-K6 |
| `/kirpr:adr-review SAS-200` | Рецензирует ADR с кросс-сервисным анализом. Проверяет по 7 критериям (R1-R7), выдает светофорный отчет. Сверяет ADR с кодовой базой и данными из трекера |

### Редактура текста

| Команда | Что делает |
|---------|-----------|
| `/kirpr:text` | Запускает агент-редактор в стиле информационного текста (Ильяхов). Пишет и редактирует тексты с упором на ясность, факты и лаконичность |

## Установка

### Из интернета (одна команда)

```bash
curl -fsSL https://raw.githubusercontent.com/jerrdasur/kirpr-claude-toolset/main/install-remote.sh | sh
```

### Из локального клона

```bash
git clone git@github.com:jerrdasur/kirpr-claude-toolset.git ~/claude-toolset
cd ~/claude-toolset
./install.sh
```

Установщик копирует файлы в `~/.claude/commands/kirpr/` и `~/.claude/kirpr/`, затем предлагает выбрать трекер (YouTrack, Jira или пропустить). При повторном запуске конфигурация трекера сохраняется.

### Зависимости

- **Claude Code** -- команды работают как slash-commands внутри Claude Code
- **Python 3** -- скрипты загрузки задач из трекеров написаны на Python, без внешних зависимостей (только stdlib)

## Настройка трекера

Установщик предлагает настроить трекер при первом запуске. Если пропустили -- отредактируйте файл `~/.claude/kirpr/config/tracker.md` вручную (шаблон: `kirpr/config/tracker.md.template`).

### YouTrack

```bash
export YOUTRACK_URL=https://youtrack.example.com
export YOUTRACK_TOKEN=<bearer-токен>
```

### Jira

```bash
export JIRA_URL=https://yourcompany.atlassian.net
export JIRA_TOKEN=<api-токен>
export JIRA_EMAIL=you@example.com  # для Jira Cloud (basic auth)
```

## Обновление

```bash
curl -fsSL https://raw.githubusercontent.com/jerrdasur/kirpr-claude-toolset/main/install-remote.sh | sh
```

Или из локального клона:

```bash
cd ~/claude-toolset && git pull && ./install.sh
```

## Удаление

```bash
./uninstall.sh
```

Удаляет все файлы. Предложит сохранить конфигурацию трекера.

## Структура проекта

```
commands/kirpr/          -- промпты slash-команд (копируются в ~/.claude/commands/kirpr/)
kirpr/
  config/                -- конфиги: workflow, шаблоны, рубрики оценки, правила агентов
  scripts/               -- Python-скрипты для загрузки задач из YouTrack и Jira
  prompts/               -- системные промпты (текстовый редактор)
install.sh               -- локальная установка
install-remote.sh        -- установка из GitHub без клонирования
uninstall.sh             -- удаление
```

## Лицензия

Open source. Свободное использование.
