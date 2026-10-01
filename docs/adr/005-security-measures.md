# ADR-005: Security Implementation Strategy

## Status

Accepted

## Context

A bank application requires robust security measures:
- Customer data protection (PII)
- Financial transaction security
- Authentication & authorization
- Defense against common attacks

## Decision

We will implement a defense-in-depth strategy:

### 1. Authentication
- JWT with RS256 (asymmetric encryption)
- Refresh tokens with rotation
- Optional MFA with TOTP
- Brute force protection (django-axes)

### 2. Data Protection
- Password hashing with Argon2
- Sensitive data encryption at rest (CPF, etc.)
- HTTPS everywhere
- CSP headers

### 3. API Security
- Rate limiting (per user/IP)
- Input validation (Pydantic)
- Output serialization (no sensitive fields)
- CORS restrictions

### 4. Authorization
- Object-level permissions
- Row-level security (Django's models)
- Audit logging

### 5. Infrastructure
- WAF for HTTP traffic filtering
- Secrets management
- Network isolation

## Implementation Details

### Password Hashing
```python
# Using Argon2 (winner of Password Hashing Competition)
from django.contrib.auth.hashers import make_password

hashed = make_password(password, hasher="argon2")
```

### JWT Tokens
```python
# RS256 for production (asymmetric)
SIMPLE_JWT = {
    "ALGORITHM": "RS256",
    "SIGNING_KEY": private_key,
    "VERIFYING_KEY": public_key,
}
```

### Rate Limiting
```python
# Using django-ratelimit
@ratelimit(key="user", rate="100/h", block=True)
def api_view(request):
    # ...
```

## Consequences

### Positive
- Multiple layers of defense
- Compliance with financial regulations
- User trust

### Negative
- Operational complexity
- Performance overhead (encryption, hashing)
- User friction (MFA, rate limits)