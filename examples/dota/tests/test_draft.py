"""Comprehensive unit tests for draft analysis component."""

import pytest
from dota_toolkit.draft import recommend_pick, team_advantage


class TestTeamAdvantage:
    """Test cases for team_advantage function."""

    def test_empty_matrices_returns_zero(self):
        """team_advantage with empty synergy_matrix and counter_matrix returns 0.0"""
        my_team = ["hero1", "hero2"]
        enemy_team = ["hero3", "hero4"]
        synergy_matrix = {}
        counter_matrix = {}

        result = team_advantage(my_team, enemy_team, synergy_matrix, counter_matrix)
        assert result == 0.0

    def test_two_hero_team_synergy_unordered(self):
        """team_advantage correctly sums synergies for a 2-hero team using unordered pair lookups"""
        my_team = ["hero1", "hero2"]
        enemy_team = []
        synergy_matrix = {("hero1", "hero2"): 5.0}
        counter_matrix = {}

        result = team_advantage(my_team, enemy_team, synergy_matrix, counter_matrix)
        assert result == 5.0

    def test_two_hero_team_synergy_reversed_order(self):
        """Test synergy lookup works with reversed tuple order"""
        my_team = ["hero1", "hero2"]
        enemy_team = []
        synergy_matrix = {("hero2", "hero1"): 5.0}
        counter_matrix = {}

        result = team_advantage(my_team, enemy_team, synergy_matrix, counter_matrix)
        assert result == 5.0

    def test_one_vs_one_counter(self):
        """team_advantage correctly sums counter values for a 1v1 matchup"""
        my_team = ["hero1"]
        enemy_team = ["hero2"]
        synergy_matrix = {}
        counter_matrix = {("hero1", "hero2"): 3.0}

        result = team_advantage(my_team, enemy_team, synergy_matrix, counter_matrix)
        assert result == 3.0

    def test_missing_keys_default_to_zero(self):
        """team_advantage handles missing keys in both matrices by defaulting to 0.0"""
        my_team = ["hero1", "hero2"]
        enemy_team = ["hero3"]
        synergy_matrix = {("hero1", "hero3"): 2.0}  # Different pair
        counter_matrix = {("hero3", "hero1"): 1.0}  # Wrong order

        result = team_advantage(my_team, enemy_team, synergy_matrix, counter_matrix)
        # No synergy between hero1-hero2, no counters for hero1->hero3 or hero2->hero3
        assert result == 0.0

    def test_empty_teams(self):
        """Test with empty teams"""
        result = team_advantage([], [], {}, {})
        assert result == 0.0

    def test_empty_my_team(self):
        """Test with empty my_team"""
        enemy_team = ["hero1", "hero2"]
        result = team_advantage([], enemy_team, {}, {})
        assert result == 0.0

    def test_empty_enemy_team(self):
        """Test with empty enemy_team (only synergies count)"""
        my_team = ["hero1", "hero2"]
        synergy_matrix = {("hero1", "hero2"): 4.0}
        result = team_advantage(my_team, [], synergy_matrix, {})
        assert result == 4.0

    def test_three_hero_team_multiple_synergies(self):
        """Test with 3 heroes (3 pairwise synergies)"""
        my_team = ["hero1", "hero2", "hero3"]
        enemy_team = []
        synergy_matrix = {("hero1", "hero2"): 2.0, ("hero1", "hero3"): 3.0, ("hero2", "hero3"): 1.5}
        counter_matrix = {}

        result = team_advantage(my_team, enemy_team, synergy_matrix, counter_matrix)
        assert result == 6.5  # 2.0 + 3.0 + 1.5

    def test_multiple_counters(self):
        """Test with multiple counter relationships"""
        my_team = ["hero1", "hero2"]
        enemy_team = ["hero3", "hero4"]
        synergy_matrix = {}
        counter_matrix = {
            ("hero1", "hero3"): 2.0,
            ("hero1", "hero4"): 1.0,
            ("hero2", "hero3"): -1.0,  # Negative counter (disadvantage)
            ("hero2", "hero4"): 0.5,
        }

        result = team_advantage(my_team, enemy_team, synergy_matrix, counter_matrix)
        assert result == 2.5  # 2.0 + 1.0 - 1.0 + 0.5

    def test_combined_synergy_and_counter(self):
        """Test with both synergies and counters"""
        my_team = ["hero1", "hero2"]
        enemy_team = ["hero3"]
        synergy_matrix = {("hero1", "hero2"): 5.0}
        counter_matrix = {("hero1", "hero3"): 2.0, ("hero2", "hero3"): 3.0}

        result = team_advantage(my_team, enemy_team, synergy_matrix, counter_matrix)
        assert result == 10.0  # 5.0 + 2.0 + 3.0

    def test_negative_values(self):
        """Test with negative synergy and counter values"""
        my_team = ["hero1", "hero2"]
        enemy_team = ["hero3"]
        synergy_matrix = {("hero1", "hero2"): -2.0}  # Bad synergy
        counter_matrix = {("hero1", "hero3"): -3.0}  # Countered by enemy

        result = team_advantage(my_team, enemy_team, synergy_matrix, counter_matrix)
        assert result == -5.0

    def test_single_hero_no_synergy(self):
        """Test with single hero (no synergies possible)"""
        my_team = ["hero1"]
        enemy_team = ["hero2"]
        synergy_matrix = {("hero1", "hero1"): 10.0}  # Self-synergy shouldn't count
        counter_matrix = {("hero1", "hero2"): 4.0}

        result = team_advantage(my_team, enemy_team, synergy_matrix, counter_matrix)
        assert result == 4.0  # Only counter, no synergy


class TestRecommendPick:
    """Test cases for recommend_pick function."""

    def test_recommend_best_marginal_gain(self):
        """recommend_pick returns the hero from available that provides the highest marginal advantage gain"""
        available = ["hero3", "hero4", "hero5"]
        my_team = ["hero1"]
        enemy_team = ["hero2"]
        synergy_matrix = {
            ("hero1", "hero3"): 2.0,
            ("hero1", "hero4"): 5.0,  # Best synergy
            ("hero1", "hero5"): 1.0,
        }
        counter_matrix = {
            ("hero3", "hero2"): 1.0,
            ("hero4", "hero2"): 2.0,  # Best counter
            ("hero5", "hero2"): 0.5,
        }

        result = recommend_pick(available, my_team, enemy_team, synergy_matrix, counter_matrix)
        # hero4 gives: 5.0 (synergy) + 2.0 (counter) = 7.0 marginal gain
        # hero3 gives: 2.0 + 1.0 = 3.0
        # hero5 gives: 1.0 + 0.5 = 1.5
        assert result == "hero4"

    def test_recommend_with_empty_team(self):
        """Test recommendation when my_team is empty"""
        available = ["hero1", "hero2"]
        my_team = []
        enemy_team = ["hero3"]
        synergy_matrix = {}
        counter_matrix = {("hero1", "hero3"): 5.0, ("hero2", "hero3"): 2.0}

        result = recommend_pick(available, my_team, enemy_team, synergy_matrix, counter_matrix)
        assert result == "hero1"

    def test_recommend_with_empty_enemy(self):
        """Test recommendation when enemy_team is empty (only synergies matter)"""
        available = ["hero2", "hero3"]
        my_team = ["hero1"]
        enemy_team = []
        synergy_matrix = {("hero1", "hero2"): 3.0, ("hero1", "hero3"): 7.0}
        counter_matrix = {}

        result = recommend_pick(available, my_team, enemy_team, synergy_matrix, counter_matrix)
        assert result == "hero3"

    def test_recommend_single_available(self):
        """Test with only one available hero"""
        available = ["hero2"]
        my_team = ["hero1"]
        enemy_team = []
        synergy_matrix = {}
        counter_matrix = {}

        result = recommend_pick(available, my_team, enemy_team, synergy_matrix, counter_matrix)
        assert result == "hero2"

    def test_recommend_empty_available_raises_error(self):
        """Test that empty available list raises ValueError"""
        available = []
        my_team = ["hero1"]
        enemy_team = ["hero2"]

        with pytest.raises(ValueError, match="Available heroes list cannot be empty"):
            recommend_pick(available, my_team, enemy_team, {}, {})

    def test_recommend_all_equal_gains(self):
        """Test when all heroes provide equal marginal gain"""
        available = ["hero2", "hero3", "hero4"]
        my_team = ["hero1"]
        enemy_team = []
        synergy_matrix = {("hero1", "hero2"): 5.0, ("hero1", "hero3"): 5.0, ("hero1", "hero4"): 5.0}
        counter_matrix = {}

        result = recommend_pick(available, my_team, enemy_team, synergy_matrix, counter_matrix)
        # Should return first one with max gain
        assert result in available

    def test_recommend_negative_gains(self):
        """Test when all available heroes have negative marginal gain"""
        available = ["hero2", "hero3"]
        my_team = ["hero1"]
        enemy_team = ["hero4"]
        synergy_matrix = {("hero1", "hero2"): -5.0, ("hero1", "hero3"): -10.0}
        counter_matrix = {}

        result = recommend_pick(available, my_team, enemy_team, synergy_matrix, counter_matrix)
        # Should pick the least bad option
        assert result == "hero2"  # -5.0 is better than -10.0

    def test_recommend_with_existing_team_synergies(self):
        """Test that existing team synergies don't affect marginal gain calculation"""
        available = ["hero3"]
        my_team = ["hero1", "hero2"]
        enemy_team = []
        synergy_matrix = {
            ("hero1", "hero2"): 100.0,  # Existing synergy, shouldn't affect choice
            ("hero1", "hero3"): 2.0,
            ("hero2", "hero3"): 3.0,
        }
        counter_matrix = {}

        result = recommend_pick(available, my_team, enemy_team, synergy_matrix, counter_matrix)
        # Marginal gain is 2.0 + 3.0 = 5.0 (existing 100.0 cancels out)
        assert result == "hero3"

    def test_recommend_complex_scenario(self):
        """Test complex scenario with multiple heroes and relationships"""
        available = ["hero4", "hero5"]
        my_team = ["hero1", "hero2"]
        enemy_team = ["hero6", "hero7"]
        synergy_matrix = {
            ("hero1", "hero2"): 10.0,
            ("hero1", "hero4"): 3.0,
            ("hero2", "hero4"): 2.0,
            ("hero1", "hero5"): 1.0,
            ("hero2", "hero5"): 1.0,
        }
        counter_matrix = {
            ("hero1", "hero6"): 1.0,
            ("hero2", "hero6"): 1.0,
            ("hero4", "hero6"): 2.0,
            ("hero4", "hero7"): 3.0,
            ("hero5", "hero6"): 0.5,
            ("hero5", "hero7"): 0.5,
        }

        result = recommend_pick(available, my_team, enemy_team, synergy_matrix, counter_matrix)
        # hero4: synergies (3.0 + 2.0) + counters (2.0 + 3.0) = 10.0
        # hero5: synergies (1.0 + 1.0) + counters (0.5 + 0.5) = 3.0
        assert result == "hero4"

    def test_recommend_zero_marginal_gain(self):
        """Test when a hero provides zero marginal gain"""
        available = ["hero2", "hero3"]
        my_team = ["hero1"]
        enemy_team = []
        synergy_matrix = {("hero1", "hero3"): 5.0}
        counter_matrix = {}

        result = recommend_pick(available, my_team, enemy_team, synergy_matrix, counter_matrix)
        # hero2: 0.0 gain, hero3: 5.0 gain
        assert result == "hero3"
