"""Draft analysis component for Dota 2 hero selection."""


def team_advantage(
    my_team: list[str],
    enemy_team: list[str],
    synergy_matrix: dict[tuple[str, str], float],
    counter_matrix: dict[tuple[str, str], float],
) -> float:
    """
    Compute the total advantage of my_team vs enemy_team.

    The advantage is calculated as:
    - Sum of all pairwise synergies within my_team (unordered pairs)
    - Plus sum of all counter values for each (my_hero, enemy_hero) pair

    Args:
        my_team: List of hero names in my team
        enemy_team: List of hero names in enemy team
        synergy_matrix: Dict mapping (hero1, hero2) tuples to synergy values
        counter_matrix: Dict mapping (my_hero, enemy_hero) tuples to counter values

    Returns:
        Total advantage score as a float

    Note:
        - Synergy pairs are treated as unordered (('A','B') == ('B','A'))
        - Missing keys default to 0.0
    """
    total_advantage = 0.0

    # Sum pairwise synergies within my_team (unordered pairs)
    for i in range(len(my_team)):
        for j in range(i + 1, len(my_team)):
            hero1, hero2 = my_team[i], my_team[j]
            # Try both orderings since pairs are unordered
            synergy = synergy_matrix.get((hero1, hero2), 0.0)
            if synergy == 0.0:
                synergy = synergy_matrix.get((hero2, hero1), 0.0)
            total_advantage += synergy

    # Sum counter values for each (my_hero, enemy_hero) pair
    for my_hero in my_team:
        for enemy_hero in enemy_team:
            counter = counter_matrix.get((my_hero, enemy_hero), 0.0)
            total_advantage += counter

    return total_advantage


def recommend_pick(
    available: list[str],
    my_team: list[str],
    enemy_team: list[str],
    synergy_matrix: dict[tuple[str, str], float],
    counter_matrix: dict[tuple[str, str], float],
) -> str:
    """
    Recommend the best hero pick from available heroes.

    Returns the hero that maximizes the marginal advantage gain when added to my_team.

    Args:
        available: List of available hero names to choose from
        my_team: Current list of hero names in my team
        enemy_team: List of hero names in enemy team
        synergy_matrix: Dict mapping (hero1, hero2) tuples to synergy values
        counter_matrix: Dict mapping (my_hero, enemy_hero) tuples to counter values

    Returns:
        The hero name from available that provides the highest marginal advantage

    Raises:
        ValueError: If available list is empty
    """
    if not available:
        raise ValueError("Available heroes list cannot be empty")

    current_advantage = team_advantage(my_team, enemy_team, synergy_matrix, counter_matrix)

    best_hero = None
    best_gain = float("-inf")

    for hero in available:
        new_team = my_team + [hero]
        new_advantage = team_advantage(new_team, enemy_team, synergy_matrix, counter_matrix)
        marginal_gain = new_advantage - current_advantage

        if marginal_gain > best_gain:
            best_gain = marginal_gain
            best_hero = hero

    return best_hero
