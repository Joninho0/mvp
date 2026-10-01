# ADR-004: Double-Entry Ledger System

## Status

Accepted

## Context

Bank transactions must maintain accounting integrity:
- Every debit has a matching credit
- Total sum of all entries is always zero
- Balances are derivable from entries

## Decision

We will implement a **double-entry ledger** with:
1. Each transaction creates 2+ ledger entries
2. Entries are immutable (append-only)
3. Reconciliation job validates the accounting equation

## Data Model

```
Transaction
├── LedgerEntry (DEBIT to source account)
└── LedgerEntry (CREDIT to destination account)
```

For internal operations (deposit/withdrawal):
```
Transaction (DEPOSIT)
└── LedgerEntry (CREDIT to customer account)
    └── LedgerEntry (DEBIT to settlement account)
```

## Invariants

1. `SUM(credits) - SUM(debits) = 0` per transaction
2. `Account.balance = SUM(entries) WHERE account=that_account`
3. All entries reference a transaction

## Consequences

### Positive
- Mathematical guarantee of integrity
- Easy reconciliation
- Audit trail
- Financial reporting capabilities

### Negative
- More complex than simple balance updates
- Slightly higher storage
- Requires careful transaction management

## Reconciliation Job

```python
def reconcile():
    for account in accounts:
        calculated = sum_ledger_entries(account)
        if calculated != account.balance:
            log_discrepancy(account, calculated)
```

Runs hourly via Celery Beat.