"""Dota 2 combat calculation functions.

This module provides pure functions for calculating physical damage multipliers,
effective HP, and DPS in Dota 2.
"""


def physical_damage_multiplier(armor: float) -> float:
    """Calculate the physical damage multiplier based on armor value.

    Uses the Dota 2 armor formula: 1 - (0.06*armor)/(1 + 0.06*abs(armor))

    Positive armor reduces incoming damage (multiplier < 1.0).
    Negative armor amplifies incoming damage (multiplier > 1.0).
    Zero armor results in no modification (multiplier = 1.0).

    Args:
        armor: The armor value. Can be positive, negative, or zero.

    Returns:
        The damage multiplier. Values < 1.0 indicate damage reduction,
        values > 1.0 indicate damage amplification, and 1.0 indicates
        no modification.

    Examples:
        >>> physical_damage_multiplier(0)
        1.0
        >>> physical_damage_multiplier(10)  # Positive armor reduces damage
        0.625
        >>> physical_damage_multiplier(-10)  # Negative armor amplifies damage
        1.6
    """
    return 1.0 - (0.06 * armor) / (1.0 + 0.06 * abs(armor))


def effective_hp_physical(hp: float, armor: float) -> float:
    """Calculate effective HP against physical damage given armor.

    Effective HP represents how much raw physical damage is needed to
    deplete the given HP pool when accounting for armor damage reduction
    or amplification.

    Args:
        hp: The base hit points value.
        armor: The armor value. Can be positive, negative, or zero.

    Returns:
        The effective HP against physical damage. Higher armor increases
        effective HP, while negative armor decreases it.

    Examples:
        >>> effective_hp_physical(1000, 0)
        1000.0
        >>> effective_hp_physical(1000, 10)
        1600.0
        >>> effective_hp_physical(1000, -10)
        625.0
    """
    return hp / physical_damage_multiplier(armor)


def dps(base_damage: float, attacks_per_second: float, target_armor: float) -> float:
    """Calculate damage per second against a target with given armor.

    Computes the effective DPS by multiplying base damage and attack rate,
    then applying the armor damage multiplier.

    Args:
        base_damage: The base damage per attack.
        attacks_per_second: The attack rate in attacks per second.
        target_armor: The target's armor value. Can be positive, negative, or zero.

    Returns:
        The effective damage per second after accounting for armor.

    Examples:
        >>> dps(100, 1.5, 0)
        150.0
        >>> dps(100, 1.5, 5)
        112.5
        >>> dps(100, 1.5, -5)
        195.0
    """
    return base_damage * attacks_per_second * physical_damage_multiplier(target_armor)
