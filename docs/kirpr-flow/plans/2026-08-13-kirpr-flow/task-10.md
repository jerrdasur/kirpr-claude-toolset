# Задача 10: установка и удаление

Единственная задача плана, которая трогает исполняемый код. Верификация —
формат «скрипт»: запуск.

**Файлы:**
- Изменить: `install.sh`
- Изменить: `uninstall.sh`

**Интерфейсы:**
- Потребляет: структуру каталога набора из задач 1-9 — `SKILL.md`, `core/`,
  `modes/`, `prompts/`.
- Предоставляет: установленный набор в `~/.claude/skills/kirpr-flow/`, на
  который ссылается путь из блока выжимки правил
  (`~/.claude/skills/kirpr-flow/core/rules.md`).

---

- [ ] **Шаг 1: Прочитать существующие скрипты**

```
Read install.sh
Read uninstall.sh
```

Разобраться, как ставятся `expert-panel` и `grill-me`: переменная с путём
назначения, удаление старой установки, `mkdir -p` на подкаталоги, цикл
копирования по каждому подкаталогу. Новый набор ставится тем же способом —
свой способ здесь был бы расхождением без причины.

- [ ] **Шаг 2: Дополнить `install.sh`**

Рядом с `PANEL_DIR` и `GRILL_DIR` добавить:

```bash
FLOW_DIR="$SKILLS_DIR/kirpr-flow"
```

В блок удаления старой установки — по образцу существующих:

```bash
if [ -d "$FLOW_DIR" ]; then
    rm -rf "$FLOW_DIR"
    echo "  Removed old $FLOW_DIR"
fi
```

В блок создания каталогов:

```bash
mkdir -p "$FLOW_DIR/core"
mkdir -p "$FLOW_DIR/modes"
mkdir -p "$FLOW_DIR/prompts"
```

Копирование — `SKILL.md` отдельно, три подкаталога циклами:

```bash
cp "$REPO_DIR/skills/kirpr-flow/SKILL.md" "$FLOW_DIR/SKILL.md"
echo "  skills/kirpr-flow/SKILL.md -> copied"
for d in core modes prompts; do
    for f in "$REPO_DIR"/skills/kirpr-flow/$d/*.md; do
        name="$(basename "$f")"
        cp "$f" "$FLOW_DIR/$d/$name"
        echo "  skills/kirpr-flow/$d/$name -> copied"
    done
done
```

Пользовательских файлов, которые надо сохранять между установками (как
`custom-experts.md` у панели), у набора нет — блок резервного копирования не
нужен.

В финальную строку вывода добавить `/kirpr-flow` к перечню доступных скилов.

- [ ] **Шаг 3: Дополнить `uninstall.sh`**

Добавить удаление `~/.claude/skills/kirpr-flow` по образцу того, как там
удаляются `expert-panel` и `grill-me`.

- [ ] **Шаг 4: Верификация — формат «скрипт»**

Запустить установку и проверить результат:

```bash
bash install.sh </dev/null
ls -R ~/.claude/skills/kirpr-flow
```

Ожидается: каталог существует, в нём `SKILL.md` и три подкаталога, в
`core/` пять файлов, в `modes/` восемь, в `prompts/` шесть.

Пересчитать машинно:

```bash
find ~/.claude/skills/kirpr-flow -name '*.md' | wc -l
```

Ожидается: `20`.

Затем проверить удаление:

```bash
bash uninstall.sh </dev/null
test ! -d ~/.claude/skills/kirpr-flow && echo "removed" || echo "STILL THERE"
```

Ожидается: `removed`.

Затем поставить обратно, чтобы набор остался установленным:

```bash
bash install.sh </dev/null
find ~/.claude/skills/kirpr-flow -name '*.md' | wc -l
```

Ожидается: `20`.

Перенаправление `</dev/null` нужно, потому что `install.sh` может спросить
про трекер задач; пустой ввод оставляет существующую настройку нетронутой.
Если скрипт при этом падает или перезаписывает `tracker.md` — это дефект,
его надо починить в этой же задаче: установка нового скила не имеет права
трогать чужую конфигурацию.

В отчёт: все команды и их вывод целиком, включая оба значения счётчика
файлов.
