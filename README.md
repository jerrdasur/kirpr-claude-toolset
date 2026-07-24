# kirpr — slash-команды для Claude Code

Декомпозиция задач из трекера, Architecture Decision Records, редактура текстов и ревью панелью экспертов — 9 команд и один скил для Claude Code.

## Команды

### Декомпозиция задач

| Команда | Что делает |
|---------|-----------|
| `/kirpr:task-fetch SAS-200` | Загружает задачу из трекера: описание, комментарии, связи, историю |
| `/kirpr:tasks-decompose SAS-200` | Разбивает задачу на подзадачи: загрузка данных → анализ с разработчиком → структура → верификация → md-файлы |
| `/kirpr:tasks-review SAS-200` | Проверяет декомпозицию по 4 категориям (неоднозначности, противоречия, пропуски, риски), выставляет quality score и итеративно поднимает качество |
| `/kirpr:tasks-adapt SAS-200` | Обновляет декомпозицию при изменении требований. Находит затронутые подзадачи, предлагает правки, остальное не трогает |
| `/kirpr:tasks-push SAS-200` | Создаёт подзадачи из декомпозиции в YouTrack: строит план → dry-run preview → подтверждение → создание с иерархией и зависимостями. Идемпотентно (`.created.json`) |

### Architecture Decision Records

| Команда | Что делает |
|---------|-----------|
| `/kirpr:adr-init` | Настраивает ADR-инфраструктуру в репозитории: services map, decision drivers, калибровочные примеры. Результат — в `CLAUDE.md` |
| `/kirpr:adr-write SAS-200` | Пишет ADR: собирает контекст из трекера и кода, анализирует альтернативы, генерирует драфт, проводит self-review по рубрике K1–K6 |
| `/kirpr:adr-review SAS-200` | Рецензирует ADR по 7 критериям (R1–R7) с кросс-сервисным анализом. Сверяет с кодовой базой и данными трекера, выдаёт светофорный отчёт |

### Редактура текста

| Команда | Что делает |
|---------|-----------|
| `/kirpr:text` | Пишет и редактирует тексты в информационном стиле (Ильяхов): ясность, факты, лаконичность |

### Ревью панелью экспертов

Скил `expert-panel` прогоняет артефакт через панель экспертов — по параллельному агенту на каждого, затем сводит замечания и ведёт разбор.

| Вызов | Что делает |
|-------|-----------|
| `/expert-panel spec docs/superpowers/specs/2026-07-24-foo-design.md` | Критическое ревью спеки перед планированием: отчёт → ваш разбор `accept`/`reject` → правки в спеке → запись в `## Review log` |
| `/expert-panel diff` | Ревью рабочего дерева против `HEAD` |
| `/expert-panel diff main` | Ревью против ветки, с проверкой актуальности базы |
| `/expert-panel diff --spec <путь>` | То же плюс сверка кода со спекой: что не реализовано, что сделано сверх, какие решения нарушены |

Ядро панели: Rob Pike (простота), Dave Cheney (границы и зависимости), Neal Ford (trade-offs и обратимость), Michael Stonebraker (данные и хранилище). Чеклисты заточены под Go.

Панель настраивается в `~/.claude/skills/expert-panel/custom-experts.md` — этот файл не перезаписывается при обновлении. Строка `disable: stonebraker` убирает ядерного эксперта, секция `## Имя — Домен` добавляет своего. Формат описан в самом файле.

Опционально: `.claude/expert-panel-ignore` в репозитории проекта задаёт glob-шаблоны файлов, которые панель не смотрит, — генерируемый код у каждой команды свой.

## Установка

### Из интернета

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

- **Claude Code** — команды работают как slash-commands внутри Claude Code
- **Python 3** — скрипты загрузки задач из трекеров (только stdlib, без внешних зависимостей)

## Настройка трекера

Установщик настраивает трекер при первом запуске. Пропустили — отредактируйте `~/.claude/kirpr/config/tracker.md` (шаблон: `kirpr/config/tracker.md.template`).

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

Из локального клона:

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
commands/kirpr/          — промпты slash-команд (→ ~/.claude/commands/kirpr/)
kirpr/
  config/                — конфиги: workflow, шаблоны, рубрики, правила агентов
  prompts/               — системные промпты (редактор текста)
  scripts/               — Python-скрипты для YouTrack и Jira
skills/expert-panel/     — скил ревью панелью (→ ~/.claude/skills/expert-panel/)
  SKILL.md               — роутер, реестр ядра, severity, синтез
  experts/               — персоны ядра
  modes/                 — протоколы режимов: спека и diff
  custom-experts.md      — пользовательские эксперты (не перезаписывается)
install.sh               — локальная установка
install-remote.sh        — установка из GitHub
uninstall.sh             — удаление
```

## Лицензия

Open source. Свободное использование.
