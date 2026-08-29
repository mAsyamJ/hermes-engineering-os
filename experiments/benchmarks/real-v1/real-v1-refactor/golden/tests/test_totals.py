import unittest
from src.totals import total

class TotalsTests(unittest.TestCase):
    def test_sum(self) -> None:
        self.assertEqual(total([1, 2, 3]), 6)
