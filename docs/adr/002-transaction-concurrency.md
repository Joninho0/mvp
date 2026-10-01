# ADR-002: Transaction Concurrency Strategy

## Status

Accepted

## Context

Bank transfers must be processed atomically to prevent:
- Double spending (balance going negative)
- Lost updates (concurrent transfers)
- Deadlocks (A→B and B→A simultaneously)

## Decision

We will use **pessimistic locking with ordered acquisition**:
1. Use `SELECT ... FOR UPDATE` to lock accounts
2. Always acquire locks in consistent order (by account ID)
3. Hold locks for the minimum time needed

## Implementation

### Django (MVT)
```python
with transaction.atomic():
    # Lock accounts in order
    accounts = [source, destination]
    accounts.sort(key=lambda a: a.id)
    for account in accounts:
        Account.objects.select_for_update().get(id=account.id)
    # Perform transfer
```

### Why not optimistic locking?

Optimistic locking (with version field) requires:
- Retry logic on version conflict
- User experience impact (transactions fail randomly)
- Complex compensation for financial operations

Pessimistic locking provides:
- Strong consistency guarantee
- Simpler error handling
- Better user experience (fail fast vs fail late)

## Consequences

### Positive
- Strong consistency
- No balance overdrafts
- Deterministic behavior

### Negative
- Potential lock contention under high load
- Slightly higher latency
- Requires ordered lock acquisition to prevent deadlocks

## Performance

Under normal load (< 100 TPS), the locking overhead is negligible. For higher throughput:
- Consider sharding by account ID
- Use read replicas for balance queries
- Implement request queuing