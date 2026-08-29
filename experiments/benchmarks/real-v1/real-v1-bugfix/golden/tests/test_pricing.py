import unittest
from src.pricing import discount

class PricingTests(unittest.TestCase):
    def test_ten_percent(self) -> None:
        self.assertEqual(discount(100, 10), 90)
