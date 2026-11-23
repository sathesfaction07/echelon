# Prime Number Utilities Component

## Component Overview
A production-grade mathematical utility library providing prime number operations for cryptographic key generation, number theory applications, and computational mathematics workflows.

## Acceptance Criteria

### AC1: Correctness
- **AC1.1**: `is_prime(n)` correctly identifies all primes up to 10^6 against OEIS A000040
- **AC1.2**: `is_prime(n)` correctly rejects all composites in range [2, 10^6]
- **AC1.3**: `prime_factors(n)` produces factorizations that multiply back to original n
- **AC1.4**: Edge cases handled: n < 2, n = 2, negative inputs, zero, one

### AC2: Performance
- **AC2.1**: `is_prime(n)` completes in < 1ms for n < 10^6 (trial division acceptable)
- **AC2.2**: `is_prime(n)` completes in < 100ms for n < 10^9 (requires optimization)
- **AC2.3**: `prime_factors(n)` completes in < 10ms for n < 10^6
- **AC2.4**: Memory usage O(log n) for prime_factors output

### AC3: Production Quality
- **AC3.1**: Type hints on all public APIs
- **AC3.2**: Input validation with clear error messages for invalid types
- **AC3.3**: Docstrings with complexity analysis
- **AC3.4**: 100% test coverage on public APIs
- **AC3.5**: No external dependencies beyond Python stdlib

### AC4: Integration
- **AC4.1**: Pure functions (no side effects, thread-safe)
- **AC4.2**: Importable as `from mathx import is_prime, prime_factors`
- **AC4.3**: Compatible with Python 3.9+
- **AC4.4**: Error handling returns/raises, never crashes

## Business Context
This component supports:
- **Cryptography team**: Prime generation for RSA key setup
- **Data Science**: Number theory features for ML pipelines
- **Education platform**: Interactive math problem verification

## Technical Decisions

### Algorithm Selection

#### is_prime()
- **For n < 10^6**: Trial division (simple, fast enough, no false positives)
- **For n >= 10^6**: Miller-Rabin probabilistic test (deterministic variant with fixed witnesses)
- **Rationale**: Balances simplicity for small inputs with performance for large inputs

#### prime_factors()
- **Algorithm**: Trial division with optimizations (handle 2 separately, odd-only search)
- **Rationale**: Deterministic, simple, sufficient for expected input range (n < 10^9)
- **Alternative considered**: Pollard's rho (complex, overkill for current requirements)

### Complexity Analysis
- `is_prime(n)`: O(√n) worst case for trial division; O(k log³ n) for Miller-Rabin (k rounds)
- `prime_factors(n)`: O(√n) worst case; O(log n) for highly composite numbers
- Space: O(1) for is_prime; O(log n) for prime_factors (output size)

## Interface Contract

```python
def is_prime(n: int) -> bool:
    """
    Deterministically check if n is prime.
    
    Time: O(√n) for n < 10^6; O(log³ n) for n >= 10^6
    Space: O(1)
    
    Raises:
        TypeError: if n is not an integer
    """

def prime_factors(n: int) -> list[int]:
    """
    Return complete prime factorization with repetition.
    
    Time: O(√n) worst case
    Space: O(log n) for output
    
    Raises:
        TypeError: if n is not an integer
    """
```

## Operational Characteristics
- **Thread-safety**: Yes (pure functions, no shared state)
- **Memory**: Bounded by O(log n) for largest factorization
- **Failure modes**: TypeError for invalid input; otherwise deterministic
- **Monitoring**: Execution time should be logged by caller for inputs > 10^6
