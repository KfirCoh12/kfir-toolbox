import unittest

from src.catalogs import BREAKER_RATINGS_A
from src.circuit_selector import STANDARD_BREAKER_CANDIDATES_A


class CatalogTests(unittest.TestCase):
    def test_breaker_catalog_matches_forward_selector_candidates(self):
        self.assertEqual(BREAKER_RATINGS_A, STANDARD_BREAKER_CANDIDATES_A)

    def test_breaker_catalog_is_ordered_and_unique(self):
        self.assertEqual(BREAKER_RATINGS_A, tuple(sorted(set(BREAKER_RATINGS_A))))
        self.assertIn(63, BREAKER_RATINGS_A)
        self.assertNotIn(64, BREAKER_RATINGS_A)


if __name__ == "__main__":
    unittest.main()
