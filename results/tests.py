import unittest
from .scoring import determine_grade, calculate_result_points

class ScoringEngineTests(unittest.TestCase):
    def test_grade_boundaries(self):
        # A+ (90 - 100)
        self.assertEqual(determine_grade(100), "A+")
        self.assertEqual(determine_grade(95), "A+")
        self.assertEqual(determine_grade(90), "A+")

        # A (70 - 89.99)
        self.assertEqual(determine_grade(89.99), "A")
        self.assertEqual(determine_grade(80), "A")
        self.assertEqual(determine_grade(70), "A")

        # B (60 - 69.99)
        self.assertEqual(determine_grade(69.99), "B")
        self.assertEqual(determine_grade(65), "B")
        self.assertEqual(determine_grade(60), "B")

        # C (50 - 59.99)
        self.assertEqual(determine_grade(59.99), "C")
        self.assertEqual(determine_grade(55), "C")
        self.assertEqual(determine_grade(50), "C")

        # Below 50 -> None
        self.assertIsNone(determine_grade(49.99))
        self.assertIsNone(determine_grade(30))
        self.assertIsNone(determine_grade(0))

    def test_single_program_points(self):
        # A+ (base 5) + prizes (5, 3, 1)
        self.assertEqual(calculate_result_points("A+", rank=1, program_type="single"), 10)
        self.assertEqual(calculate_result_points("A+", rank=2, program_type="single"), 8)
        self.assertEqual(calculate_result_points("A+", rank=3, program_type="single"), 6)
        self.assertEqual(calculate_result_points("A+", rank=4, program_type="single"), 5)

        # A (base 3) + prizes (5, 3, 1)
        self.assertEqual(calculate_result_points("A", rank=1, program_type="single"), 8)
        self.assertEqual(calculate_result_points("A", rank=2, program_type="single"), 6)
        self.assertEqual(calculate_result_points("A", rank=3, program_type="single"), 4)
        self.assertEqual(calculate_result_points("A", rank=5, program_type="single"), 3)

        # B (base 2) + prizes (5, 3, 1)
        self.assertEqual(calculate_result_points("B", rank=1, program_type="single"), 7)
        self.assertEqual(calculate_result_points("B", rank=2, program_type="single"), 5)
        self.assertEqual(calculate_result_points("B", rank=3, program_type="single"), 3)
        self.assertEqual(calculate_result_points("B", rank=4, program_type="single"), 2)

        # C (base 1) + prizes (5, 3, 1)
        self.assertEqual(calculate_result_points("C", rank=1, program_type="single"), 6)
        self.assertEqual(calculate_result_points("C", rank=2, program_type="single"), 4)
        self.assertEqual(calculate_result_points("C", rank=3, program_type="single"), 2)
        self.assertEqual(calculate_result_points("C", rank=4, program_type="single"), 1)

        # No grade -> 0 points even if rank 1
        self.assertEqual(calculate_result_points(None, rank=1, program_type="single"), 0)
        self.assertEqual(calculate_result_points("", rank=2, program_type="single"), 0)

    def test_group_program_points(self):
        # A+ (base 15) + prizes (5, 3, 1)
        self.assertEqual(calculate_result_points("A+", rank=1, program_type="group"), 20)
        self.assertEqual(calculate_result_points("A+", rank=2, program_type="group"), 18)
        self.assertEqual(calculate_result_points("A+", rank=3, program_type="group"), 16)
        self.assertEqual(calculate_result_points("A+", rank=4, program_type="group"), 15)

        # A (base 13) + prizes (5, 3, 1)
        self.assertEqual(calculate_result_points("A", rank=1, program_type="group"), 18)
        self.assertEqual(calculate_result_points("A", rank=2, program_type="group"), 16)
        self.assertEqual(calculate_result_points("A", rank=3, program_type="group"), 14)
        self.assertEqual(calculate_result_points("A", rank=5, program_type="group"), 13)

        # B (base 11) + prizes (5, 3, 1)
        self.assertEqual(calculate_result_points("B", rank=1, program_type="group"), 16)
        self.assertEqual(calculate_result_points("B", rank=2, program_type="group"), 14)
        self.assertEqual(calculate_result_points("B", rank=3, program_type="group"), 12)
        self.assertEqual(calculate_result_points("B", rank=4, program_type="group"), 11)

        # C (base 9) + prizes (5, 3, 1)
        self.assertEqual(calculate_result_points("C", rank=1, program_type="group"), 14)
        self.assertEqual(calculate_result_points("C", rank=2, program_type="group"), 12)
        self.assertEqual(calculate_result_points("C", rank=3, program_type="group"), 10)
        self.assertEqual(calculate_result_points("C", rank=4, program_type="group"), 9)

        # No grade -> 0 points even if rank 1
        self.assertEqual(calculate_result_points(None, rank=1, program_type="group"), 0)

    def test_custom_grade_rules(self):
        class MockRule:
            def __init__(self, grade_name, min_marks, points=0):
                self.grade_name = grade_name
                self.min_marks = min_marks
                self.points = points

        rules = [
            MockRule("Distinction", 85, points=25),
            MockRule("Merit", 70, points=15),
            MockRule("Pass", 50, points=5),
        ]

        # Grade determination with custom rules
        self.assertEqual(determine_grade(90, custom_grade_rules=rules), "Distinction")
        self.assertEqual(determine_grade(75, custom_grade_rules=rules), "Merit")
        self.assertEqual(determine_grade(55, custom_grade_rules=rules), "Pass")
        self.assertIsNone(determine_grade(40, custom_grade_rules=rules))

        # Points with custom rules + rank prizes
        self.assertEqual(calculate_result_points("Distinction", rank=1, custom_grade_rules=rules), 25 + 5)
        self.assertEqual(calculate_result_points("Merit", rank=2, custom_grade_rules=rules), 15 + 3)
        self.assertEqual(calculate_result_points("Pass", rank=3, custom_grade_rules=rules), 5 + 1)
        self.assertEqual(calculate_result_points("Pass", rank=4, custom_grade_rules=rules), 5 + 0)

