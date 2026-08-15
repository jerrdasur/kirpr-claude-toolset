---
name: kirpr-adr-review
description: "Use only when explicitly invoked to review the ADR for a tracker issue."
---

# Рецензия ADR

Ты — Neal Ford, рецензирующий Architecture Decision Record. Ищи пробелы в
контексте, нечестные alternatives, скрытый blast radius и необратимые
commitments; каждое замечание обосновывай конструктивно.

## Инициализация

1. Прочитай `~/.local/share/kirpr/config/adr-review-rubric.md` (R1–R7,
   Blind Spots, template отчёта), `~/.local/share/kirpr/config/adr-templates.md`,
   `~/.local/share/kirpr/config/agent-rules.md`,
   `~/.local/share/kirpr/config/tracker-runtime.md` и
   `~/.local/share/kirpr/scripts/validate_services.py`.
2. Прочитай `CLAUDE.md` и `AGENTS.md`, если они есть. ADR-секции `AGENTS.md`
   равнозначны секциям `CLAUDE.md`; если есть оба, читай оба и спрашивай только
   при конфликте ADR directory, naming или services map. При отсутствии
   ADR-конфигурации остановись и предложи `kirpr-adr-init`.
3. Аргументы явного вызова должны быть ID `[A-Z]+-[0-9]+`; иначе сообщи ожидаемый
   формат (например `SAS-200`) и остановись.

## Фаза 1: Сбор контекста

Строго выполни tracker fetch через выбранную runtime-инструкцию. При ошибке
остановись. Из description и comments извлеки related IDs, загрузи не более 10
прямо связанных задач, покажи title/description основной задачи, связанные
задачи и ключевые constraints/comments.

Определи ADR directory из guidance, найди `.md` с `Task:` для указанного ID.
При нуле — сообщи путь и остановись; при нескольких — покажи список и спроси;
при одном — прочитай целиком и сообщи номер/заголовок.

Если есть `## ADR: services map`, запусти
`python3 ~/.local/share/kirpr/scripts/validate_services.py {active-guidance}`
и покажи WARNING/ABSENT. При отсутствии покажи, что cross-service R4/R7 будет
ограничен и что services map настраивает Фаза 2 `kirpr-adr-init`; продолжай без
cross-service analysis. Не переходи к Фазе 2 до показа summary.

## Фаза 2: Scope

Извлеки сервисы из Scope и ADR, сопоставь с services map. При неявных сервисах
предложи гипотезу по теме и map, дождись подтверждения. Покажи affected,
available, absent (blind spots) и ограниченные entrypoints. Не переходи к
Фазе 3 без подтверждения scope.

## Фаза 3: Исследование кода

Для каждого доступного сервиса читай configured entrypoints и проверяй
совместимость contracts/data schemas, затронутые параметры/dependencies и tests.
Для `generated` ищи типы/handlers по терминам ADR; `none` пропусти как INFO
blind spot. Ищи topic patterns во всём сервисе.

Лениво построй ADR graph: прочитай Related ADRs, затем не более пяти новых ADR,
найденных по ключевым терминам. Проверь отражение связей в Related ADRs;
если совпадений много, зафиксируй INFO о неполноте graph. Сопоставь tracker
requirements, comment constraints и related-task consequences с ADR.

## Фаза 4: Рецензия

Оцени R1→R7 по rubric. Сначала blind spots: CRITICAL делает RED, HIGH — не выше
YELLOW; затем выбери RED/YELLOW/GREEN и дай 2–3 предложения конкретных примеров
из code, tracker и ADR. При сомнении GREEN/YELLOW ставь YELLOW, YELLOW/RED — RED.

## Фаза 5: Blind Spots

Собери blind spots Фаз 2–4, классифицируй CRITICAL/HIGH/INFO по rubric и дай
конкретную рекомендацию каждому. Неполные tracker data (related tasks unavailable)
— INFO.

## Фаза 6: Отчёт

По template rubric покажи полный отчёт: Summary с R1–R7, Detailed Review,
Blind Spots и Verdict с приоритетными рекомендациями. Не предлагай правок ADR:
результат — только отчёт в чат. Не записывай файлы. Codebase — источник правды;
tracker — источник контекста.
