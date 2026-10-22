---
type: llm
---

PASS if the review reports that GetByID dereferences o.Address.City while Address is a pointer that ByID never fills, so it panics on nil.
FAIL otherwise.
