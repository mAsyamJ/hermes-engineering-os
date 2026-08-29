import unittest
from src.settings import timeout

class SettingsTests(unittest.TestCase):
    def test_timeout(self) -> None:
        self.assertEqual(timeout(), 30)
