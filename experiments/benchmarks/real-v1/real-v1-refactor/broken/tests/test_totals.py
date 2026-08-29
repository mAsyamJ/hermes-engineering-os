import unittest
from src.left import total as left_total
from src.right import total as right_total

class TotalsTests(unittest.TestCase):
    def test_same(self) -> None:
        self.assertEqual(left_total([1, 2, 3]), 6)
        self.assertEqual(right_total([1, 2, 3]), 6)
