"""
Comprehensive test suite for mathx module.

Test categories:
1. Correctness tests (edge cases, known primes/composites)
2. Property-based tests (factorization validity)
3. Performance tests (realistic input distributions)
4. Integration tests (type safety, error handling)
"""

import time

import pytest
from mathx import _validate_factorization, is_prime, prime_factors

# ============================================================================
# CORRECTNESS TESTS - is_prime()
# ============================================================================


class TestIsPrimeCorrectness:
    """Test correctness of is_prime() function."""

    def test_edge_case_negative(self):
        """Negative numbers are not prime."""
        assert is_prime(-1) is False
        assert is_prime(-5) is False
        assert is_prime(-100) is False
        assert is_prime(-1000000) is False

    def test_edge_case_zero(self):
        """Zero is not prime."""
        assert is_prime(0) is False

    def test_edge_case_one(self):
        """One is not prime by definition."""
        assert is_prime(1) is False

    def test_edge_case_two(self):
        """Two is the smallest prime."""
        assert is_prime(2) is True

    def test_edge_case_three(self):
        """Three is prime."""
        assert is_prime(3) is True

    def test_small_primes(self):
        """First 25 primes (OEIS A000040)."""
        small_primes = [
            2,
            3,
            5,
            7,
            11,
            13,
            17,
            19,
            23,
            29,
            31,
            37,
            41,
            43,
            47,
            53,
            59,
            61,
            67,
            71,
            73,
            79,
            83,
            89,
            97,
        ]
        for p in small_primes:
            assert is_prime(p) is True, f"{p} should be prime"

    def test_small_composites(self):
        """Common small composite numbers."""
        composites = [
            4,
            6,
            8,
            9,
            10,
            12,
            14,
            15,
            16,
            18,
            20,
            21,
            22,
            24,
            25,
            26,
            27,
            28,
            30,
            32,
            33,
            34,
            35,
            36,
            38,
            39,
            40,
        ]
        for c in composites:
            assert is_prime(c) is False, f"{c} should be composite"

    def test_even_numbers(self):
        """All even numbers > 2 are composite."""
        for n in range(4, 1000, 2):
            assert is_prime(n) is False, f"{n} should be composite (even)"

    def test_perfect_squares(self):
        """Perfect squares are always composite (except 1, which isn't prime anyway)."""
        for i in range(2, 100):
            assert is_prime(i * i) is False, f"{i * i} should be composite (perfect square)"

    def test_medium_primes(self):
        """Medium-sized primes (100 < p < 10000)."""
        medium_primes = [
            101,
            1009,
            1013,
            1019,
            1021,
            1031,
            1033,
            1039,
            1049,
            1051,
            1061,
            1063,
            1069,
            1087,
            1091,
            1093,
            1097,
            1103,
            1109,
            1117,
            1123,
            1129,
            9973,
            9967,
            9949,
        ]
        for p in medium_primes:
            assert is_prime(p) is True, f"{p} should be prime"

    def test_large_primes_trial_division(self):
        """Large primes < 10^6 (uses trial division path)."""
        large_primes = [104729, 104743, 999983, 999979, 999961]
        for p in large_primes:
            assert is_prime(p) is True, f"{p} should be prime"

    def test_large_composites_trial_division(self):
        """Large composites < 10^6."""
        large_composites = [104730, 999982, 999980, 1000000]
        for c in large_composites:
            assert is_prime(c) is False, f"{c} should be composite"

    def test_very_large_primes_miller_rabin(self):
        """Very large primes >= 10^6 (uses Miller-Rabin path)."""
        very_large_primes = [
            1000003,
            1000033,
            1000037,
            1000039,
            10000019,
            10000079,
            10000103,
            100000007,
            100000037,
            1000000007,
            1000000009,
        ]
        for p in very_large_primes:
            assert is_prime(p) is True, f"{p} should be prime"

    def test_very_large_composites_miller_rabin(self):
        """Very large composites >= 10^6."""
        very_large_composites = [
            1000002,
            1000004,
            1000005,
            1000006,
            10000020,
            10000080,
            10000104,
            100000008,
            100000038,
            1000000008,
            1000000010,
        ]
        for c in very_large_composites:
            assert is_prime(c) is False, f"{c} should be composite"

    def test_mersenne_primes(self):
        """Mersenne primes: 2^p - 1 for prime p."""
        # Small Mersenne primes
        mersenne_primes = [3, 7, 31, 127, 8191, 131071, 524287]
        for mp in mersenne_primes:
            assert is_prime(mp) is True, f"Mersenne prime {mp} should be prime"

    def test_carmichael_numbers(self):
        """Carmichael numbers (pseudoprimes that fool Fermat test)."""
        # These are composite but pass many primality tests
        carmichael = [561, 1105, 1729, 2465, 2821, 6601, 8911]
        for c in carmichael:
            assert is_prime(c) is False, f"Carmichael number {c} should be composite"


# ============================================================================
# CORRECTNESS TESTS - prime_factors()
# ============================================================================


class TestPrimeFactorsCorrectness:
    """Test correctness of prime_factors() function."""

    def test_edge_case_negative(self):
        """Negative numbers return empty list."""
        assert prime_factors(-1) == []
        assert prime_factors(-5) == []
        assert prime_factors(-100) == []

    def test_edge_case_zero(self):
        """Zero returns empty list."""
        assert prime_factors(0) == []

    def test_edge_case_one(self):
        """One returns empty list."""
        assert prime_factors(1) == []

    def test_edge_case_two(self):
        """Two returns [2]."""
        assert prime_factors(2) == [2]

    def test_small_primes(self):
        """Prime numbers return themselves."""
        small_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]
        for p in small_primes:
            assert prime_factors(p) == [p], f"Prime {p} should return [{p}]"

    def test_powers_of_two(self):
        """Powers of 2 return correct factorization."""
        assert prime_factors(4) == [2, 2]
        assert prime_factors(8) == [2, 2, 2]
        assert prime_factors(16) == [2, 2, 2, 2]
        assert prime_factors(32) == [2, 2, 2, 2, 2]
        assert prime_factors(1024) == [2] * 10

    def test_powers_of_primes(self):
        """Powers of primes return correct factorization."""
        assert prime_factors(9) == [3, 3]  # 3^2
        assert prime_factors(27) == [3, 3, 3]  # 3^3
        assert prime_factors(25) == [5, 5]  # 5^2
        assert prime_factors(125) == [5, 5, 5]  # 5^3
        assert prime_factors(49) == [7, 7]  # 7^2

    def test_small_composites(self):
        """Small composite numbers."""
        assert prime_factors(6) == [2, 3]
        assert prime_factors(10) == [2, 5]
        assert prime_factors(12) == [2, 2, 3]
        assert prime_factors(15) == [3, 5]
        assert prime_factors(20) == [2, 2, 5]
        assert prime_factors(30) == [2, 3, 5]

    def test_medium_composites(self):
        """Medium composite numbers."""
        assert prime_factors(60) == [2, 2, 3, 5]
        assert prime_factors(100) == [2, 2, 5, 5]
        assert prime_factors(210) == [2, 3, 5, 7]
        assert prime_factors(1000) == [2, 2, 2, 5, 5, 5]

    def test_large_composites(self):
        """Large composite numbers."""
        assert prime_factors(10000) == [2, 2, 2, 2, 5, 5, 5, 5]
        assert prime_factors(99999) == [3, 3, 41, 271]
        assert prime_factors(100000) == [2, 2, 2, 2, 2, 5, 5, 5, 5, 5]

    def test_semiprimes(self):
        """Semiprimes (product of exactly two primes)."""
        assert prime_factors(6) == [2, 3]
        assert prime_factors(15) == [3, 5]
        assert prime_factors(21) == [3, 7]
        assert prime_factors(35) == [5, 7]
        assert prime_factors(77) == [7, 11]
        assert prime_factors(143) == [11, 13]

    def test_highly_composite(self):
        """Highly composite numbers (many small factors)."""
        # 2520 = 2^3 * 3^2 * 5 * 7
        assert prime_factors(2520) == [2, 2, 2, 3, 3, 5, 7]
        # 5040 = 2^4 * 3^2 * 5 * 7
        assert prime_factors(5040) == [2, 2, 2, 2, 3, 3, 5, 7]

    def test_large_prime(self):
        """Large prime numbers."""
        assert prime_factors(104729) == [104729]
        assert prime_factors(1000003) == [1000003]

    def test_product_of_large_primes(self):
        """Product of two large primes."""
        # 101 * 103 = 10403
        assert prime_factors(10403) == [101, 103]
        # 1009 * 1013 = 1022117
        assert prime_factors(1022117) == [1009, 1013]


# ============================================================================
# PROPERTY-BASED TESTS
# ============================================================================


class TestPropertyBased:
    """Property-based tests to verify mathematical invariants."""

    def test_factorization_product_equals_input(self):
        """Product of prime factors should equal original number."""
        test_cases = [2, 6, 12, 60, 100, 1000, 9999, 10000, 104729, 999983]
        for n in test_cases:
            factors = prime_factors(n)
            assert _validate_factorization(n, factors), f"Factors {factors} don't multiply to {n}"

    def test_all_factors_are_prime(self):
        """All returned factors should be prime."""
        test_cases = [6, 12, 60, 100, 1000, 9999, 10000]
        for n in test_cases:
            factors = prime_factors(n)
            for f in factors:
                assert is_prime(f), f"Factor {f} of {n} is not prime"

    def test_factors_sorted_ascending(self):
        """Factors should be returned in ascending order."""
        test_cases = [6, 12, 60, 100, 1000, 9999, 10000]
        for n in test_cases:
            factors = prime_factors(n)
            assert factors == sorted(factors), f"Factors {factors} not sorted for {n}"

    def test_prime_has_single_factor(self):
        """Prime numbers should have exactly one factor (themselves)."""
        primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]
        for p in primes:
            factors = prime_factors(p)
            assert len(factors) == 1, f"Prime {p} has {len(factors)} factors"
            assert factors[0] == p, f"Prime {p} factor is {factors[0]}"

    def test_composite_has_multiple_factors(self):
        """Composite numbers should have at least 2 factors."""
        composites = [4, 6, 8, 9, 10, 12, 14, 15, 16, 18, 20]
        for c in composites:
            factors = prime_factors(c)
            assert len(factors) >= 2, f"Composite {c} has only {len(factors)} factors"


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


class TestPerformance:
    """Performance tests with realistic input distributions."""

    def test_is_prime_small_numbers_performance(self):
        """is_prime should be fast for small numbers (< 10^6)."""
        start = time.time()
        for n in range(2, 10000):
            is_prime(n)
        elapsed = time.time() - start
        # Should process 10k numbers in well under 1 second
        assert elapsed < 1.0, f"Small number primality too slow: {elapsed:.3f}s"

    def test_is_prime_large_primes_performance(self):
        """is_prime should handle large primes efficiently."""
        large_primes = [1000003, 10000019, 100000007]
        start = time.time()
        for p in large_primes:
            assert is_prime(p) is True
        elapsed = time.time() - start
        # Should complete in under 100ms total
        assert elapsed < 0.1, f"Large prime checking too slow: {elapsed:.3f}s"

    def test_is_prime_large_composites_performance(self):
        """is_prime should handle large composites efficiently."""
        # Composites with small factors are detected quickly
        large_composites = [1000002, 10000020, 100000008]
        start = time.time()
        for c in large_composites:
            assert is_prime(c) is False
        elapsed = time.time() - start
        assert elapsed < 0.1, f"Large composite checking too slow: {elapsed:.3f}s"

    def test_prime_factors_small_numbers_performance(self):
        """prime_factors should be fast for small numbers."""
        start = time.time()
        for n in range(2, 1000):
            prime_factors(n)
        elapsed = time.time() - start
        assert elapsed < 0.5, f"Small number factorization too slow: {elapsed:.3f}s"

    def test_prime_factors_worst_case_performance(self):
        """prime_factors worst case: large primes."""
        # Worst case is when n is prime (must check all divisors up to sqrt(n))
        large_primes = [104729, 1000003]
        start = time.time()
        for p in large_primes:
            factors = prime_factors(p)
            assert factors == [p]
        elapsed = time.time() - start
        # Should complete in under 10ms
        assert elapsed < 0.01, f"Prime factorization too slow: {elapsed:.3f}s"

    def test_prime_factors_highly_composite_performance(self):
        """prime_factors should handle highly composite numbers efficiently."""
        # Numbers with many small factors are actually fast
        highly_composite = [2520, 5040, 10080, 20160]
        start = time.time()
        for n in highly_composite:
            prime_factors(n)
        elapsed = time.time() - start
        assert elapsed < 0.01, f"Highly composite factorization too slow: {elapsed:.3f}s"


# ============================================================================
# INTEGRATION & ERROR HANDLING TESTS
# ============================================================================


class TestIntegrationAndErrorHandling:
    """Test type safety, error handling, and integration characteristics."""

    def test_is_prime_type_error_float(self):
        """is_prime should raise TypeError for float input."""
        with pytest.raises(TypeError, match="Expected integer"):
            is_prime(3.14)

    def test_is_prime_type_error_string(self):
        """is_prime should raise TypeError for string input."""
        with pytest.raises(TypeError, match="Expected integer"):
            is_prime("17")

    def test_is_prime_type_error_none(self):
        """is_prime should raise TypeError for None input."""
        with pytest.raises(TypeError, match="Expected integer"):
            is_prime(None)

    def test_is_prime_type_error_list(self):
        """is_prime should raise TypeError for list input."""
        with pytest.raises(TypeError, match="Expected integer"):
            is_prime([2, 3, 5])

    def test_prime_factors_type_error_float(self):
        """prime_factors should raise TypeError for float input."""
        with pytest.raises(TypeError, match="Expected integer"):
            prime_factors(12.5)

    def test_prime_factors_type_error_string(self):
        """prime_factors should raise TypeError for string input."""
        with pytest.raises(TypeError, match="Expected integer"):
            prime_factors("12")

    def test_prime_factors_type_error_none(self):
        """prime_factors should raise TypeError for None input."""
        with pytest.raises(TypeError, match="Expected integer"):
            prime_factors(None)

    def test_is_prime_accepts_bool(self):
        """is_prime should handle bool (subclass of int) gracefully."""
        # In Python, bool is a subclass of int: True=1, False=0
        assert is_prime(True) is False  # 1 is not prime
        assert is_prime(False) is False  # 0 is not prime

    def test_prime_factors_accepts_bool(self):
        """prime_factors should handle bool (subclass of int) gracefully."""
        assert prime_factors(True) == []  # 1 returns []
        assert prime_factors(False) == []  # 0 returns []

    def test_thread_safety_simulation(self):
        """Functions should be thread-safe (pure, no shared state)."""
        # Simple simulation: call functions multiple times in sequence
        # Real thread safety would require concurrent.futures, but this
        # verifies no hidden state corruption
        results = []
        for _ in range(100):
            results.append(is_prime(17))
            results.append(prime_factors(12))

        assert all(r is True for r in results[::2])  # All is_prime(17) are True
        assert all(r == [2, 2, 3] for r in results[1::2])  # All prime_factors(12) are [2,2,3]

    def test_memory_bounded_factorization(self):
        """prime_factors memory usage should be O(log n)."""
        # Largest factorization is for numbers with many small factors
        # 2^20 = 1048576 has 20 factors (all 2s)
        factors = prime_factors(2**20)
        assert len(factors) == 20
        assert all(f == 2 for f in factors)

        # Even large primes have O(1) output
        factors = prime_factors(1000003)
        assert len(factors) == 1


# ============================================================================
# REGRESSION TESTS
# ============================================================================


class TestRegression:
    """Regression tests for previously found bugs (none yet, but good practice)."""

    def test_boundary_at_million(self):
        """Test boundary between trial division and Miller-Rabin."""
        # 999983 is prime, uses trial division
        assert is_prime(999983) is True
        # 1000003 is prime, uses Miller-Rabin
        assert is_prime(1000003) is True
        # Verify composites at boundary too
        assert is_prime(999984) is False
        assert is_prime(1000002) is False

    def test_small_miller_rabin_witnesses(self):
        """Ensure Miller-Rabin handles cases where witness >= n."""
        # For small n >= 10^6, some witnesses will be >= n
        # This shouldn't cause issues (we skip them)
        assert is_prime(1000003) is True
