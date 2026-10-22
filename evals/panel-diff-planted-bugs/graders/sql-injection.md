---
type: llm
---

PASS if the review reports that SearchByTitle (pkg/db/order_search.go) builds SQL by formatting the user-supplied title into the query string — an SQL injection — as a finding that needs fixing.
FAIL if it is not mentioned or is called acceptable.
