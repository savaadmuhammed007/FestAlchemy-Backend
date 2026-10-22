"""
Scoring and Grading engine for FestAlchemy.
Centralizes grade determinations, base point allocations, and rank-based prize bonuses.
"""

def determine_grade(scaled_percentage, custom_grade_rules=None):
    """
    Determine grade string based on scaled percentage (0-100).
    Default scale:
      - A+: 90% - 100%
      - A:  70% - 89.99%
      - B:  60% - 69.99%
      - C:  50% - 59.99%
      - None: Below 50%
    """
    if custom_grade_rules:
        # Rules should be ordered by -min_marks
        for rule in custom_grade_rules:
            if scaled_percentage >= rule.min_marks:
                return rule.grade_name

    if scaled_percentage >= 90:
        return "A+"
    elif scaled_percentage >= 70:
        return "A"
    elif scaled_percentage >= 60:
        return "B"
    elif scaled_percentage >= 50:
        return "C"
    return None


def calculate_result_points(grade_name, rank, program_type='single', custom_grade_rules=None):
    """
    Calculate points awarded for a result:
      Total Points = Base Grade Points + Position / Prize Bonus

    Base Points:
      Single programs:
        - A+: 5 pts
        - A:  3 pts
        - B:  2 pts
        - C:  1 pt
      Group programs:
        - A+: 15 pts
        - A:  13 pts
        - B:  11 pts
        - C:  9 pts

    Position / Prize Bonus (Only awarded if participant got an eligible grade):
      - 1st Prize (Rank 1): +5 pts
      - 2nd Prize (Rank 2): +3 pts
      - 3rd Prize (Rank 3): +1 pt
      - Other ranks:        +0 pts
    """
    if not grade_name:
        return 0

    # 1. Base Grade Points
    base_points = None
    if custom_grade_rules:
        for rule in custom_grade_rules:
            if rule.grade_name == grade_name and rule.points > 0:
                base_points = rule.points
                break

    if base_points is None:
        if str(program_type).lower() == 'group':
            grade_points_map = {
                'A+': 15,
                'A': 13,
                'B': 11,
                'C': 9,
            }
        else:  # single / individual
            grade_points_map = {
                'A+': 5,
                'A': 3,
                'B': 2,
                'C': 1,
            }
        base_points = grade_points_map.get(grade_name, 0)

    # 2. Position Prize Bonus (applied if participant achieved any grade)
    position_bonus = 0
    if rank == 1:
        position_bonus = 5
    elif rank == 2:
        position_bonus = 3
    elif rank == 3:
        position_bonus = 1

    return base_points + position_bonus
