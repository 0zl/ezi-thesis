
import unittest
from fuzzy_logic import fuzzy_system

class TestFuzzyLogic(unittest.TestCase):

    def test_gizi_buruk_case(self):
        # Bb Sangat Kurang (-4) + Tb Sangat Pendek (-4) -> Harusnya Gizi Buruk
        score, label = fuzzy_system.predict(-4, -4)
        self.assertLessEqual(score, 25)
        self.assertEqual(label, "Gizi Buruk")

    def test_gizi_baik_case(self):
        # Berat Normal (0) + Tinggi Normal (0) -> Harusnya Gizi Baik (sekitar 51-80)
        score, label = fuzzy_system.predict(0, 0)
        self.assertTrue(50 <= score <= 80)
        self.assertEqual(label, "Gizi Baik")

    def test_gizi_lebih_case(self):
        # Kegemukan (+2) + Tinggi Normal (0) -> Harusnya Gizi Lebih
        # Aturan 15: risiko_lebih & normal -> gizi_lebih
        score, label = fuzzy_system.predict(3, 0)
        self.assertGreaterEqual(score, 80)
        self.assertEqual(label, "Gizi Lebih")

    def test_boundary_clamping(self):
        # Input > 5 harusnya di-clamp jadi 5
        score_1, _ = fuzzy_system.predict(10, 0)
        score_2, _ = fuzzy_system.predict(5, 0)
        self.assertEqual(score_1, score_2)

if __name__ == '__main__':
    unittest.main()
