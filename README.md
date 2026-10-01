# Bank MVP - Digital Bank in Three Architectures

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue" alt="Python">
  <img src="https://img.shields.io/badge/Django-5.0-green" alt="Django">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="MIT">
</p>

A complete digital bank MVP implemented three times in Python to demonstrate architectural trade-offs:

1. **MVT** (Django Monolithic) - Strong consistency, ACID transactions
2. **Microservices** (FastAPI + Kafka) - Distributed systems, event-driven
3. **Serverless** (AWS Lambda + DynamoDB) - Cloud-native, pay-per-use

## Features

- ✅ Customer registration with KYC
- ✅ Multiple accounts per customer
- ✅ Deposits, withdrawals, transfers
- ✅ Double-entry ledger with reconciliation
- ✅ Idempotency keys
- ✅ Fraud detection
- ✅ Async notifications
- ✅ Audit trail with hash chaining
- ✅ Complete API documentation

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/bank-mvp.git
cd bank-mvp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -e .

# Start infrastructure
docker compose up -d

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

### Access

- **Web App**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs/
- **Admin**: http://localhost:8000/admin/

## Project Structure

```
bank-mvp/
├── apps/                    # Django apps
│   ├── accounts/           # Account management
│   ├── customers/          # User management
│   ├── transactions/       # Transaction processing
│   ├── ledger/            # Double-entry ledger
│   ├── fraud/             # Fraud detection
│   ├── notifications/     # Async notifications
│   └── audit/             # Audit logging
├── core/                   # Shared utilities
├── tests/                  # Test suite
├── docs/                   # Documentation
│   └── adr/               # Architecture Decision Records
├── templates/              # HTML templates
└── config/                 # Django configuration
```

## API Endpoints

### Authentication
```
POST /api/auth/register/     # Register new user
POST /api/auth/login/        # Login (returns JWT)
POST /api/auth/refresh/      # Refresh token
```

### Accounts
```
GET    /api/accounts/                    # List accounts
POST   /api/accounts/                    # Create account
GET    /api/accounts/{id}/               # Account details
GET    /api/accounts/{id}/balance/       # Get balance
GET    /api/accounts/{id}/statement/     # Get statement
```

### Transactions
```
POST /api/transactions/deposit/    # Deposit money
POST /api/transactions/withdraw/   # Withdraw money
POST /api/transactions/transfer/   # Transfer money
GET  /api/transactions/            # List transactions
GET  /api/transactions/{id}/       # Transaction details
POST /api/transactions/{id}/reverse/  # Reverse transaction
```

## Concurrency Handling

This project demonstrates the importance of proper locking:

### Without Locking (Bug)
```python
# DON'T DO THIS - race condition!
def transfer(amount):
    if balance >= amount:
        balance -= amount  # Another thread can modify here!
```

### With Ordered Locking (Correct)
```python
# Lock accounts in deterministic order
def transfer(source, dest, amount):
    accounts = sorted([source, dest], key=lambda a: a.id)
    with transaction.atomic():
        for acc in accounts:
            Account.objects.select_for_update().get(id=acc.id)
        if source.balance >= amount:
            source.balance -= amount
            dest.balance += amount
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_concurrency.py

# Run load tests
locust -f tests/locustfile.py
```

## Key Concepts

### Money Handling
- Always use `Decimal`, never `float`
- Use `Money` class for type safety
- Store in smallest unit (cents) or use Decimal with 2 decimal places

### Idempotency
- All write operations support `Idempotency-Key` header
- Same key + same request = same response
- Keys expire after 7 days

### Security
- JWT authentication with RS256
- Argon2 password hashing
- Rate limiting (100 req/hour anonymous, 1000 req/hour authenticated)
- MFA support with TOTP
- All sensitive data encrypted at rest (CPF, etc.)

## Architecture Comparison

| Aspect | MVT | Microservices | Serverless |
|--------|-----|---------------|------------|
| **Complexity** | Low | High | Medium |
| **Consistency** | Strong (ACID) | Eventual | Strong (Transactions) |
| **Deployment** | Simple | Complex | Simple |
| **Cost** | Medium | High | Pay-per-use |
| **Scalability** | Vertical | Horizontal | Automatic |
| **Observability** | Easy | Complex | Medium |

## Learnings

Each architecture teaches different lessons:

### MVT (Start Here)
- Database transactions and locking
- Domain-driven design
- Task queues (Celery)
- Web frameworks (Django)

### Microservices
- Distributed systems
- Event-driven architecture (Kafka)
- Saga pattern for distributed transactions
- Service discovery, load balancing

### Serverless
- Cloud-native design
- DynamoDB single-table design
- Step Functions orchestration
- AWS IAM, Lambda, API Gateway

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit PR

## License

MIT License - See LICENSE file for details.

## References

- [Django Documentation](https://docs.djangoproject.com/)
- [PostgreSQL Transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html)
- [OWASP API Security](https://owasp.org/API-Security/)
- [AWS Serverless Patterns](https://serverlessland.com/)