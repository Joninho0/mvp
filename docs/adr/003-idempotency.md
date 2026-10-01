# ADR-003: Idempotency Implementation

## Status

Accepted

## Context

Financial APIs must be idempotent to handle:
- Client retries (network failures, timeouts)
- Duplicate requests
- Replay attacks

## Decision

We will use **server-side idempotency keys** stored in the database:
1. Client provides `Idempotency-Key` header (UUID)
2. Server calculates request hash and stores with key
3. Duplicate requests with same key return cached response

## Implementation

### Flow
```
1. Client: POST /transfer (Idempotency-Key: abc123)
2. Server: INSERT INTO idempotency_records (key, hash, status)
3. Process request...
4. Server: UPDATE idempotency_records (response, status=COMPLETED)
5. Client receives response

6. Client: POST /transfer (Idempotency-Key: abc123)
7. Server: FIND BY KEY -> return cached response
```

### Storage
- Key: Unique constraint
- Request hash: SHA-256 for collision resistance
- TTL: 7 days (configurable)
- Status: IN_PROGRESS / COMPLETED / FAILED

## Consequences

### Positive
- Safe retries for clients
- Prevents duplicate transactions
- Audit trail of all requests

### Negative
- Storage overhead (minimal - ~200 bytes per record)
- Key management complexity
- TTL cleanup required

## Alternative Considered

**Client-managed idempotency** (stateless) was rejected because:
- Requires cryptographic verification of request body
- Complex signature scheme
- No way to prevent replay attacks