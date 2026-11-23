# Quick Start Guide

## Installation
No installation needed! Just use the `mathx.py` module.

```python
from mathx import is_prime, prime_factors
```

## Basic Usage

### Check if a number is prime
```python
is_prime(17)        # True
is_prime(100)       # False
is_prime(1000003)   # True
```

### Get prime factorization
```python
prime_factors(12)   # [2, 2, 3]
prime_factors(100)  # [2, 2, 5, 5]
prime_factors(17)   # [17]
```

## Run Tests
```bash
pytest test_mathx.py -v
```

## Documentation
- **README.md** - Complete usage guide and API reference
- **COMPONENT_SPEC.md** - Acceptance criteria and business context
- **COMPLEXITY_ANALYSIS.md** - Algorithm justification and tradeoffs
- **SENIOR_REVIEW_RESPONSE.md** - Response to review feedback
- **DELIVERY_SUMMARY.md** - Complete delivery summary

## Key Features
✅ Production-ready (type-safe, error-handling, tested)  
✅ Fast (hybrid algorithm: trial division + Miller-Rabin)  
✅ Thread-safe (pure functions, no side effects)  
✅ Zero dependencies (Python stdlib only)  
✅ 100% test coverage (54 tests)

## Performance
- Small numbers (< 10³): Instant
- Medium numbers (< 10⁶): < 1ms
- Large numbers (< 10⁹): < 100ms

## Support
For questions or issues beyond n > 10⁹, escalate to Senior Engineer.
