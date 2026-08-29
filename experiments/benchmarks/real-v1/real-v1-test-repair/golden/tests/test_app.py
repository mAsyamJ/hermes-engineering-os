import unittest
from src.app import add

class AddTests(unittest.TestCase):
    def test_add(self) -> None:
        self.assertEqual(add(2, 2), 4)
