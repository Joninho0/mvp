# ADR-001: MVP Architecture Decision

## Status

Accepted

## Context

We need to build a bank digital MVP with three different architectures:
1. MVT (Django monolithic)
2. Microservices (FastAPI + Kafka)
3. Serverless (AWS Lambda + Step Functions)

The key challenge is demonstrating trade-offs between these architectures while solving the same domain problems.

## Decision

We will implement the MVP three times, once in each architecture. Each implementation will:
- Share the same domain logic (in a `domain/` package)
- Follow the same OpenAPI contract
- Use the same test suite (black-box tests)

## Consequences

### Positive
- Direct comparison of trade-offs with real code
- Portfolio-ready demonstrations
- Learning all three approaches thoroughly

### Negative
- Triple the development effort
- Maintaining three codebases

## Trade-offs Demonstrated

| Aspect | MVT | Microservices | Serverless |
|--------|-----|---------------|------------|
| Complexity | Low | High | Medium |
| Scalability | Vertical | Horizontal | Automatic |
| Cost (low traffic) | Medium | High | Low |
| Operational Overhead | Low | High | Medium |
| Deployment | Simple | Complex | Simple |
| Testing | Easy | Hard | Medium |

## Implementation Plan

1. Start with MVT (Django) - foundation
2. Then Microservices (FastAPI) - distributed systems
3. Finally Serverless (AWS) - cloud-native

## References

- [Martin Fowler on Monoliths](https://martinfowler.com/bliki/MonolithFirst.html)
- [AWS Serverless Patterns](https://serverlessland.com/)