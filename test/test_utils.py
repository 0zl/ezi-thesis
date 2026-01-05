
import unittest
from datetime import date
from utils import calculate_age_months, correct_height, get_z_scores, _calculate_z

class TestUtils(unittest.TestCase):
    
    def test_age_calculation(self):
        # Lahir 2020-01-01, Periksa 2020-02-01 -> 1 bulan
        self.assertEqual(calculate_age_months(date(2020, 1, 1), date(2020, 2, 1)), 1)
        # Lahir 2020-01-01, Periksa 2021-01-01 -> 12 bulan
        self.assertEqual(calculate_age_months(date(2020, 1, 1), date(2021, 1, 1)), 12)
        # Lahir 2020-01-01, Periksa 2020-01-15 -> 0 bulan
        self.assertEqual(calculate_age_months(date(2020, 1, 1), date(2020, 1, 15)), 0)

    def test_height_correction(self):
        # < 24 bulan, Berdiri -> +0.7
        self.assertEqual(correct_height(23, 80.0, 'standing'), 80.7)
        # < 24 bulan, Terlentang -> Tetap
        self.assertEqual(correct_height(23, 80.0, 'recumbent'), 80.0)
        # 24+ bulan, Terlentang -> -0.7
        self.assertEqual(correct_height(24, 90.0, 'recumbent'), 89.3)
        # 24+ bulan, Berdiri -> Tetap
        self.assertEqual(correct_height(24, 90.0, 'standing'), 90.0)

    def test_z_score_basic_logic(self):
        # Median=10, SD-1=9, SD+1=11
        # Value=10 -> Z=0
        self.assertEqual(_calculate_z(10, 10, 9, 11), 0.0)
        # Value=11 -> Z=1
        self.assertEqual(_calculate_z(11, 10, 9, 11), 1.0)
        # Value=9 -> Z=-1
        self.assertEqual(_calculate_z(9, 10, 9, 11), -1.0)
        # Value=12 -> Z=2 (12-10)/(11-10) = 2/1 = 2
        self.assertEqual(_calculate_z(12, 10, 9, 11), 2.0)
        
    def test_get_z_scores_integration(self):
        try:
            # Laki-laki, 0 bulan. Median BB_U buat bayi laki 0 bln itu 3.3
            # Input berat 3.3 -> Z harusnya 0.
            result = get_z_scores(
                gender='L',
                dob=date(2023, 1, 1), 
                weight=3.3, 
                height=50.0, 
                measure_mode='recumbent',
                visit_date=date(2023, 1, 1) # 0 months old
            )
            self.assertEqual(result['age_months'], 0)
            self.assertEqual(result['z_bb_u'], 0.0)
            
        except RuntimeError:
            self.skipTest("Reference data not loaded, skipping integration test.")

if __name__ == '__main__':
    unittest.main()
