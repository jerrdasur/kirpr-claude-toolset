---
type: llm
---

PASS if the final message asks the user which mode to run (spec or diff) and does not start a review.
FAIL if it starts reviewing something, guesses a mode, or does not ask.
