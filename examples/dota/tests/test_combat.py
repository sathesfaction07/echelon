"""Comprehensive unit tests for dota_toolkit.combat module."""

from dota_toolkit.combat import (
    dps,
    effective_hp_physical,
    physical_damage_multiplier,
)


class TestPhysicalDamageMultiplier:
    """Tests for physical_damage_multiplier function."""

    def test_zero_armor(self):
        """Test that zero armor results in no damage modification."""
        assert physical_damage_multiplier(0) == 1.0

    def test_positive_armor_reduces_damage(self):
        """Test that positive armor reduces damage (multiplier < 1.0)."""
        assert physical_damage_multiplier(10) < 1.0
        assert physical_damage_multiplier(5) < 1.0
        assert physical_damage_multiplier(20) < 1.0

    def test_negative_armor_amplifies_damage(self):
        """Test that negative armor amplifies damage (multiplier > 1.0)."""
        assert physical_damage_multiplier(-10) > 1.0
        assert physical_damage_multiplier(-5) > 1.0
        assert physical_damage_multiplier(-20) > 1.0

    def test_specific_positive_armor_values(self):
        """Test specific positive armor values against expected results."""
        # armor=10: 1 - (0.06*10)/(1 + 0.06*10) = 1 - 0.6/1.6 = 1 - 0.375 = 0.625
        assert abs(physical_damage_multiplier(10) - 0.625) < 1e-10

        # armor=5: 1 - (0.06*5)/(1 + 0.06*5) = 1 - 0.3/1.3 ≈ 0.769230769
        expected = 1.0 - (0.06 * 5) / (1.0 + 0.06 * 5)
        assert abs(physical_damage_multiplier(5) - expected) < 1e-10

    def test_specific_negative_armor_values(self):
        """Test specific negative armor values against expected results."""
        # armor=-10: 1 - (0.06*-10)/(1 + 0.06*10) = 1 - (-0.6)/1.6 = 1 + 0.375 = 1.375
        assert abs(physical_damage_multiplier(-10) - 1.375) < 1e-10

        # armor=-5: 1 - (0.06*-5)/(1 + 0.06*5) = 1 - (-0.3)/1.3 ≈ 1.230769231
        expected = 1.0 - (0.06 * -5) / (1.0 + 0.06 * 5)
        assert abs(physical_damage_multiplier(-5) - expected) < 1e-10

    def test_large_positive_armor(self):
        """Test large positive armor values."""
        # Should asymptotically approach 0 but never reach it
        result = physical_damage_multiplier(100)
        assert 0 < result < 1.0
        assert result < physical_damage_multiplier(50)

        # armor=100: 1 - (0.06*100)/(1 + 0.06*100) = 1 - 6/7 ≈ 0.142857
        expected = 1.0 - (0.06 * 100) / (1.0 + 0.06 * 100)
        assert abs(physical_damage_multiplier(100) - expected) < 1e-10

    def test_large_negative_armor(self):
        """Test large negative armor values."""
        # Should increase but with diminishing returns
        result = physical_damage_multiplier(-100)
        assert result > 1.0
        assert result > physical_damage_multiplier(-50)

        # armor=-100: 1 - (0.06*-100)/(1 + 0.06*100) = 1 + 6/7 ≈ 1.857143
        expected = 1.0 - (0.06 * -100) / (1.0 + 0.06 * 100)
        assert abs(physical_damage_multiplier(-100) - expected) < 1e-10

    def test_symmetry_property(self):
        """Test that positive and negative armor have symmetric effects."""
        # The formula should be symmetric around zero
        pos_reduction = 1.0 - physical_damage_multiplier(10)
        neg_amplification = physical_damage_multiplier(-10) - 1.0
        assert abs(pos_reduction - neg_amplification) < 1e-10

    def test_float_armor_values(self):
        """Test that function handles float armor values correctly."""
        result = physical_damage_multiplier(7.5)
        assert 0 < result < 1.0

        result = physical_damage_multiplier(-7.5)
        assert result > 1.0


class TestEffectiveHpPhysical:
    """Tests for effective_hp_physical function."""

    def test_zero_armor_no_change(self):
        """Test that zero armor results in effective HP equal to base HP."""
        assert effective_hp_physical(1000, 0) == 1000.0
        assert effective_hp_physical(500, 0) == 500.0

    def test_positive_armor_increases_ehp(self):
        """Test that positive armor increases effective HP."""
        assert effective_hp_physical(1000, 10) > 1000
        assert effective_hp_physical(1000, 5) > 1000
        assert effective_hp_physical(1000, 20) > 1000

    def test_negative_armor_decreases_ehp(self):
        """Test that negative armor decreases effective HP."""
        assert effective_hp_physical(1000, -10) < 1000
        assert effective_hp_physical(1000, -5) < 1000
        assert effective_hp_physical(1000, -20) < 1000

    def test_specific_ehp_calculation(self):
        """Test specific effective HP calculations."""
        # HP=1000, armor=10: multiplier=0.625, EHP=1000/0.625=1600
        assert abs(effective_hp_physical(1000, 10) - 1600.0) < 1e-10

        # HP=1000, armor=-10: multiplier=1.375, EHP=1000/1.375≈727.27
        expected = 1000.0 / 1.375
        assert abs(effective_hp_physical(1000, -10) - expected) < 1e-10

    def test_higher_armor_higher_ehp(self):
        """Test that higher armor results in higher effective HP."""
        ehp_5 = effective_hp_physical(1000, 5)
        ehp_10 = effective_hp_physical(1000, 10)
        ehp_20 = effective_hp_physical(1000, 20)

        assert ehp_5 < ehp_10 < ehp_20

    def test_lower_armor_lower_ehp(self):
        """Test that lower (more negative) armor results in lower effective HP."""
        ehp_neg5 = effective_hp_physical(1000, -5)
        ehp_neg10 = effective_hp_physical(1000, -10)
        ehp_neg20 = effective_hp_physical(1000, -20)

        assert ehp_neg20 < ehp_neg10 < ehp_neg5

    def test_various_hp_values(self):
        """Test with various HP values."""
        # The ratio should be consistent
        ratio_1000 = effective_hp_physical(1000, 10) / 1000
        ratio_500 = effective_hp_physical(500, 10) / 500
        assert abs(ratio_1000 - ratio_500) < 1e-10

    def test_float_hp_values(self):
        """Test that function handles float HP values correctly."""
        result = effective_hp_physical(1234.56, 7)
        assert result > 1234.56


class TestDps:
    """Tests for dps function."""

    def test_zero_armor_basic_calculation(self):
        """Test basic DPS calculation with zero armor."""
        # 100 damage * 1.5 attacks/sec * 1.0 multiplier = 150
        assert dps(100, 1.5, 0) == 150.0

        # 50 damage * 2.0 attacks/sec * 1.0 multiplier = 100
        assert dps(50, 2.0, 0) == 100.0

    def test_positive_armor_reduces_dps(self):
        """Test that positive armor reduces DPS."""
        dps_no_armor = dps(100, 1.5, 0)
        dps_with_armor = dps(100, 1.5, 10)

        assert dps_with_armor < dps_no_armor

    def test_negative_armor_increases_dps(self):
        """Test that negative armor increases DPS."""
        dps_no_armor = dps(100, 1.5, 0)
        dps_neg_armor = dps(100, 1.5, -10)

        assert dps_neg_armor > dps_no_armor

    def test_specific_dps_calculation(self):
        """Test specific DPS calculation as per acceptance criteria."""
        # base_damage=100, attacks_per_second=1.5, target_armor=5
        # multiplier for armor=5: 1 - (0.06*5)/(1 + 0.06*5) = 1 - 0.3/1.3
        multiplier = physical_damage_multiplier(5)
        expected = 100 * 1.5 * multiplier

        result = dps(100, 1.5, 5)
        assert abs(result - expected) < 1e-10

        # Verify the actual value
        # multiplier ≈ 0.769230769, so DPS ≈ 115.384615
        assert abs(result - 115.38461538461539) < 1e-10

    def test_dps_with_various_armor_values(self):
        """Test DPS with various armor values."""
        base = 100
        aps = 1.5

        dps_neg10 = dps(base, aps, -10)
        dps_0 = dps(base, aps, 0)
        dps_10 = dps(base, aps, 10)

        # More negative armor = higher DPS
        # More positive armor = lower DPS
        assert dps_neg10 > dps_0 > dps_10

    def test_dps_scales_with_damage(self):
        """Test that DPS scales linearly with base damage."""
        aps = 1.5
        armor = 5

        dps_100 = dps(100, aps, armor)
        dps_200 = dps(200, aps, armor)

        assert abs(dps_200 - 2 * dps_100) < 1e-10

    def test_dps_scales_with_attack_speed(self):
        """Test that DPS scales linearly with attack speed."""
        damage = 100
        armor = 5

        dps_1 = dps(damage, 1.0, armor)
        dps_2 = dps(damage, 2.0, armor)

        assert abs(dps_2 - 2 * dps_1) < 1e-10

    def test_dps_with_large_armor_values(self):
        """Test DPS with large armor values."""
        # Large positive armor
        result = dps(100, 1.5, 100)
        assert result > 0
        assert result < dps(100, 1.5, 0)

        # Large negative armor
        result = dps(100, 1.5, -100)
        assert result > dps(100, 1.5, 0)

    def test_dps_with_float_values(self):
        """Test DPS with float values for all parameters."""
        result = dps(123.45, 1.73, 7.8)
        assert result > 0

        # Verify calculation
        expected = 123.45 * 1.73 * physical_damage_multiplier(7.8)
        assert abs(result - expected) < 1e-10


class TestEdgeCases:
    """Tests for edge cases across all functions."""

    def test_very_small_armor_values(self):
        """Test with very small armor values."""
        assert abs(physical_damage_multiplier(0.001) - 1.0) < 0.01
        assert abs(physical_damage_multiplier(-0.001) - 1.0) < 0.01

    def test_extreme_armor_values(self):
        """Test with extreme armor values."""
        # Very large positive armor
        result = physical_damage_multiplier(1000)
        assert 0 < result < 1.0

        # Very large negative armor
        result = physical_damage_multiplier(-1000)
        assert result > 1.0

    def test_consistency_across_functions(self):
        """Test that functions are consistent with each other."""
        armor = 15
        hp = 1000
        base_dmg = 100
        aps = 1.5

        # EHP should be HP divided by damage multiplier
        multiplier = physical_damage_multiplier(armor)
        ehp = effective_hp_physical(hp, armor)
        assert abs(ehp - hp / multiplier) < 1e-10

        # DPS should be base_damage * aps * multiplier
        calculated_dps = dps(base_dmg, aps, armor)
        expected_dps = base_dmg * aps * multiplier
        assert abs(calculated_dps - expected_dps) < 1e-10

    def test_zero_damage_dps(self):
        """Test DPS with zero damage."""
        assert dps(0, 1.5, 10) == 0.0

    def test_zero_attack_speed_dps(self):
        """Test DPS with zero attack speed."""
        assert dps(100, 0, 10) == 0.0

    def test_zero_hp_ehp(self):
        """Test effective HP with zero HP."""
        assert effective_hp_physical(0, 10) == 0.0
