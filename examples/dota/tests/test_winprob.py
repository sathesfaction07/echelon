"""Unit tests for win probability prediction component."""

from dota_toolkit.winprob import WinProbEngine


class TestWinProbEngine:
    """Test suite for WinProbEngine class."""

    def test_zero_inputs_returns_half(self):
        """Test that all zero inputs return exactly 0.5."""
        engine = WinProbEngine(1, 1, 1)
        result = engine.win_probability(0, 0, 0)
        assert result == 0.5

    def test_zero_inputs_different_coefficients(self):
        """Test zero inputs with different coefficients still return 0.5."""
        engine = WinProbEngine(2.5, -1.3, 0.7)
        result = engine.win_probability(0, 0, 0)
        assert result == 0.5

    def test_output_in_exclusive_range(self):
        """Test that output is always in (0, 1) exclusive for various inputs."""
        engine = WinProbEngine(1, 1, 1)

        test_cases = [
            (0.5, 100, 50),
            (-0.5, -100, -50),
            (1.0, 1000, 500),
            (-1.0, -1000, -500),
            (0.1, 0, 0),
            (0, 0.1, 0),
            (0, 0, 0.1),
        ]

        for draft_adv, net_worth_diff, xp_diff in test_cases:
            result = engine.win_probability(draft_adv, net_worth_diff, xp_diff)
            assert 0 < result < 1, f"Failed for inputs ({draft_adv}, {net_worth_diff}, {xp_diff})"

    def test_extreme_positive_values(self):
        """Test that extreme positive values are clamped properly."""
        engine = WinProbEngine(1, 1, 1)

        # Very large positive inputs should give probability close to 1 but not equal
        result = engine.win_probability(100, 10000, 5000)
        assert 0 < result < 1
        assert result > 0.99

    def test_extreme_negative_values(self):
        """Test that extreme negative values are clamped properly."""
        engine = WinProbEngine(1, 1, 1)

        # Very large negative inputs should give probability close to 0 but not equal
        result = engine.win_probability(-100, -10000, -5000)
        assert 0 < result < 1
        assert result < 0.01

    def test_monotonicity_draft_adv_positive_coefficient(self):
        """Test that win_probability increases with draft_adv when a > 0."""
        engine = WinProbEngine(1, 0, 0)

        # Hold other inputs constant, vary draft_adv
        prob1 = engine.win_probability(-1.0, 0, 0)
        prob2 = engine.win_probability(0.0, 0, 0)
        prob3 = engine.win_probability(1.0, 0, 0)

        assert prob1 < prob2 < prob3

    def test_monotonicity_net_worth_positive_coefficient(self):
        """Test that win_probability increases with net_worth_diff when b > 0."""
        engine = WinProbEngine(0, 1, 0)

        prob1 = engine.win_probability(0, -1000, 0)
        prob2 = engine.win_probability(0, 0, 0)
        prob3 = engine.win_probability(0, 1000, 0)

        assert prob1 < prob2 < prob3

    def test_monotonicity_xp_positive_coefficient(self):
        """Test that win_probability increases with xp_diff when c > 0."""
        engine = WinProbEngine(0, 0, 1)

        prob1 = engine.win_probability(0, 0, -500)
        prob2 = engine.win_probability(0, 0, 0)
        prob3 = engine.win_probability(0, 0, 500)

        assert prob1 < prob2 < prob3

    def test_symmetry_negative_coefficients(self):
        """Test symmetry with negative coefficients."""
        engine_pos = WinProbEngine(1, 1, 1)
        engine_neg = WinProbEngine(-1, -1, -1)

        # Positive inputs with positive coefficients
        prob_pos = engine_pos.win_probability(0.5, 100, 50)

        # Negative inputs with negative coefficients (should mirror)
        prob_neg = engine_neg.win_probability(-0.5, -100, -50)

        # Both should give same result due to symmetry
        assert abs(prob_pos - prob_neg) < 1e-10

    def test_negative_coefficient_reverses_monotonicity(self):
        """Test that negative coefficient reverses the monotonicity."""
        engine = WinProbEngine(-1, 0, 0)

        # With negative coefficient, increasing draft_adv should decrease probability
        prob1 = engine.win_probability(-1.0, 0, 0)
        prob2 = engine.win_probability(0.0, 0, 0)
        prob3 = engine.win_probability(1.0, 0, 0)

        assert prob1 > prob2 > prob3

    def test_coefficient_storage(self):
        """Test that coefficients are stored correctly."""
        engine = WinProbEngine(2.5, -1.3, 0.7)
        assert engine.a == 2.5
        assert engine.b == -1.3
        assert engine.c == 0.7

    def test_combined_features(self):
        """Test win probability with all features combined."""
        engine = WinProbEngine(1, 0.001, 0.002)

        # Positive advantage
        prob_advantage = engine.win_probability(0.5, 1000, 500)
        assert prob_advantage > 0.5

        # Negative advantage
        prob_disadvantage = engine.win_probability(-0.5, -1000, -500)
        assert prob_disadvantage < 0.5

    def test_zero_coefficients(self):
        """Test engine with all zero coefficients."""
        engine = WinProbEngine(0, 0, 0)

        # With zero coefficients, any input should give 0.5
        result = engine.win_probability(10, 1000, 500)
        assert result == 0.5

    def test_single_nonzero_coefficient(self):
        """Test engine with only one non-zero coefficient."""
        engine = WinProbEngine(2, 0, 0)

        prob1 = engine.win_probability(0.5, 999, 999)
        prob2 = engine.win_probability(0.5, 0, 0)

        # Should be equal since b and c are zero
        assert prob1 == prob2
