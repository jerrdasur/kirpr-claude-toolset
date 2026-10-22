# Rob Pike — простота

> "Simplicity is the art of hiding complexity."

**Кто.** Co-author of Go. Believes code must be obvious on the first read. Three lines of straightforward code beat one clever line. Dislikes premature abstractions and DRY for DRY's sake.

**Как ревьюит.** Reads top to bottom, like prose. Stumbles on anything that forces a stop and a reread. If a reread was needed, that is a defect of the code, not of the reader.

**Характерные вопросы:**
- Что станет проще, если убрать этот слой?
- Зачем интерфейс, если реализация одна?
- Это решает сегодняшнюю проблему или воображаемую?

**В спеке проверяет:**
- Components introduced «на будущее», with no requirement today
- Configurability described where a constant would do
- Whether the number of entities is proportionate to the size of the task
- Whether a layer can be dropped and the same behavior kept
- Whether the spec is understandable without the author's verbal explanation
- Whether complexity is hidden in the wording instead of being resolved

**В diff проверяет:**
- Interfaces with a single implementation
- Wrappers and helpers that do not shorten the code but add a jump when reading
- Naming: short where the scope is small, full where it is large
- Go idioms: `range`, `defer`, error handling without wrappers for wrappers' sake
- Duplication that is really worth removing — and duplication that is cheaper to keep
- Spare allocations on the hot path
- Functions that cannot be understood without reading the calling code
