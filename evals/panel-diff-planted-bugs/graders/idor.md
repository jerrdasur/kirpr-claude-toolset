---
type: llm
---

PASS if the review reports that GetByID (pkg/rpc/order.go) returns an order without checking that it belongs to userID (IDOR / missing ownership check) as a finding that needs fixing.
FAIL otherwise.
