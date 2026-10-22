---
type: llm
---

PASS if the review reports that a new Status constant (StatusCancelled) was added under //go:generate stringer while status_string.go was not regenerated.
FAIL if this is not reported, or reported only as minor with low confidence.
