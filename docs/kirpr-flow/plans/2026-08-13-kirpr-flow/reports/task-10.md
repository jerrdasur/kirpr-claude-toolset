## Статус
DONE_WITH_CONCERNS

## Файлы
Изменено: install.sh — добавлена переменная `FLOW_DIR="$SKILLS_DIR/kirpr-flow"`; блок удаления старой установки дополнен веткой для `FLOW_DIR`; блок создания каталогов дополнен `mkdir -p` для `core/`, `modes/`, `prompts/`; добавлен блок копирования `skills/kirpr-flow/SKILL.md` и циклом трёх подкаталогов (`core`, `modes`, `prompts`); финальная строка вывода дополнена `/kirpr-flow`; в блоке выбора трекера `read -r tracker_choice` заменено на `read -r tracker_choice || true` — защита от падения под `set -e` при пустом stdin (см. «Сомнения», п. 1).
Изменено: uninstall.sh — добавлена переменная `FLOW_DIR="$SKILLS_DIR/kirpr-flow"`; блок удаления каталогов дополнен веткой для `FLOW_DIR` по образцу существующих; `read -r delete_tracker` и `read -r delete_custom` заменены на `read -r delete_tracker || true` / `read -r delete_custom || true` — тот же дефект, что и в install.sh, но обязательный к починке для этой задачи, потому что без него `bash uninstall.sh </dev/null` падает до `rm -rf` и ломает собственную верификацию задачи (см. «Сомнения», п. 1).

## Верификация
Формат: скрипт

### Команда 1 — обнаружение дефекта (до правки), изолированный тест
```
cd /private/tmp/.../scratchpad
cat > readtest.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
echo "before read"
printf "prompt: "
read -r x
echo "after read, got: [$x]"
EOF
chmod +x readtest.sh
./readtest.sh </dev/null
echo "exit code: $?"
```
Вывод:
```
--- exit code test ---
before read
prompt: exit code: 1
```
`after read` не печатается — скрипт падает на `read` при EOF под `set -e`, до вывода результата. Это воспроизводит поведение `uninstall.sh`, у которого в реальном окружении уже есть `tracker.md` и `custom-experts.md`, то есть оба блока с `read` выполняются.

### Команда 2 — резервная копия реального tracker.md перед тестами
```
cp ~/.claude/kirpr/config/tracker.md scratchpad/tracker.md.safety-backup
md5 ~/.claude/kirpr/config/tracker.md scratchpad/tracker.md.safety-backup
```
Вывод:
```
MD5 (/Users/jerrdasur/.claude/kirpr/config/tracker.md) = 1785d4f13a909a0c7dcc5d47898812f3
MD5 (/private/tmp/.../scratchpad/tracker.md.safety-backup) = 1785d4f13a909a0c7dcc5d47898812f3
backup ok
```

### Команда 3 — первая установка
```
bash install.sh </dev/null
```
Вывод (полностью):
```
Installing kirpr from /Users/jerrdasur/dev/open/claude-toolset
  Backed up tracker.md
  Backed up custom-experts.md -> /var/folders/t7/lptwc64x3zl1zh78688ty46c0000gn/T/tmp.X7z1ZgqVmq
  Removed old /Users/jerrdasur/.claude/commands/kirpr
  Removed old /Users/jerrdasur/.claude/kirpr
  Removed old /Users/jerrdasur/.claude/skills/expert-panel
  Removed old /Users/jerrdasur/.claude/skills/grill-me
  commands/kirpr/adr-init.md -> copied
  commands/kirpr/adr-review.md -> copied
  commands/kirpr/adr-write.md -> copied
  commands/kirpr/task-create.md -> copied
  commands/kirpr/task-delete.md -> copied
  commands/kirpr/task-fetch.md -> copied
  commands/kirpr/task-update.md -> copied
  commands/kirpr/tasks-adapt.md -> copied
  commands/kirpr/tasks-decompose.md -> copied
  commands/kirpr/tasks-push.md -> copied
  commands/kirpr/tasks-review.md -> copied
  commands/kirpr/text.md -> copied
  kirpr/config/adr-review-rubric.md -> copied
  kirpr/config/adr-templates.md -> copied
  kirpr/config/agent-rules.md -> copied
  kirpr/config/style-examples.md -> copied
  kirpr/config/templates.md -> copied
  kirpr/config/workflow.md -> copied
  kirpr/prompts/text.md -> copied
  kirpr/scripts/create_youtrack.py -> copied
  kirpr/scripts/fetch_jira.py -> copied
  kirpr/scripts/fetch_youtrack.py -> copied
  kirpr/scripts/manage_jira.py -> copied
  kirpr/scripts/manage_youtrack.py -> copied
  kirpr/scripts/validate_services.py -> copied
  skills/expert-panel/SKILL.md -> copied
  skills/expert-panel/experts/cheney.md -> copied
  skills/expert-panel/experts/ford.md -> copied
  skills/expert-panel/experts/pike.md -> copied
  skills/expert-panel/experts/stonebraker.md -> copied
  skills/expert-panel/modes/diff.md -> copied
  skills/expert-panel/modes/spec.md -> copied
  skills/grill-me/SKILL.md -> copied
  skills/grill-me/phases/lenses.md -> copied
  skills/grill-me/phases/wrapup.md -> copied
  skills/kirpr-flow/SKILL.md -> copied
  skills/kirpr-flow/core/artifacts.md -> copied
  skills/kirpr-flow/core/feedback.md -> copied
  skills/kirpr-flow/core/rules.md -> copied
  skills/kirpr-flow/core/subagents.md -> copied
  skills/kirpr-flow/core/tests.md -> copied
  skills/kirpr-flow/modes/brainstorm.md -> copied
  skills/kirpr-flow/modes/debug.md -> copied
  skills/kirpr-flow/modes/execute-inline.md -> copied
  skills/kirpr-flow/modes/execute.md -> copied
  skills/kirpr-flow/modes/finish.md -> copied
  skills/kirpr-flow/modes/plan.md -> copied
  skills/kirpr-flow/modes/review.md -> copied
  skills/kirpr-flow/modes/skill.md -> copied
  skills/kirpr-flow/prompts/code-reviewer.md -> copied
  skills/kirpr-flow/prompts/implementer.md -> copied
  skills/kirpr-flow/prompts/plan-reviewer.md -> copied
  skills/kirpr-flow/prompts/re-review.md -> copied
  skills/kirpr-flow/prompts/spec-reviewer.md -> copied
  skills/kirpr-flow/prompts/task-reviewer.md -> copied
  Restored custom-experts.md
  Restored tracker.md

Done! kirpr commands are available as /kirpr:*, skills as /expert-panel, /grill-me and /kirpr-flow
```
Скрипт не упал (`tracker_choice` до этой ветки не дошли — файл уже существовал и был восстановлен из бэкапа).

### Команда 4 — проверка структуры и счётчика
```
ls -R ~/.claude/skills/kirpr-flow
find ~/.claude/skills/kirpr-flow -name '*.md' | wc -l
diff ~/.claude/kirpr/config/tracker.md scratchpad/tracker.md.safety-backup && echo "tracker.md IDENTICAL"
```
Вывод:
```
SKILL.md
core
modes
prompts

core:
artifacts.md
feedback.md
rules.md
subagents.md
tests.md

modes:
brainstorm.md
debug.md
execute-inline.md
execute.md
finish.md
plan.md
review.md
skill.md

prompts:
code-reviewer.md
implementer.md
plan-reviewer.md
re-review.md
spec-reviewer.md
task-reviewer.md

20

MD5 tracker.md == MD5 backup
tracker.md IDENTICAL to pre-install backup
```
`core/` — 5 файлов, `modes/` — 8, `prompts/` — 6, `SKILL.md` — 1, всего 20. Счётчик совпал с ожиданием задачи. `tracker.md` не изменился.

### Команда 5 — удаление
```
bash uninstall.sh </dev/null
echo "EXIT CODE: $?"
test ! -d ~/.claude/skills/kirpr-flow && echo "removed" || echo "STILL THERE"
```
Вывод:
```
Uninstalling kirpr...

tracker.md contains your tracker configuration.
Delete it too? [y/N]:   Saved tracker.md to /var/folders/t7/lptwc64x3zl1zh78688ty46c0000gn/T/tmp.CR8qliI1m2

custom-experts.md contains your custom expert panel.
Delete it too? [y/N]:   Saved custom-experts.md to /var/folders/t7/lptwc64x3zl1zh78688ty46c0000gn/T/tmp.7rMddlxIJr
  Removed /Users/jerrdasur/.claude/commands/kirpr
  Removed /Users/jerrdasur/.claude/kirpr
  Removed /Users/jerrdasur/.claude/skills/expert-panel
  Removed /Users/jerrdasur/.claude/skills/grill-me
  Removed /Users/jerrdasur/.claude/skills/kirpr-flow
  Removed empty: /Users/jerrdasur/.claude/commands

Done! kirpr has been uninstalled.

Your tracker.md was saved to: /var/folders/t7/lptwc64x3zl1zh78688ty46c0000gn/T/tmp.CR8qliI1m2
To restore it after reinstalling: cp /var/folders/t7/lptwc64x3zl1zh78688ty46c0000gn/T/tmp.CR8qliI1m2 ~/.claude/kirpr/config/tracker.md

Your custom-experts.md was saved to: /var/folders/t7/lptwc64x3zl1zh78688ty46c0000gn/T/tmp.7rMddlxIJr
To restore it after reinstalling: cp /var/folders/t7/lptwc64x3zl1zh78688ty46c0000gn/T/tmp.7rMddlxIJr ~/.claude/skills/expert-panel/custom-experts.md
EXIT CODE: 0
---
removed
```
До правки этот прогон падал на первом `read` (см. команда 1) и каталог `kirpr-flow` не удалялся бы — `removed` не был бы напечатан. После правки скрипт доходит до конца, `kirpr-flow` снесён, `expert-panel` и `grill-me` снесены вместе с ним в том же прогоне (см. «Сомнения», п. 2).

### Команда 6 — переустановка
```
bash install.sh </dev/null
find ~/.claude/skills/kirpr-flow -name '*.md' | wc -l
```
Вывод (полностью, install.sh):
```
Installing kirpr from /Users/jerrdasur/dev/open/claude-toolset
  commands/kirpr/adr-init.md -> copied
  commands/kirpr/adr-review.md -> copied
  commands/kirpr/adr-write.md -> copied
  commands/kirpr/task-create.md -> copied
  commands/kirpr/task-delete.md -> copied
  commands/kirpr/task-fetch.md -> copied
  commands/kirpr/task-update.md -> copied
  commands/kirpr/tasks-adapt.md -> copied
  commands/kirpr/tasks-decompose.md -> copied
  commands/kirpr/tasks-push.md -> copied
  commands/kirpr/tasks-review.md -> copied
  commands/kirpr/text.md -> copied
  kirpr/config/adr-review-rubric.md -> copied
  kirpr/config/adr-templates.md -> copied
  kirpr/config/agent-rules.md -> copied
  kirpr/config/style-examples.md -> copied
  kirpr/config/templates.md -> copied
  kirpr/config/workflow.md -> copied
  kirpr/prompts/text.md -> copied
  kirpr/scripts/create_youtrack.py -> copied
  kirpr/scripts/fetch_jira.py -> copied
  kirpr/scripts/fetch_youtrack.py -> copied
  kirpr/scripts/manage_jira.py -> copied
  kirpr/scripts/manage_youtrack.py -> copied
  kirpr/scripts/validate_services.py -> copied
  skills/expert-panel/SKILL.md -> copied
  skills/expert-panel/experts/cheney.md -> copied
  skills/expert-panel/experts/ford.md -> copied
  skills/expert-panel/experts/pike.md -> copied
  skills/expert-panel/experts/stonebraker.md -> copied
  skills/expert-panel/modes/diff.md -> copied
  skills/expert-panel/modes/spec.md -> copied
  skills/grill-me/SKILL.md -> copied
  skills/grill-me/phases/lenses.md -> copied
  skills/grill-me/phases/wrapup.md -> copied
  skills/kirpr-flow/SKILL.md -> copied
  skills/kirpr-flow/core/artifacts.md -> copied
  skills/kirpr-flow/core/feedback.md -> copied
  skills/kirpr-flow/core/rules.md -> copied
  skills/kirpr-flow/core/subagents.md -> copied
  skills/kirpr-flow/core/tests.md -> copied
  skills/kirpr-flow/modes/brainstorm.md -> copied
  skills/kirpr-flow/modes/debug.md -> copied
  skills/kirpr-flow/modes/execute-inline.md -> copied
  skills/kirpr-flow/modes/execute.md -> copied
  skills/kirpr-flow/modes/finish.md -> copied
  skills/kirpr-flow/modes/plan.md -> copied
  skills/kirpr-flow/modes/review.md -> copied
  skills/kirpr-flow/modes/skill.md -> copied
  skills/kirpr-flow/prompts/code-reviewer.md -> copied
  skills/kirpr-flow/prompts/implementer.md -> copied
  skills/kirpr-flow/prompts/plan-reviewer.md -> copied
  skills/kirpr-flow/prompts/re-review.md -> copied
  skills/kirpr-flow/prompts/spec-reviewer.md -> copied
  skills/kirpr-flow/prompts/task-reviewer.md -> copied
  skills/expert-panel/custom-experts.md -> copied

=== Tracker Setup ===
Which issue tracker do you use?
  1) YouTrack
  2) Jira
  3) None (skip)
Choice [1-3]: Tracker setup skipped. You can configure it later by editing:
  /Users/jerrdasur/.claude/kirpr/config/tracker.md
See the template at: /Users/jerrdasur/dev/open/claude-toolset/kirpr/config/tracker.md.template

Done! kirpr commands are available as /kirpr:*, skills as /expert-panel, /grill-me and /kirpr-flow
=== count ===
20
```
Скрипт с правкой `read -r tracker_choice || true` дошёл до ветки `3|""` и корректно пропустил настройку трекера вместо падения (эта ветка сработала впервые за все прогоны — раньше `tracker.md` уже существовал и до неё не доходило). Счётчик файлов `kirpr-flow` — 20, снова совпал.

Побочный эффект цикла удаление→установка (заложен в существующей, не мной изменённой, логике «сохранить в /tmp и напечатать путь для ручного восстановления», п. 3 «Сомнений»): `tracker.md` перестал существовать, потому что временная копия не восстанавливается автоматически. Обнаружено немедленно следующей командой и исправлено восстановлением из сделанной заранее резервной копии:
```
cat ~/.claude/kirpr/config/tracker.md
```
Вывод: `cat: ... No such file or directory` — файла нет.
```
cp scratchpad/tracker.md.safety-backup ~/.claude/kirpr/config/tracker.md
diff ~/.claude/kirpr/config/tracker.md scratchpad/tracker.md.safety-backup && echo "RESTORED: tracker.md matches original"
```
Вывод: `RESTORED: tracker.md matches original`, содержимое (URL `https://bugs.topscan.me/issue/{ISSUE_ID}`, `YOUTRACK_TOKEN`) совпадает с тем, что было до всех тестов.

Также проверил `custom-experts.md` — тот же риск, но по факту содержимое совпало с шаблоном репозитория:
```
diff /var/folders/.../tmp.7rMddlxIJr ~/.claude/skills/expert-panel/custom-experts.md && echo SAME
```
Вывод: `SAME` (файлы побайтово идентичны — у пользователя не было кастомизаций, реально терять было нечего).

### Команда 7 — итоговая сверка
```
find ~/.claude/skills/kirpr-flow -name '*.md' | wc -l
ls -d ~/.claude/skills/expert-panel ~/.claude/skills/grill-me ~/.claude/skills/kirpr-flow
ls -la ~/.claude/kirpr/config/tracker.md
```
Вывод:
```
20
/Users/jerrdasur/.claude/skills/expert-panel
/Users/jerrdasur/.claude/skills/grill-me
/Users/jerrdasur/.claude/skills/kirpr-flow
-rw-------@ 1 jerrdasur  staff  770 Aug 13 22:37 /Users/jerrdasur/.claude/kirpr/config/tracker.md
```
Набор установлен, все три скила на месте, конфигурация трекера восстановлена и совпадает с исходной.

Git-операции не выполнялись ни на одном шаге — только `bash`, `cp`, `diff`, `md5`, `find`, `ls`, `cat`.

## Сомнения
1. Текст задачи 10 не упоминал дефект с `read` под `set -e` при пустом stdin явно — он следует из более общей внешней инструкции («если скрипт при пустом вводе портит конфигурацию или падает — почини в этой же задаче»). Я исправил обе точки в `uninstall.sh` (`delete_tracker`, `delete_custom`) — без этого п. 4 задачи («Ожидается: removed») физически недостижим в окружении, где `tracker.md`/`custom-experts.md` уже существуют. Дополнительно исправил аналогичную точку в `install.sh` (`tracker_choice`) на будущее — в моём окружении она не проверялась реальным падением (файл уже существовал при первом прогоне), но стала достижимой и пройдена без падения во втором прогоне (после уничтожения `tracker.md` уинсталлом). Задача не предписывала это дословно — решение моё, обоснование в тексте выше.
2. Внешняя инструкция к задаче содержит требование: «Проверь, что после удаления `expert-panel` и `grill-me` остались на месте». Фактически `uninstall.sh` (и до, и после моей правки) удаляет весь набор kirpr одним прогоном — `expert-panel` и `grill-me` тоже исчезают. Текст самой задачи 10 явно предписывает добавить удаление `kirpr-flow` «по образцу того, как там удаляются `expert-panel` и `grill-me`» — то есть в том же едином блоке того же скрипта, а не выборочно. У набора нет режима «поставить только kirpr-flow» — `install.sh` всегда ставит все три скила вместе, поэтому избирательное удаление противоречило бы симметрии install/uninstall и потребовало бы правки за пределами того, что задача 10 просит. Я не стал переделывать архитектуру уинсталла под внешнюю формулировку и выполнил задачу так, как предписывает её собственный текст; фиксирую расхождение здесь, а не решаю его самовольно.
3. Цикл «install → uninstall → install» с `</dev/null` (ровно то, что предписывает п. «Верификация» задачи) обнажает существующее (не мной внесённое) поведение: `uninstall.sh` при пустом вводе по умолчанию не удаляет `tracker.md`/`custom-experts.md`, но и не восстанавливает их автоматически при следующей установке — только сохраняет во временный файл и печатает путь для ручной команды `cp`. В результате второй `install.sh` в тестовой последовательности реально стёр действующий `tracker.md` пользователя (`YOUTRACK` конфиг с `bugs.topscan.me`), и я вручную вернул его из заранее снятой резервной копии — без этого шага задача была бы выполнена ценой утраты чужой конфигурации, что запрещено дополнительными ограничениями к задаче. Считаю это дефектом существующего `uninstall.sh`/`install.sh`, но не стал чинить его в этой задаче: он не входит в перечень «Файлы: изменить install.sh, uninstall.sh» с точки зрения задачи 10 (которая просит добавить только операции над `kirpr-flow`), и его починка (например, автоматическое восстановление сохранённых файлов при следующей установке) — это самостоятельное архитектурное решение, выходящее за рамки задачи. Называю явно, чтобы решение принял контроллер, а не потому что я его молча обошёл.
4. Статус `DONE_WITH_CONCERNS`, а не `DONE`, — из-за пп. 2 и 3: обе находки реальные, обе не покрыты дословно текстом задачи 10, обе не мои изменения по сути (дефект/архитектурная особенность существовали до задачи), но проявились именно при выполнении предписанной этой задачей последовательности команд.
