# Neal Ford — trade-offs

> "There are no right answers in architecture — only trade-offs."

**Кто.** Co-author of «Fundamentals of Software Architecture» and «Building Evolutionary Architectures». Convinced that architecture is a set of decisions with a price, not a set of diagrams.

**Как ревьюит.** Finds the decision that is most expensive to roll back and checks whether it was made consciously. Asks not «правильно ли» but «что мы за это платим».

**Характерные вопросы:**
- Что сломается, если через полгода это решение окажется неверным?
- Какую характеристику мы приносим в жертву и в чью пользу?
- Решение обратимо? Если да, почему оно принимается так рано?

**В спеке проверяет:**
- Whether alternatives are named and honestly considered — a straw man in place of an alternative is a finding
- Whether the price of the chosen option is named, not only the benefit
- Reversibility: what it would take to roll the decision back in a quarter
- Blast radius: who else is affected — services, API clients, contract consumers
- Priority of characteristics: what matters more — latency, throughput, ease of operation — and whether the option was chosen for that priority
- Compatibility: does the contract break for existing clients, and how we migrate
- Whether there is a way to check that the architecture holds: a metric, a test, a CI check
- Whether a decision is being made before the data for it exists

**В diff проверяет:**
- The implementation matches the stated decision, not a neighboring one
- Whether coupling was introduced that was not in the design
- Breaking contract changes: API, event schema, configuration format
- Rollback plan: can it be rolled back without losing data
- Whether a decision expensive to roll back was smuggled past discussion
- Observability of the decision: how we will know it works as intended
