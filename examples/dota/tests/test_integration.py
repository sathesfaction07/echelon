"""Integration tests for dota_toolkit components."""

from dota_toolkit.combat import dps, effective_hp_physical, physical_damage_multiplier
from dota_toolkit.draft import recommend_pick, team_advantage
from dota_toolkit.winprob import WinProbEngine


class TestWinProbIntegration:
    """Integration tests for win probability with other components."""

    def test_full_draft_and_winprob_pipeline(self):
        """Test complete pipeline: draft heroes and compute win probability."""
        # Create 5x5 sample synergy matrix
        synergy_matrix = {
            ("Hero1", "Hero2"): 0.8,
            ("Hero1", "Hero3"): 0.6,
            ("Hero2", "Hero3"): 0.7,
            ("Hero1", "Hero4"): 0.5,
            ("Hero2", "Hero4"): 0.4,
            ("Hero3", "Hero4"): 0.6,
            ("Hero1", "Hero5"): 0.3,
            ("Hero2", "Hero5"): 0.5,
            ("Hero3", "Hero5"): 0.4,
            ("Hero4", "Hero5"): 0.7,
            ("Hero6", "Hero7"): 0.6,
            ("Hero6", "Hero8"): 0.5,
            ("Hero7", "Hero8"): 0.4,
            ("Hero6", "Hero9"): 0.7,
            ("Hero7", "Hero9"): 0.5,
            ("Hero8", "Hero9"): 0.6,
            ("Hero6", "Hero10"): 0.4,
            ("Hero7", "Hero10"): 0.3,
            ("Hero8", "Hero10"): 0.5,
            ("Hero9", "Hero10"): 0.6,
        }

        # Create 5x5 sample counter matrix
        counter_matrix = {
            ("Hero1", "Hero6"): 0.5,
            ("Hero1", "Hero7"): 0.3,
            ("Hero1", "Hero8"): 0.4,
            ("Hero1", "Hero9"): 0.2,
            ("Hero1", "Hero10"): 0.6,
            ("Hero2", "Hero6"): 0.4,
            ("Hero2", "Hero7"): 0.5,
            ("Hero2", "Hero8"): 0.3,
            ("Hero2", "Hero9"): 0.4,
            ("Hero2", "Hero10"): 0.2,
            ("Hero3", "Hero6"): 0.3,
            ("Hero3", "Hero7"): 0.4,
            ("Hero3", "Hero8"): 0.5,
            ("Hero3", "Hero9"): 0.3,
            ("Hero3", "Hero10"): 0.4,
            ("Hero4", "Hero6"): 0.6,
            ("Hero4", "Hero7"): 0.2,
            ("Hero4", "Hero8"): 0.4,
            ("Hero4", "Hero9"): 0.5,
            ("Hero4", "Hero10"): 0.3,
            ("Hero5", "Hero6"): 0.2,
            ("Hero5", "Hero7"): 0.6,
            ("Hero5", "Hero8"): 0.3,
            ("Hero5", "Hero9"): 0.4,
            ("Hero5", "Hero10"): 0.5,
        }

        # Draft a 5v5 lineup using recommend_pick
        my_team = []
        enemy_team = ["Hero6", "Hero7", "Hero8", "Hero9", "Hero10"]
        available_heroes = ["Hero1", "Hero2", "Hero3", "Hero4", "Hero5"]

        # Draft 5 heroes for my team
        for _ in range(5):
            pick = recommend_pick(
                available_heroes, my_team, enemy_team, synergy_matrix, counter_matrix
            )
            my_team.append(pick)
            available_heroes.remove(pick)

        # Verify we drafted 5 heroes
        assert len(my_team) == 5
        assert len(set(my_team)) == 5  # All unique

        # Compute draft advantage
        draft_adv = team_advantage(my_team, enemy_team, synergy_matrix, counter_matrix)

        # Create win probability engine
        engine = WinProbEngine(1.0, 0.001, 0.002)

        # Compute win probability with sample net_worth_diff and xp_diff
        result = engine.win_probability(draft_adv=0.2, net_worth_diff=1000, xp_diff=500)

        # Assert result is in valid range
        assert 0 < result < 1

        # Since we have positive advantages, probability should be > 0.5
        assert result > 0.5

    def test_winprob_with_combat_metrics(self):
        """Test win probability computation with combat mechanics."""
        # Use combat mechanics to compute some metrics
        armor = 10
        hp = 1000

        damage_mult = physical_damage_multiplier(armor)
        eff_hp = effective_hp_physical(hp, armor)
        damage_per_sec = dps(100, 1.5, armor)

        # Verify combat calculations work
        assert 0 < damage_mult < 1  # Positive armor reduces damage
        assert eff_hp > hp  # Effective HP is higher with positive armor
        assert damage_per_sec > 0

        # Create win probability engine
        engine = WinProbEngine(1.0, 0.0001, 0.0001)

        # Use effective HP difference as a proxy for advantage
        # (this is a simplified example)
        my_eff_hp = effective_hp_physical(1200, 15)
        enemy_eff_hp = effective_hp_physical(1000, 10)
        hp_advantage = my_eff_hp - enemy_eff_hp

        # Compute win probability
        result = engine.win_probability(draft_adv=0.1, net_worth_diff=hp_advantage, xp_diff=200)

        # Assert result is valid
        assert 0 < result < 1

    def test_winprob_with_negative_draft_advantage(self):
        """Test win probability when draft is disadvantageous."""
        synergy_matrix = {
            ("A", "B"): 0.2,
        }
        counter_matrix = {
            ("A", "C"): -0.5,  # Negative counter (enemy counters us)
            ("B", "C"): -0.3,
        }

        my_team = ["A", "B"]
        enemy_team = ["C"]

        draft_adv = team_advantage(my_team, enemy_team, synergy_matrix, counter_matrix)

        # Create engine
        engine = WinProbEngine(2.0, 0.001, 0.001)

        # With negative draft advantage and negative net worth/xp
        result = engine.win_probability(draft_adv=draft_adv, net_worth_diff=-500, xp_diff=-300)

        # Should still be in valid range
        assert 0 < result < 1

        # With negative advantages, probability should be < 0.5
        assert result < 0.5

    def test_imports_work_correctly(self):
        """Test that all required imports work correctly."""
        # This test verifies that the integration test can import all necessary modules
        from dota_toolkit.combat import dps, effective_hp_physical, physical_damage_multiplier
        from dota_toolkit.draft import recommend_pick, team_advantage
        from dota_toolkit.winprob import WinProbEngine

        # Verify we can instantiate and use each component
        assert callable(physical_damage_multiplier)
        assert callable(effective_hp_physical)
        assert callable(dps)
        assert callable(team_advantage)
        assert callable(recommend_pick)

        engine = WinProbEngine(1, 1, 1)
        assert engine is not None
        assert hasattr(engine, "win_probability")
