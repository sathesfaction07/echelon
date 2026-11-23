"""Win probability prediction component for Dota 2.

This module provides a logistic regression-based win probability engine
that combines draft advantage, net worth difference, and experience difference
to predict match outcomes.
"""

import math


class WinProbEngine:
    """Engine for computing win probability based on game state features.

    Uses a logistic regression model: P(win) = 1 / (1 + exp(-(a*draft_adv + b*net_worth_diff + c*xp_diff)))

    Attributes:
        a: Coefficient for draft advantage
        b: Coefficient for net worth difference
        c: Coefficient for experience difference
    """

    def __init__(self, a: float, b: float, c: float):
        """Initialize the win probability engine with coefficients.

        Args:
            a: Coefficient for draft advantage
            b: Coefficient for net worth difference
            c: Coefficient for experience difference
        """
        self.a = a
        self.b = b
        self.c = c

    def win_probability(self, draft_adv: float, net_worth_diff: float, xp_diff: float) -> float:
        """Calculate win probability based on game state features.

        Uses logistic regression to combine multiple features into a probability.
        Special case: when all inputs are 0, returns exactly 0.5.
        Output is clamped to (0, 1) exclusive to avoid numerical edge cases.

        Args:
            draft_adv: Draft advantage score
            net_worth_diff: Net worth difference between teams
            xp_diff: Experience difference between teams

        Returns:
            Win probability in the range (0, 1) exclusive

        Examples:
            >>> engine = WinProbEngine(1, 1, 1)
            >>> engine.win_probability(0, 0, 0)
            0.5
            >>> prob = engine.win_probability(0.2, 1000, 500)
            >>> 0 < prob < 1
            True
        """
        # Special case: all inputs zero returns exactly 0.5
        if draft_adv == 0 and net_worth_diff == 0 and xp_diff == 0:
            return 0.5

        # Compute linear combination
        z = self.a * draft_adv + self.b * net_worth_diff + self.c * xp_diff

        # Apply logistic function: 1 / (1 + exp(-z))
        # Handle overflow by clamping z to avoid exp overflow
        # exp(x) overflows for x > ~709, so exp(-z) overflows for z < -709
        if z > 709:
            # exp(-z) approaches 0, so result approaches 1
            result = 1.0 - 1e-15
        elif z < -709:
            # exp(-z) approaches infinity, so result approaches 0
            result = 1e-15
        else:
            result = 1.0 / (1.0 + math.exp(-z))
            # Clamp to (0, 1) exclusive
            result = max(1e-15, min(1 - 1e-15, result))

        return result
