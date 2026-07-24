# expert-panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Оформить панель экспертов (Pike, Cheney, Ford, Stonebraker) как самодостаточный скил Claude Code с двумя режимами — ревью спеки и ревью git diff — и научить установщики репозитория его распространять.

**Architecture:** Папка `skills/expert-panel/` с `SKILL.md`-роутером, файлами персон в `experts/`, протоколами режимов в `modes/` и пользовательским overlay `custom-experts.md`. Оркестратор собирает активную панель, запускает по параллельному агенту на эксперта, синтезирует замечания и ведёт интерактивный разбор. Установщики копируют папку в `~/.claude/skills/expert-panel/`, сохраняя overlay между обновлениями.

**Tech Stack:** Markdown (скилы Claude Code), bash (установщики), Python 3 stdlib + `unittest` (существующие тесты, не трогаем).

## Global Constraints

- **Только Go.** Чеклисты персон заточены под Go-сервисы. Языко-агностичных формулировок не добавлять.
- **Самодостаточность.** Ни один файл скила не ссылается на `~/.claude/kirpr/`.
- **Скил, не команда.** Файлов в `commands/kirpr/` не создавать.
- **Overlay переживает обновление.** `custom-experts.md` не перезаписывается ни `install.sh`, ни `install-remote.sh`.
- **Язык файлов — русский**, как во всех промптах репозитория. Цитаты экспертов — на языке оригинала.
- **Без автотестов на скил.** Верификация markdown-задач — структурные проверки командами из шагов.
- **Никаких обращений к трекеру** из файлов скила.
- **Имя скила:** `expert-panel`, без префикса.
- Идентификаторы ядра: `pike`, `cheney`, `ford`, `stonebraker`. Префиксы замечаний: `P`, `C`, `F`, `S`.
- Маркер начала пользовательских секций в overlay: `<!-- BEGIN EXPERTS -->` (точное написание).

## File Structure

| Файл | Ответственность |
|---|---|
| `skills/expert-panel/SKILL.md` | фронтматтер, разбор аргументов и роутинг, сборка активной панели, протокол запуска агентов, схема замечания, синтез, severity |
| `skills/expert-panel/custom-experts.md` | шаблон overlay: инструкция + маркер `<!-- BEGIN EXPERTS -->` |
| `skills/expert-panel/experts/pike.md` | персона Rob Pike |
| `skills/expert-panel/experts/cheney.md` | персона Dave Cheney |
| `skills/expert-panel/experts/ford.md` | персона Neal Ford |
| `skills/expert-panel/experts/stonebraker.md` | персона Michael Stonebraker |
| `skills/expert-panel/modes/spec.md` | протокол ревью спеки, фазы 1–6 |
| `skills/expert-panel/modes/diff.md` | протокол ревью diff, preflight и вердикт |
| `install.sh` | установка скила из локального клона + сохранение overlay |
| `uninstall.sh` | удаление скила + сохранение overlay |
| `install-remote.sh` | установка скила из GitHub + сохранение overlay + фикс четырёх недостающих файлов |
| `README.md` | раздел про скил, обновлённая структура проекта |

Персоны живут по файлу на эксперта, потому что оркестратор их не читает — он передаёт агенту путь. Один общий файл заставил бы агента вычитывать четыре чужие персоны ради своей.

---

### Task 1: Каркас скила — SKILL.md и шаблон overlay

**Files:**
- Create: `skills/expert-panel/SKILL.md`
- Create: `skills/expert-panel/custom-experts.md`

**Interfaces:**
- Consumes: ничего.
- Produces: контракты, на которые опираются задачи 2–4 — схема замечания (поля `id`, `severity`, `место`, `суть`, `почему`, `правка`), префиксы `P`/`C`/`F`/`S`, маркер `<!-- BEGIN EXPERTS -->`, имена файлов режимов `modes/spec.md` и `modes/diff.md`, имена файлов персон `experts/<id>.md`.

- [ ] **Step 1: Создать `skills/expert-panel/SKILL.md`**

````markdown
---
name: expert-panel
description: "Мульти-персонное ревью Go-проектов панелью экспертов (Rob Pike, Dave Cheney, Neal Ford, Michael Stonebraker плюс пользовательские). Два режима: ревью спеки перед планированием и ревью git diff перед коммитом. Вызывается только явно: /expert-panel spec <путь> или /expert-panel diff [база]."
---

# expert-panel — ревью панелью экспертов

Прогоняет артефакт через панель экспертов. Каждый эксперт — отдельный агент со своим взглядом, оркестратор сводит результаты и ведёт разбор с пользователем.

Запускается только по явному вызову. Панель дорогая: параллельные агенты на каждого эксперта.

## Разбор аргументов

- `spec [путь]` — ревью спеки. Читай `modes/spec.md` и следуй ему.
- `diff [база] [--spec путь]` — ревью изменений. Читай `modes/diff.md` и следуй ему.
- Аргументов нет или формат не распознан — спроси, какой режим нужен. Не угадывай.

Пути к `modes/*.md` и `experts/*.md` — относительно каталога этого файла.

## Сборка активной панели

1. Ядро: `experts/pike.md`, `experts/cheney.md`, `experts/ford.md`, `experts/stonebraker.md`. Идентификаторы: `pike`, `cheney`, `ford`, `stonebraker`.
2. Прочитай `custom-experts.md`, если он есть. Учитывай только то, что идёт **после** строки `<!-- BEGIN EXPERTS -->`:
   - строка `disable: <id>` убирает ядерного эксперта из панели;
   - каждая секция `## <Имя> — <Домен>` добавляет эксперта.
   Всё, что выше маркера, — инструкция для человека. Игнорируй её целиком.
3. Если активных экспертов не осталось — сообщи об этом и прерви работу.
4. Покажи состав панели одной строкой перед запуском: «Панель: Pike, Cheney, Ford, Stonebraker».

## Запуск агентов

Один агент на эксперта. Все агенты запускаются одним сообщением, чтобы работать параллельно.

В промпт агента входит:

- Роль: «Ты — <Имя>. Прочитай файл `<абсолютный путь к experts/<id>.md>` и ревьюй строго по нему.» Для эксперта из overlay текст его секции передаётся прямо в промпте — файла у него нет.
- Режим: `спека` или `diff` — агент использует соответствующий чеклист своей персоны.
- Артефакт: абсолютный путь к спеке либо путь к файлу с сохранённым diff.
- Релевантные пути в репозитории, собранные оркестратором.
- Ограничение: только чтение. Агент не редактирует файлы, не запускает тесты, не делает коммитов.
- Схема ответа (ниже).

Файлы персон оркестратор не читает — они нужны только агентам.

## Схема замечания

Агент возвращает список замечаний. Каждое — шесть полей:

- `id` — префикс эксперта плюс порядковый номер: `P1`, `C2`, `F3`, `S1`. Префиксы ядра: Pike — `P`, Cheney — `C`, Ford — `F`, Stonebraker — `S`. Для эксперта из overlay — первая буква фамилии; при коллизии с занятой буквой — две первые.
- `severity` — `blocker`, `major`, `minor` или `nit`.
- `место` — раздел спеки либо `file:line`.
- `суть` — одно предложение.
- `почему` — чем это грозит.
- `правка` — что конкретно изменить.

**Замечание без поля «правка» не принимается.** «Тут неясно» — не замечание. «В разделе X не описано поведение при недоступности Y; добавить абзац с ответом сервиса и поведением клиента» — замечание. Такие ответы агента отбрасывай при синтезе.

Отдельно агент возвращает список удачных решений — что сделано правильно. Минимум одно, если есть за что.

## Severity

| | В спеке | В diff |
|---|---|---|
| `blocker` | ведёт к переделке: неверная модель данных, невыполнимое требование, внутреннее противоречие | баг, уязвимость, потеря данных |
| `major` | существенный пробел: не описан отказ, миграция, граница ответственности | архитектурная проблема, неверная логика |
| `minor` | уточнение, экономящее вопросы на этапе плана | улучшение, некритично |
| `nit` | формулировка | стиль, нейминг |

## Синтез

1. **Дедуп.** Замечания об одном месте с одной сутью сливаются в одно. Авторы перечисляются через запятую, severity берётся максимальный, поле «правка» — самое конкретное из предложенных.
2. **Конфликты.** Если два замечания требуют взаимоисключающих правок одного места — это не дефект, а развилка. Выноси парой в блок «Конфликты» с позицией каждого эксперта. Вердикт по конфликту выносит пользователь, а не оркестратор.
3. **Лимиты.** Полностью показывай не больше 3 `blocker` и 5 `major` — самые тяжёлые. Остальные сворачивай в одну строку каждое, под заголовком «Ниже порога». Отчёт нужен для решений, а не для объёма.
4. **Нумерация** сохраняется от агентов: пользователь ссылается на `C2`, а не на «второе сверху».

## Общие правила

- Ничего не пишет на диск, пока пользователь явно не принял замечания.
- Не запускает тесты, линтеры и сборку. Если проверка нужна — выводит команду, которую пользователь запустит сам.
- Не делает коммитов.
- Не переходит между фазами режима без подтверждения там, где фаза этого требует.
- При сомнении в severity выбирает более высокий.
````

- [ ] **Step 2: Проверить фронтматтер и структуру SKILL.md**

Run:
```bash
head -4 skills/expert-panel/SKILL.md
for s in "## Разбор аргументов" "## Сборка активной панели" "## Запуск агентов" "## Схема замечания" "## Severity" "## Синтез" "## Общие правила"; do
  grep -qF "$s" skills/expert-panel/SKILL.md || echo "MISSING SECTION: $s"
done
grep -c "kirpr" skills/expert-panel/SKILL.md
```
Expected: первая строка `---`, вторая `name: expert-panel`; ни одной строки `MISSING SECTION`; последняя команда печатает `0` (самодостаточность — ссылок на kirpr нет).

- [ ] **Step 3: Создать `skills/expert-panel/custom-experts.md`**

````markdown
# Пользовательские эксперты

Файл не перезаписывается при обновлении скила. Правьте свободно.

Скил учитывает только то, что идёт **после** строки-маркера в самом конце файла. Всё выше — инструкция, она игнорируется.

Литерал маркера в этом файле встречается ровно один раз — последней строкой. Иначе правило «всё после маркера» становится двусмысленным и инструкция попадает в панель как эксперты.

## Отключить ядерного эксперта

Строка `disable: <id>` после маркера убирает эксперта из панели. Идентификаторы ядра: `pike`, `cheney`, `ford`, `stonebraker`.

    disable: stonebraker

## Добавить своего эксперта

Секция второго уровня вида `## <Имя> — <Домен>` после маркера. Структура — как у ядра, образец: `experts/pike.md`. Обязательные блоки: цитата, «Кто», «Как ревьюит», «Характерные вопросы», «В спеке проверяет», «В diff проверяет».

Образец:

    ## Filippo Valsorda — безопасность

    > "Every input is hostile until proven otherwise."

    **Кто.** Криптограф, бывший security lead команды Go, автор age. Не верит
    никаким входным данным.

    **Как ревьюит.** Ищет границы доверия: где данные приходят извне и где
    используются без проверки.

    **Характерные вопросы:**
    - Кто проверяет, что пользователь имеет доступ именно к этому ресурсу?
    - Куда утечёт этот токен, если сервис упадёт с паникой?

    **В спеке проверяет:**
    - Названы ли границы доверия и источники недоверенных данных
    - Описана ли авторизация, а не только аутентификация

    **В diff проверяет:**
    - SQL-инъекции в запросах, собранных вручную
    - IDOR: проверяются ли права на объект, а не только вход
    - Не логируются ли пароли, токены, персональные данные

<!-- BEGIN EXPERTS -->
````

- [ ] **Step 4: Проверить, что образец из инструкции не попадает в панель**

Run:
```bash
awk '/<!-- BEGIN EXPERTS -->/{found=1; next} found' skills/expert-panel/custom-experts.md | grep -c "^## " || true
grep -c "^## Filippo" skills/expert-panel/custom-experts.md
```
Expected: первая команда печатает `0` (после маркера нет ни одной активной секции эксперта); вторая — `0` (образец лежит в отступе, а не заголовком).

- [ ] **Step 5: Коммит**

```bash
git add skills/expert-panel/SKILL.md skills/expert-panel/custom-experts.md
git commit -m "feat(expert-panel): каркас скила и шаблон overlay"
```

---

### Task 2: Персоны ядра

**Files:**
- Create: `skills/expert-panel/experts/pike.md`
- Create: `skills/expert-panel/experts/cheney.md`
- Create: `skills/expert-panel/experts/ford.md`
- Create: `skills/expert-panel/experts/stonebraker.md`

**Interfaces:**
- Consumes: из Task 1 — имена файлов `experts/<id>.md`, деление чеклиста на «В спеке проверяет» и «В diff проверяет», схему замечания.
- Produces: четыре файла персон, на которые ссылается сборка панели в `SKILL.md`; блоки `**В спеке проверяет:**` и `**В diff проверяет:**` в каждом — их выбирают режимы из Task 3 и Task 4.

- [ ] **Step 1: Создать `skills/expert-panel/experts/pike.md`**

```markdown
# Rob Pike — простота

> "Simplicity is the art of hiding complexity."

**Кто.** Соавтор Go. Считает, что код должен быть очевиден с первого прочтения. Три строки прямого кода лучше одной умной. Не любит преждевременные абстракции и DRY ради DRY.

**Как ревьюит.** Читает сверху вниз, как текст. Спотыкается на всём, что заставляет остановиться и перечитать. Если пришлось перечитать — это дефект кода, а не читателя.

**Характерные вопросы:**
- Что станет проще, если убрать этот слой?
- Зачем интерфейс, если реализация одна?
- Это решает сегодняшнюю проблему или воображаемую?

**В спеке проверяет:**
- Нет ли компонентов, введённых «на будущее», без требования сегодня
- Не описана ли конфигурируемость там, где хватает константы
- Соразмерно ли число сущностей размеру задачи
- Можно ли выкинуть слой и получить то же поведение
- Понятна ли спека без устного пояснения автора
- Не спрятана ли сложность в формулировке вместо того, чтобы быть решённой

**В diff проверяет:**
- Интерфейсы с единственной реализацией
- Обёртки и хелперы, которые не сокращают код, а добавляют прыжок при чтении
- Именование: короткое там, где область видимости мала, полное — где велика
- Идиоматичность Go: `range`, `defer`, обработка ошибок без обёрток ради обёрток
- Дублирование, которое реально стоит устранить, — и то, которое дешевле оставить
- Лишние аллокации в горячем пути
- Функции, которые нельзя понять, не читая вызывающий код
```

- [ ] **Step 2: Создать `skills/expert-panel/experts/cheney.md`**

```markdown
# Dave Cheney — границы

> "The biggest risk is not that the code doesn't work today, but that no one will understand it six months from now."

**Кто.** Автор «Practical Go», евангелист ясных зависимостей и явных контрактов. Не терпит скрытой связности и магии.

**Как ревьюит.** Строит в голове граф зависимостей и ищет циклы, лишние рёбра и связи, направленные не туда. Смотрит на пакет как на публичный API, а не как на папку с файлами.

**Характерные вопросы:**
- Почему этот пакет вообще знает о том?
- Что видно снаружи пакета из того, что должно быть внутри?
- Что произойдёт с этим кодом через год, когда контекст забудется?

**В спеке проверяет:**
- Определены ли границы компонентов и кто кому подчинён
- Направление зависимостей: строго сверху вниз (API → Domain → DB), без обратных рёбер
- Не протекают ли модели слоя БД в контракт API
- Описано ли поведение при ошибке на каждой границе: что возвращаем, что логируем, что ретраим
- Есть ли конкурентность и определены ли владение данными и время жизни
- Названы ли контракты между компонентами, а не только сами компоненты
- Что происходит при частичном отказе зависимости

**В diff проверяет:**
- Направление зависимостей, появление обратных импортов
- Размер публичной поверхности пакета: что экспортировано без необходимости
- Ошибки: обёрнуты ли с контекстом, не потеряны ли, не сравниваются ли строкой вместо `errors.Is` и `errors.As`
- Обработка `nil` и нулевых значений
- Конкурентность: гонки, утечки горутин, `context` без отмены и без таймаута
- Конвертеры между слоями: полнота, потеря полей при преобразовании
- Не появилось ли у пакета знание о слое, который выше него
```

- [ ] **Step 3: Создать `skills/expert-panel/experts/ford.md`**

```markdown
# Neal Ford — trade-offs

> "There are no right answers in architecture — only trade-offs."

**Кто.** Соавтор «Fundamentals of Software Architecture» и «Building Evolutionary Architectures». Убеждён, что архитектура — это набор решений с ценой, а не набор диаграмм.

**Как ревьюит.** Находит решение, которое дороже всего откатить, и проверяет, осознанно ли оно принято. Спрашивает не «правильно ли», а «что мы за это платим».

**Характерные вопросы:**
- Что сломается, если через полгода это решение окажется неверным?
- Какую характеристику мы приносим в жертву и в чью пользу?
- Решение обратимо? Если да, почему оно принимается так рано?

**В спеке проверяет:**
- Названы ли альтернативы и честно ли рассмотрены — соломенное чучело вместо альтернативы это замечание
- Названа ли цена выбранного варианта, а не только выгода
- Обратимость: что понадобится, чтобы откатить решение через квартал
- Blast radius: кто ещё пострадает — сервисы, клиенты API, потребители контракта
- Приоритет характеристик: что важнее — задержка, пропускная способность, простота эксплуатации — и выбран ли вариант под этот приоритет
- Совместимость: ломается ли контракт для существующих клиентов и как мигрируем
- Есть ли способ проверить, что архитектура держится: метрика, тест, проверка в CI
- Не принимается ли решение раньше, чем появились данные для него

**В diff проверяет:**
- Реализация соответствует заявленному решению, а не соседнему
- Не введена ли связность, которой не было в дизайне
- Ломающие изменения контракта: API, схема события, формат конфигурации
- План отката: можно ли выкатить назад, не потеряв данные
- Не протащено ли мимо обсуждения решение, дорогое в откате
- Наблюдаемость решения: по чему поймём, что оно работает как задумано
```

- [ ] **Step 4: Создать `skills/expert-panel/experts/stonebraker.md`**

```markdown
# Michael Stonebraker — данные

> "One size does not fit all."

**Кто.** Создатель Ingres и Postgres, лауреат премии Тьюринга. Считает, что выбор хранилища и модель данных определяют систему сильнее, чем код вокруг них.

**Как ревьюит.** Начинает с данных: что храним, как читаем, как меняем, что происходит при сбое посередине. Код смотрит как следствие модели.

**Характерные вопросы:**
- Какой запрос это должно обслуживать и сколько там будет строк через год?
- Что произойдёт, если процесс упадёт между этими двумя записями?
- Почему это хранится здесь, а не там?

**В спеке проверяет:**
- Обоснован ли выбор хранилища рабочей нагрузкой, а не привычкой команды
- Модель данных: нормализация, ключи, уникальность, что является источником правды
- Объёмы и рост: есть ли оценка числа строк и скорости роста
- Паттерны доступа: какие запросы, с какой частотой, какие индексы им нужны
- Транзакционные границы: что атомарно, что нет, что делать с частичным результатом
- Согласованность: где допустима отложенная, где нет
- Миграция: как переезжают существующие данные и сколько это займёт на боевом объёме
- Удаление и ретенция: что и когда чистим

**В diff проверяет:**
- Запросы: индексируемость, seq scan на больших таблицах, N+1
- Транзакции: границы, длительность удержания, риск дедлока
- Миграции: блокирующий `ALTER`, время выполнения на боевом объёме, обратимость
- Схема и код: не разъехались ли
- Целостность: ограничения выражены в БД или только в коде
- Пагинация через `OFFSET` на больших выборках
- Идемпотентность записи: что произойдёт при повторе операции
```

- [ ] **Step 5: Проверить, что у всех персон есть оба чеклиста**

Run:
```bash
for f in skills/expert-panel/experts/*.md; do
  grep -qF "**В спеке проверяет:**" "$f" || echo "NO SPEC CHECKLIST: $f"
  grep -qF "**В diff проверяет:**" "$f" || echo "NO DIFF CHECKLIST: $f"
  grep -qF "**Как ревьюит.**" "$f" || echo "NO HOW: $f"
done
ls skills/expert-panel/experts/ | sort
```
Expected: ни одной строки `NO ...`; листинг ровно из четырёх файлов — `cheney.md`, `ford.md`, `pike.md`, `stonebraker.md`.

- [ ] **Step 6: Коммит**

```bash
git add skills/expert-panel/experts/
git commit -m "feat(expert-panel): персоны ядра — Pike, Cheney, Ford, Stonebraker"
```

---

### Task 3: Режим ревью спеки

**Files:**
- Create: `skills/expert-panel/modes/spec.md`

**Interfaces:**
- Consumes: из Task 1 — схему замечания, синтез, лимиты, нумерацию `P1`/`C2`/`F3`/`S1`; из Task 2 — блок `**В спеке проверяет:**` в файлах персон.
- Produces: формат секции `## Review log`, которую дописывает в спеку и читает при повторном прогоне.

- [ ] **Step 1: Создать `skills/expert-panel/modes/spec.md`**

````markdown
# Режим: ревью спеки

Критический разбор design-документа перед переходом к планированию. Заканчивается обновлённой спекой, а не отчётом.

## Определение артефакта

1. Путь передан аргументом — используй его.
2. Пути нет — возьми самый свежий файл из `docs/superpowers/specs/`. Если каталога нет или он пуст, спроси путь у пользователя.
3. Кандидатов несколько и выбор неочевиден — покажи список и спроси.

## Фаза 1. Контекст

1. Прочитай спеку целиком.
2. Прочитай `CLAUDE.md` репозитория, если он есть.
3. Найди затронутый код: grep по ключевым терминам спеки — именам пакетов, типов, таблиц, эндпоинтов. Собери список релевантных путей, не больше 20.
4. Если в спеке есть секция `## Review log` — прочитай её. Замечания, отклонённые ранее с причиной, повторно не поднимаются. Принятые ранее — проверяются: отражены ли они в текущем тексте.
5. Покажи пользователю summary:
   - тема спеки одной строкой;
   - задетые пакеты и сервисы;
   - что из упомянутого в спеке не найдено в коде;
   - предыдущие прогоны панели, если есть.

**Не переходи к фазе 2 без подтверждения пользователя.** Панель, запущенная по спеке в вакууме, выдаёт замечания про несуществующий код.

## Фаза 2. Панель

Собери активную панель и запусти агентов по протоколу из `SKILL.md`. Режим — `спека`: агент использует блок «В спеке проверяет» своей персоны.

Каждому агенту передай: путь к спеке, список релевантных путей из фазы 1, содержимое Review log, если он есть.

## Фаза 3. Отчёт

Синтезируй по протоколу из `SKILL.md` и покажи отчёт:

1. **Панель** — кто участвовал.
2. **Удачные решения** — сводно, без разбивки по экспертам.
3. **Замечания** — по убыванию severity, каждое с `id`, местом, сутью, последствием и предложенной правкой.
4. **Конфликты** — пары взаимоисключающих замечаний с позицией каждого эксперта.
5. **Ниже порога** — свёрнутые строки, если лимиты превышены.

## Фаза 4. Разбор

Попроси пользователя ответить одной строкой в формате:

    accept C2,S1; reject F3 — причина; ? P4

- `accept` — правка будет применена.
- `reject` — причина обязательна, она попадёт в Review log.
- `?` — обсуждаем по одному, каждое до решения `accept` или `reject`.

Конфликты требуют явного выбора стороны — принять оба замечания из пары нельзя.

Поштучный опрос по каждому замечанию не устраивай: при пятнадцати замечаниях это пятнадцать раундов, дороже самого ревью.

## Фаза 5. Правки

1. Применяй только принятые замечания, точечными правками. Спеку целиком не переписывай — пользователь согласовывал текст, а не его пересказ.
2. Если правка требует решения, которого нет ни в замечании, ни в спеке, — спроси, не придумывай.
3. Покажи diff изменений.

## Фаза 6. Журнал

Допиши в конец спеки секцию `## Review log` (или новый подраздел в существующую):

    ## Review log

    ### 2026-07-24 — expert-panel (Pike, Cheney, Ford, Stonebraker)
    Принято: C2 — добавлено поведение при недоступности каталога; S1 — схема
    переведена на составной ключ.
    Отклонено: F3 — вынос в отдельный сервис. Причина: преждевременно,
    объём не оправдан.

Дату бери из системного окружения, состав панели — фактический.

Отклонённые с причиной важнее принятых: следующий прогон читает журнал и не поднимает закрытые вопросы заново.

## Завершение

Коммит не делай. Скажи пользователю, что спека обновлена и готова к переходу к планированию. `writing-plans` сам не вызывай.
````

- [ ] **Step 2: Проверить структуру режима**

Run:
```bash
for s in "## Определение артефакта" "## Фаза 1. Контекст" "## Фаза 2. Панель" "## Фаза 3. Отчёт" "## Фаза 4. Разбор" "## Фаза 5. Правки" "## Фаза 6. Журнал" "## Завершение"; do
  grep -qF "$s" skills/expert-panel/modes/spec.md || echo "MISSING: $s"
done
grep -qF "Review log" skills/expert-panel/modes/spec.md || echo "MISSING: Review log"
grep -c "kirpr" skills/expert-panel/modes/spec.md
```
Expected: ни одной строки `MISSING`; последняя команда печатает `0`.

- [ ] **Step 3: Коммит**

```bash
git add skills/expert-panel/modes/spec.md
git commit -m "feat(expert-panel): режим ревью спеки"
```

---

### Task 4: Режим ревью diff

**Files:**
- Create: `skills/expert-panel/modes/diff.md`

**Interfaces:**
- Consumes: из Task 1 — схему замечания, синтез, лимиты; из Task 2 — блок `**В diff проверяет:**`; из Task 3 — формат `## Review log` для сверки со спекой по флагу `--spec`.
- Produces: имя опционального файла проекта `.claude/expert-panel-ignore`, вердикты `Approve` / `Approve with comments` / `Request changes`.

- [ ] **Step 1: Создать `skills/expert-panel/modes/diff.md`**

````markdown
# Режим: ревью diff

Разбор изменений перед коммитом или merge request.

## Preflight

1. Убедись, что текущий каталог внутри git-репозитория: `git rev-parse --git-dir`. Не репозиторий — сообщи и прерви.
2. Определи базу:
   - база передана аргументом — разреши её по шагу 3;
   - аргумента нет — сравнивай рабочее дерево с `HEAD`, шаг 3 пропусти.
3. Разреши базу в ref и проверь актуальность. Ни одна из команд не предполагается успешной — проверяй каждую:

       git rev-parse --verify <база>
       git remote get-url origin

   - Локального ref нет, но есть `origin/<база>` — ревьюй против `origin/<база>` и скажи об этом пользователю.
   - Нет ни локального ref, ни `origin/<база>` — сообщи, что база не найдена, и прерви.
   - `origin` отсутствует — проверку свежести пропусти, предупреди, что база не сверена с удалённой, и продолжай. Репозиторий без remote — нормальный случай, а не ошибка.
   - `origin` и локальный ref есть — выполни:

         git fetch origin <база> --quiet
         git rev-list --count <база>..origin/<база>

     Результат больше нуля — локальная база отстала. Спроси пользователя: обновить базу или ревьюить против устаревшей. Молча ревьюить неверный diff хуже, чем не ревьюить вовсе.
4. Получи diff и сохрани во временный файл — агентам передаётся путь, а не содержимое в промпте:
   - без базы: `git diff HEAD` — рабочее дерево целиком, включая незакоммиченное;
   - с базой: `git diff <разрешённая база>...HEAD` — три точки, сравнение от точки расхождения. Незакоммиченные изменения сюда не попадают; если рабочее дерево грязное, скажи об этом пользователю.

## Фильтрация файлов

Исключай из ревью три категории:

1. **Сгенерированный Go-код** — файлы, у которых первая строка соответствует `^// Code generated .* DO NOT EDIT\.$`. Это стандарт Go, проверяется механически.
2. **Дефолтный список путей:** `vendor/`, `*.pb.go`, `*_mock.go`, `testdata/`.
3. **Проектный список** — если в репозитории есть `.claude/expert-panel-ignore`, каждая непустая строка без `#` в начале трактуется как glob-шаблон пути. Набор генераторов у каждой команды свой, это свойство проекта, а не скила.

Покажи пользователю, сколько файлов исключено и по какой причине. Молчаливое исключение читается как «панель это посмотрела».

Если после фильтрации не осталось изменений — сообщи и прерви.

## Фаза 1. Контекст

1. Список изменённых файлов со статистикой.
2. Для каждого файла из diff читай контекст целиком, а не только изменённые строки. Ревьюится только diff, но судить о нём без окружения нельзя.
3. Если передан `--spec <путь>` — прочитай спеку и её `## Review log`.
4. Покажи summary: база, число файлов, исключённые файлы, наличие спеки.

## Фаза 2. Панель

Собери активную панель и запусти агентов по протоколу из `SKILL.md`. Режим — `diff`: агент использует блок «В diff проверяет» своей персоны.

Каждому агенту передай: путь к файлу с diff, список изменённых файлов, путь к спеке и её Review log, если передан `--spec`.

При `--spec` каждый агент дополнительно проверяет:
- что из спеки не реализовано;
- что сделано сверх спеки;
- какие решения, зафиксированные в Review log, нарушены.

## Фаза 3. Отчёт

Синтезируй по протоколу из `SKILL.md`. Каждое замечание обязано иметь `file:line`.

1. **Панель** — кто участвовал, база, число файлов.
2. **Удачные решения** — обязательно, если есть за что. Отчёт из одних претензий перестают читать.
3. **Замечания** — по убыванию severity.
4. **Конфликты**.
5. **Ниже порога**.
6. **Вердикт** — `Approve`, `Approve with comments` или `Request changes`. При `Request changes` перечисли блокеры списком.

## Фаза 4. Разбор

Тот же формат, что в режиме спеки:

    accept C2,S1; reject F3 — причина; ? P4

## Фаза 5. Правки

1. Применяй только принятые замечания.
2. Тесты, линтеры и сборку не запускай — выведи команды, которые пользователь запустит сам. Панель судит о коде, а не отвечает за то, что он собирается.
3. Покажи diff внесённых правок.
4. Коммит не делай.
````

- [ ] **Step 2: Проверить структуру режима**

Run:
```bash
for s in "## Preflight" "## Фильтрация файлов" "## Фаза 1. Контекст" "## Фаза 2. Панель" "## Фаза 3. Отчёт" "## Фаза 4. Разбор" "## Фаза 5. Правки"; do
  grep -qF "$s" skills/expert-panel/modes/diff.md || echo "MISSING: $s"
done
for s in "expert-panel-ignore" "DO NOT EDIT" "Request changes" "Approve with comments"; do
  grep -qF "$s" skills/expert-panel/modes/diff.md || echo "MISSING: $s"
done
grep -c "kirpr" skills/expert-panel/modes/diff.md
```
Expected: ни одной строки `MISSING`; последняя команда печатает `0`.

- [ ] **Step 3: Коммит**

```bash
git add skills/expert-panel/modes/diff.md
git commit -m "feat(expert-panel): режим ревью git diff"
```

---

### Task 5: Установка скила из локального клона

**Files:**
- Modify: `install.sh:4-7` (блок переменных), `install.sh:11-17` (блок бэкапа), `install.sh:19-32` (очистка и создание каталогов), `install.sh:60-65` (после копирования скриптов), `install.sh:165-166` (финальное сообщение)

**Interfaces:**
- Consumes: из Task 1–4 — раскладку `skills/expert-panel/{SKILL.md,custom-experts.md,experts/*.md,modes/*.md}`.
- Produces: путь установки `$HOME/.claude/skills/expert-panel/`; поведение «overlay переживает переустановку», на которое опирается Task 6 и Task 7.

- [ ] **Step 1: Добавить переменные каталогов**

В `install.sh` после строки `KIRPR_DIR="$CLAUDE_DIR/kirpr"` добавить:

```bash
SKILLS_DIR="$CLAUDE_DIR/skills"
PANEL_DIR="$SKILLS_DIR/expert-panel"
```

- [ ] **Step 2: Добавить бэкап overlay рядом с бэкапом tracker.md**

В `install.sh` после блока, заканчивающегося строкой `echo "  Backed up tracker.md"` и её закрывающим `fi`, добавить:

```bash
# --- Backup custom-experts.md if it exists ---
CUSTOM_BACKUP=""
if [ -f "$PANEL_DIR/custom-experts.md" ]; then
    CUSTOM_BACKUP="$(mktemp)"
    cp "$PANEL_DIR/custom-experts.md" "$CUSTOM_BACKUP"
    echo "  Backed up custom-experts.md"
fi
```

- [ ] **Step 3: Добавить очистку и создание каталогов скила**

В `install.sh` в блок `# --- Clean old installation ---` после удаления `$KIRPR_DIR` добавить:

```bash
if [ -d "$PANEL_DIR" ]; then
    rm -rf "$PANEL_DIR"
    echo "  Removed old $PANEL_DIR"
fi
```

В блок `# --- Create directories ---` после `mkdir -p "$KIRPR_DIR/scripts"` добавить:

```bash
mkdir -p "$PANEL_DIR/experts"
mkdir -p "$PANEL_DIR/modes"
```

- [ ] **Step 4: Добавить копирование файлов скила**

В `install.sh` после блока `# --- Copy scripts ---` (перед `# --- Restore or configure tracker ---`) добавить:

```bash
# --- Copy expert-panel skill ---
cp "$REPO_DIR/skills/expert-panel/SKILL.md" "$PANEL_DIR/SKILL.md"
echo "  skills/expert-panel/SKILL.md -> copied"
for f in "$REPO_DIR"/skills/expert-panel/experts/*.md; do
    name="$(basename "$f")"
    cp "$f" "$PANEL_DIR/experts/$name"
    echo "  skills/expert-panel/experts/$name -> copied"
done
for f in "$REPO_DIR"/skills/expert-panel/modes/*.md; do
    name="$(basename "$f")"
    cp "$f" "$PANEL_DIR/modes/$name"
    echo "  skills/expert-panel/modes/$name -> copied"
done

# --- Restore or seed custom-experts.md ---
if [ -n "$CUSTOM_BACKUP" ] && [ -f "$CUSTOM_BACKUP" ]; then
    cp "$CUSTOM_BACKUP" "$PANEL_DIR/custom-experts.md"
    rm "$CUSTOM_BACKUP"
    echo "  Restored custom-experts.md"
else
    cp "$REPO_DIR/skills/expert-panel/custom-experts.md" "$PANEL_DIR/custom-experts.md"
    echo "  skills/expert-panel/custom-experts.md -> copied"
fi
```

- [ ] **Step 5: Обновить финальное сообщение**

Заменить последнюю строку `echo "Done! kirpr commands are now available in Claude Code as /kirpr:*"` на:

```bash
echo "Done! kirpr commands are available as /kirpr:*, expert-panel skill as /expert-panel"
```

- [ ] **Step 6: Проверить синтаксис**

Run: `bash -n install.sh`
Expected: пустой вывод, код возврата 0.

- [ ] **Step 7: Проверить установку в изолированный HOME**

Run:
```bash
TMPHOME="$(mktemp -d)"
printf '3\n' | HOME="$TMPHOME" ./install.sh > /dev/null
find "$TMPHOME/.claude/skills" -type f | sort
```
Expected: ровно восемь файлов —
```
<TMPHOME>/.claude/skills/expert-panel/SKILL.md
<TMPHOME>/.claude/skills/expert-panel/custom-experts.md
<TMPHOME>/.claude/skills/expert-panel/experts/cheney.md
<TMPHOME>/.claude/skills/expert-panel/experts/ford.md
<TMPHOME>/.claude/skills/expert-panel/experts/pike.md
<TMPHOME>/.claude/skills/expert-panel/experts/stonebraker.md
<TMPHOME>/.claude/skills/expert-panel/modes/diff.md
<TMPHOME>/.claude/skills/expert-panel/modes/spec.md
```

- [ ] **Step 8: Проверить, что overlay переживает переустановку**

Run:
```bash
echo "## Мой Эксперт — тест" >> "$TMPHOME/.claude/skills/expert-panel/custom-experts.md"
printf '3\n' | HOME="$TMPHOME" ./install.sh > /dev/null
grep -c "Мой Эксперт" "$TMPHOME/.claude/skills/expert-panel/custom-experts.md"
rm -rf "$TMPHOME"
```
Expected: `1` — пользовательская правка сохранилась после переустановки.

- [ ] **Step 9: Коммит**

```bash
git add install.sh
git commit -m "feat(install): установка скила expert-panel с сохранением overlay"
```

---

### Task 6: Удаление скила

**Files:**
- Modify: `uninstall.sh:4-6` (переменные), `uninstall.sh:10-21` (после блока tracker.md), `uninstall.sh:23-34` (удаление каталогов), `uninstall.sh:36-43` (финальные сообщения)

**Interfaces:**
- Consumes: из Task 5 — путь `$HOME/.claude/skills/expert-panel/` и имя файла `custom-experts.md`.
- Produces: ничего для последующих задач.

- [ ] **Step 1: Добавить переменные**

В `uninstall.sh` после строки `KIRPR_DIR="$CLAUDE_DIR/kirpr"` добавить:

```bash
SKILLS_DIR="$CLAUDE_DIR/skills"
PANEL_DIR="$SKILLS_DIR/expert-panel"
```

- [ ] **Step 2: Добавить сохранение overlay**

В `uninstall.sh` после блока `# --- Handle tracker.md ---` добавить:

```bash
# --- Handle custom-experts.md ---
if [ -f "$PANEL_DIR/custom-experts.md" ]; then
    echo ""
    echo "custom-experts.md contains your custom expert panel."
    printf "Delete it too? [y/N]: "
    read -r delete_custom
    if [ "$delete_custom" != "y" ] && [ "$delete_custom" != "Y" ]; then
        CUSTOM_SAVE="$(mktemp)"
        cp "$PANEL_DIR/custom-experts.md" "$CUSTOM_SAVE"
        echo "  Saved custom-experts.md to $CUSTOM_SAVE"
    fi
fi
```

- [ ] **Step 3: Добавить удаление каталога скила**

В `uninstall.sh` в блок `# --- Remove directories ---` после удаления `$KIRPR_DIR` добавить:

```bash
if [ -d "$PANEL_DIR" ]; then
    rm -rf "$PANEL_DIR"
    echo "  Removed $PANEL_DIR"
fi
```

В блок `# --- Clean up empty parent directories ---` после существующей строки про `commands` добавить:

```bash
rmdir "$SKILLS_DIR" 2>/dev/null && echo "  Removed empty: $SKILLS_DIR" || true
```

- [ ] **Step 4: Добавить финальное сообщение о сохранённом overlay**

В конец `uninstall.sh` после блока про `TRACKER_SAVE` добавить:

```bash
if [ -n "${CUSTOM_SAVE:-}" ] && [ -f "${CUSTOM_SAVE:-}" ]; then
    echo ""
    echo "Your custom-experts.md was saved to: $CUSTOM_SAVE"
    echo "To restore it after reinstalling: cp $CUSTOM_SAVE ~/.claude/skills/expert-panel/custom-experts.md"
fi
```

- [ ] **Step 5: Проверить синтаксис**

Run: `bash -n uninstall.sh`
Expected: пустой вывод, код возврата 0.

- [ ] **Step 6: Проверить полный цикл установка → удаление**

Run:
```bash
TMPHOME="$(mktemp -d)"
printf '3\n' | HOME="$TMPHOME" ./install.sh > /dev/null
printf 'n\nn\n' | HOME="$TMPHOME" ./uninstall.sh
ls -d "$TMPHOME/.claude/skills" 2>&1 | tail -1
rm -rf "$TMPHOME"
```
Expected: в выводе `uninstall.sh` есть строки `Saved custom-experts.md to ...` и `Removed .../.claude/skills/expert-panel`; последняя команда печатает ошибку «No such file or directory» — пустой каталог `skills` тоже удалён.

- [ ] **Step 7: Коммит**

```bash
git add uninstall.sh
git commit -m "feat(uninstall): удаление скила expert-panel с сохранением overlay"
```

---

### Task 7: Установка из GitHub и фикс недостающих файлов

**Files:**
- Modify: `install-remote.sh:8-10` (переменные), `install-remote.sh:14-20` (бэкап), `install-remote.sh:22-35` (очистка и каталоги), `install-remote.sh:48-68` (списки загрузки)

**Interfaces:**
- Consumes: из Task 5 — раскладку установки и правило сохранения overlay.
- Produces: полный список файлов для скачивания, который проверяется автоматически против `git ls-files`.

- [ ] **Step 1: Добавить переменные и бэкап overlay**

В `install-remote.sh` после строки `KIRPR_DIR="$CLAUDE_DIR/kirpr"` добавить:

```bash
SKILLS_DIR="$CLAUDE_DIR/skills"
PANEL_DIR="$SKILLS_DIR/expert-panel"
```

После блока бэкапа `tracker.md` добавить:

```bash
# --- Backup custom-experts.md if it exists ---
CUSTOM_BACKUP=""
if [ -f "$PANEL_DIR/custom-experts.md" ]; then
    CUSTOM_BACKUP="$(mktemp)"
    cp "$PANEL_DIR/custom-experts.md" "$CUSTOM_BACKUP"
    echo "  Backed up custom-experts.md"
fi
```

- [ ] **Step 2: Добавить очистку и каталоги**

В блок `# --- Clean old installation ---` после удаления `$KIRPR_DIR` добавить:

```bash
if [ -d "$PANEL_DIR" ]; then
    rm -rf "$PANEL_DIR"
    echo "  Removed old $PANEL_DIR"
fi
```

В блок `# --- Create directories ---` после `mkdir -p "$KIRPR_DIR/scripts"` добавить:

```bash
mkdir -p "$KIRPR_DIR/prompts"
mkdir -p "$PANEL_DIR/experts"
mkdir -p "$PANEL_DIR/modes"
```

Каталог `prompts` создаётся здесь же: без него скачивание `kirpr/prompts/text.md` в шаге 3 упадёт.

- [ ] **Step 3: Дополнить списки загрузки**

В блоке `# Commands` после строки с `tasks-review.md` добавить:

```bash
download "commands/kirpr/tasks-push.md"        "$COMMANDS_DIR/tasks-push.md"
download "commands/kirpr/text.md"              "$COMMANDS_DIR/text.md"
```

После блока `# Config` добавить:

```bash
# Prompts
download "kirpr/prompts/text.md"               "$KIRPR_DIR/prompts/text.md"
```

В блоке `# Scripts` после строки с `validate_services.py` добавить:

```bash
download "kirpr/scripts/create_youtrack.py"    "$KIRPR_DIR/scripts/create_youtrack.py"
```

После блока `# Scripts` добавить:

```bash
# Skill: expert-panel
download "skills/expert-panel/SKILL.md"                  "$PANEL_DIR/SKILL.md"
download "skills/expert-panel/experts/pike.md"           "$PANEL_DIR/experts/pike.md"
download "skills/expert-panel/experts/cheney.md"         "$PANEL_DIR/experts/cheney.md"
download "skills/expert-panel/experts/ford.md"           "$PANEL_DIR/experts/ford.md"
download "skills/expert-panel/experts/stonebraker.md"    "$PANEL_DIR/experts/stonebraker.md"
download "skills/expert-panel/modes/spec.md"             "$PANEL_DIR/modes/spec.md"
download "skills/expert-panel/modes/diff.md"             "$PANEL_DIR/modes/diff.md"

# --- Restore or seed custom-experts.md ---
if [ -n "$CUSTOM_BACKUP" ] && [ -f "$CUSTOM_BACKUP" ]; then
    cp "$CUSTOM_BACKUP" "$PANEL_DIR/custom-experts.md"
    rm "$CUSTOM_BACKUP"
    echo "  Restored custom-experts.md"
else
    download "skills/expert-panel/custom-experts.md"      "$PANEL_DIR/custom-experts.md"
fi
```

- [ ] **Step 4: Обновить финальное сообщение**

Заменить последнюю строку `echo "Done! kirpr commands are now available in Claude Code as /kirpr:*"` на:

```bash
echo "Done! kirpr commands are available as /kirpr:*, expert-panel skill as /expert-panel"
```

- [ ] **Step 5: Проверить синтаксис**

Run: `bash -n install-remote.sh`
Expected: пустой вывод, код возврата 0.

- [ ] **Step 6: Проверить полноту списка загрузки против репозитория**

Run:
```bash
missing=0
for f in $(git ls-files 'commands/kirpr/*.md' 'kirpr/config/*.md' 'kirpr/prompts/*.md' 'kirpr/scripts/*.py' 'skills/expert-panel/*.md' 'skills/expert-panel/experts/*.md' 'skills/expert-panel/modes/*.md'); do
  [ "$f" = "kirpr/config/tracker.md.template" ] && continue
  grep -qF "\"$f\"" install-remote.sh || { echo "NOT DOWNLOADED: $f"; missing=1; }
done
echo "missing=$missing"
```
Expected: ни одной строки `NOT DOWNLOADED`, вывод `missing=0`. Эта проверка и есть фикс: до правки она обязана была печатать `tasks-push.md`, `text.md`, `prompts/text.md`, `create_youtrack.py`.

- [ ] **Step 7: Коммит**

```bash
git add install-remote.sh
git commit -m "fix(install-remote): скил expert-panel и четыре потерянных файла"
```

Тело коммита должно перечислить восстановленные файлы: `commands/kirpr/tasks-push.md`, `commands/kirpr/text.md`, `kirpr/prompts/text.md`, `kirpr/scripts/create_youtrack.py`.

---

### Task 8: Документация

**Files:**
- Modify: `README.md:3` (вводная строка), `README.md:25-30` (после раздела про текст — новый раздел), `README.md:93-104` (структура проекта)

**Interfaces:**
- Consumes: из Task 1–7 — имя скила, режимы, путь установки, имя overlay.
- Produces: ничего для последующих задач.

- [ ] **Step 1: Обновить вводную строку**

Заменить строку 3 `README.md`:

```markdown
Декомпозиция задач из трекера, Architecture Decision Records, редактура текстов и ревью панелью экспертов — 9 команд и один скил для Claude Code.
```

- [ ] **Step 2: Добавить раздел про скил**

После раздела `### Редактура текста` и его таблицы, перед разделом `## Установка`, вставить:

```markdown
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
```

- [ ] **Step 3: Обновить структуру проекта**

Заменить блок структуры проекта в `README.md` на:

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

- [ ] **Step 4: Проверить README**

Run:
```bash
for s in "/expert-panel spec" "/expert-panel diff" "custom-experts.md" "expert-panel-ignore" "skills/expert-panel/" "Michael Stonebraker"; do
  grep -qF "$s" README.md || echo "MISSING: $s"
done
grep -n "8 команд" README.md
```
Expected: ни одной строки `MISSING`; вторая команда ничего не печатает — старое число команд из вводной убрано.

- [ ] **Step 5: Коммит**

```bash
git add README.md
git commit -m "docs: раздел про скил expert-panel"
```

---

## Итоговая проверка

- [ ] **Прогнать существующие тесты — убедиться, что ничего не задето**

Run: `python3 -m unittest discover -s tests -v`
Expected: `OK`, ни одного `FAILED`.

- [ ] **Прогнать полный цикл установки в изолированный HOME**

Run:
```bash
TMPHOME="$(mktemp -d)"
printf '3\n' | HOME="$TMPHOME" ./install.sh
find "$TMPHOME/.claude" -type f | sort
rm -rf "$TMPHOME"
```
Expected: девять команд в `commands/kirpr/`, восемь файлов скила в `skills/expert-panel/`, скрипты и конфиги на месте.
