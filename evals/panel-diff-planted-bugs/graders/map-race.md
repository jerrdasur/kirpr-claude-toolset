---
type: llm
---

PASS if the review reports that GetByID writes s.cache from a goroutine without synchronization (data race on the map; the map may also be nil).
FAIL otherwise.
