import unittest
from src.breaker import compare_breaker

class BreakerComparisonTests(unittest.TestCase):
    def test_ib_below_breaker_is_numerical_pass(self):
        r = compare_breaker(ib_a=155.2, in_a=200)
        self.assertEqual(r.comparison, "PASS")
        self.assertAlmostEqual(r.utilization, 0.776)
        self.assertAlmostEqual(r.headroom_a, 44.8)
        self.assertEqual(r.standards_status, "CALCULATED — NOT IEC VERIFIED")

    def test_equal_current_is_numerical_pass(self):
        r = compare_breaker(ib_a=100, in_a=100)
        self.assertEqual(r.comparison, "PASS")
        self.assertEqual(r.headroom_a, 0)

    def test_undersized_breaker_is_numerical_fail(self):
        r = compare_breaker(ib_a=105, in_a=100)
        self.assertEqual(r.comparison, "FAIL")
        self.assertGreater(r.utilization, 1)
        self.assertLess(r.headroom_a, 0)

    def test_invalid_values_rejected(self):
        for ib, inn in [(0, 100), (-1, 100), (100, 0), (100, -1)]:
            with self.subTest(ib=ib, inn=inn):
                with self.assertRaises(ValueError):
                    compare_breaker(ib_a=ib, in_a=inn)

if __name__ == "__main__": unittest.main()
