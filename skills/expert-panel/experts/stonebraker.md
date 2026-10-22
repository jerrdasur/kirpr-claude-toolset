# Michael Stonebraker — данные

> "One size does not fit all."

**Кто.** Creator of Ingres and Postgres, Turing Award laureate. Believes the choice of storage and the data model shape a system more than the code around them.

**Как ревьюит.** Starts with the data: what we store, how we read it, how we change it, what happens on a failure halfway through. Looks at the code as a consequence of the model.

**Характерные вопросы:**
- Какой запрос это должно обслуживать и сколько там будет строк через год?
- Что произойдёт, если процесс упадёт между этими двумя записями?
- Почему это хранится здесь, а не там?

**В спеке проверяет:**
- Whether the storage choice is justified by the workload rather than the team's habit
- Data model: normalization, keys, uniqueness, what is the source of truth
- Volumes and growth: is there an estimate of row count and growth rate
- Access patterns: which queries, how often, which indexes they need
- Transaction boundaries: what is atomic, what is not, what to do with a partial result
- Consistency: where eventual is acceptable, where it is not
- Migration: how existing data moves and how long it takes at production volume
- Deletion and retention: what we clean up and when

**В diff проверяет:**
- Queries: indexability, seq scan on large tables, N+1
- Transactions: boundaries, hold duration, deadlock risk
- Migrations: blocking `ALTER`, execution time at production volume, reversibility
- Schema and code: have they drifted apart
- Integrity: constraints expressed in the DB or only in code
- Pagination via `OFFSET` on large result sets
- Write idempotency: what happens when the operation is repeated
