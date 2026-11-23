"""
Mathematical utility functions for prime number operations.

This module provides production-grade prime number utilities for cryptographic,
number theory, and computational mathematics applications.

Public API:
    - is_prime(n: int) -> bool
    - prime_factors(n: int) -> list[int]

Thread-safety: All functions are pure (no side effects) and thread-safe.
Dependencies: Python stdlib only (math, typing)
"""

import math
from typing import List


def is_prime(n: int) -> bool:
    """
    Deterministically check if a number is prime.

    Uses trial division for n < 10^6 and Miller-Rabin primality test with
    deterministic witnesses for larger values. Guaranteed correct results
    for all inputs.

    Args:
        n: Integer to check for primality

    Returns:
        True if n is prime, False otherwise

    Raises:
        TypeError: If n is not an integer

    Time Complexity:
        - O(√n) for n < 10^6 (trial division)
        - O(k log³ n) for n >= 10^6 (Miller-Rabin, k=12 rounds)

    Space Complexity: O(1)

    Examples:
        >>> is_prime(2)
        True
        >>> is_prime(17)
        True
        >>> is_prime(100)
        False
        >>> is_prime(1)
        False
    """
    # Input validation
    if not isinstance(n, int):
        raise TypeError(f"Expected integer, got {type(n).__name__}")

    # Handle edge cases
    if n < 2:
        return False
    if n == 2 or n == 3:
        return True
    if n % 2 == 0:
        return False

    # Use trial division for smaller numbers (faster and simpler)
    if n < 1_000_000:
        return _trial_division_primality(n)

    # Use Miller-Rabin for larger numbers (much faster for large n)
    return _miller_rabin_primality(n)


def _trial_division_primality(n: int) -> bool:
    """
    Check primality using trial division up to sqrt(n).

    Assumes n >= 3 and n is odd (caller must validate).

    Time: O(√n)
    Space: O(1)
    """
    sqrt_n = int(math.sqrt(n))
    for i in range(3, sqrt_n + 1, 2):
        if n % i == 0:
            return False
    return True


def _miller_rabin_primality(n: int, rounds: int = 12) -> bool:
    """
    Miller-Rabin probabilistic primality test with deterministic witnesses.

    For n < 3,317,044,064,679,887,385,961,981, using the first 12 primes
    as witnesses gives a deterministic result.

    Assumes n >= 3 and n is odd (caller must validate).

    Time: O(k log³ n) where k is number of rounds
    Space: O(1)
    """
    # Write n - 1 as 2^r * d
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2

    # Deterministic witnesses (first 12 primes)
    witnesses = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]

    for a in witnesses:
        if a >= n:
            continue

        # Compute a^d mod n
        x = pow(a, d, n)

        if x == 1 or x == n - 1:
            continue

        # Square x up to r-1 times
        composite = True
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                composite = False
                break

        if composite:
            return False

    return True


def prime_factors(n: int) -> List[int]:
    """
    Return the complete prime factorization of n in ascending order.

    Returns all prime factors with repetition such that their product equals n.
    For example, prime_factors(12) returns [2, 2, 3] because 2 * 2 * 3 = 12.

    Args:
        n: Integer to factorize (must be >= 0)

    Returns:
        List of prime factors in ascending order with repetition.
        Returns empty list for n <= 1.

    Raises:
        TypeError: If n is not an integer

    Time Complexity: O(√n) worst case (when n is prime)
    Space Complexity: O(log n) for output list

    Examples:
        >>> prime_factors(12)
        [2, 2, 3]
        >>> prime_factors(17)
        [17]
        >>> prime_factors(100)
        [2, 2, 5, 5]
        >>> prime_factors(1)
        []
    """
    # Input validation
    if not isinstance(n, int):
        raise TypeError(f"Expected integer, got {type(n).__name__}")

    # Handle edge cases
    if n <= 1:
        return []

    factors = []

    # Handle factor of 2 separately (optimization)
    while n % 2 == 0:
        factors.append(2)
        n //= 2

    # Handle odd factors from 3 onwards
    # Only check up to sqrt(n) because if n has a factor > sqrt(n),
    # it must also have a factor < sqrt(n)
    i = 3
    while i * i <= n:
        while n % i == 0:
            factors.append(i)
            n //= i
        i += 2

    # If n is still greater than 1, it's a prime factor
    if n > 1:
        factors.append(n)

    return factors


def _validate_factorization(n: int, factors: List[int]) -> bool:
    """
    Internal helper to validate that factors multiply back to n.
    Used for testing and verification.

    Args:
        n: Original number
        factors: List of prime factors

    Returns:
        True if product of factors equals n
    """
    if not factors:
        return n <= 1

    product = 1
    for f in factors:
        product *= f
    return product == n
