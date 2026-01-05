
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

class MalnutritionFuzzySystem:
    def __init__(self):
        # --- Antecedents (Input) ---
        # 1. Status Berat Badan (Z-Score BB/U)
        # Rentang: -5 sampai +5
        self.bb_u = ctrl.Antecedent(np.arange(-5, 5.1, 0.1), 'bb_u')
        
        # 2. Status Tinggi Badan (Z-Score TB/U)
        # Rentang: -5 sampai +5
        self.tb_u = ctrl.Antecedent(np.arange(-5, 5.1, 0.1), 'tb_u')

        # --- Consequent (Output) ---
        # Skor Kesehatan Gizi (0-100)
        self.score = ctrl.Consequent(np.arange(0, 101, 1), 'score')

        # --- Membership Functions ---
        
        # BB/U: Sangat Kurang (<-3), Kurang (-3 s.d -2), Normal (-2 s.d +1), Risiko Lebih (>+1)
        # Pakai kurva Trapesium dan Segitiga biar transisinya halus
        self.bb_u['sangat_kurang'] = fuzz.trapmf(self.bb_u.universe, [-5, -5, -3.5, -3])
        self.bb_u['kurang'] = fuzz.trimf(self.bb_u.universe, [-3.5, -2.5, -1.5]) # Dimodif dikit biar overlap-nya bagus
        self.bb_u['normal'] = fuzz.trapmf(self.bb_u.universe, [-2.5, -1, 0, 1.5])
        self.bb_u['risiko_lebih'] = fuzz.trapmf(self.bb_u.universe, [1, 2, 5, 5])

        # TB/U: Sangat Pendek (<-3), Pendek (-3 s.d -2), Normal (-2 s.d +3), Tinggi (>+3)
        self.tb_u['sangat_pendek'] = fuzz.trapmf(self.tb_u.universe, [-5, -5, -3.5, -3])
        self.tb_u['pendek'] = fuzz.trimf(self.tb_u.universe, [-3.5, -2.5, -1.5])
        self.tb_u['normal'] = fuzz.trapmf(self.tb_u.universe, [-2.5, -1, 2, 3.5])
        self.tb_u['tinggi'] = fuzz.trapmf(self.tb_u.universe, [3, 4, 5, 5])

        # Skor: Gizi Buruk (0-20), Gizi Kurang (21-50), Gizi Baik (51-80), Gizi Lebih (81-100)
        self.score['gizi_buruk'] = fuzz.trapmf(self.score.universe, [0, 0, 15, 25])
        self.score['gizi_kurang'] = fuzz.trimf(self.score.universe, [20, 35, 55])
        self.score['gizi_baik'] = fuzz.trimf(self.score.universe, [50, 65, 85])
        self.score['gizi_lebih'] = fuzz.trapmf(self.score.universe, [80, 90, 100, 100])

        # --- Rules ---
        # Matriks Inferensi Logika
        
        # 1. Logika Sangat Kurang (Severely Underweight)
        r1 = ctrl.Rule(self.bb_u['sangat_kurang'] & self.tb_u['sangat_pendek'], self.score['gizi_buruk'])
        r2 = ctrl.Rule(self.bb_u['sangat_kurang'] & self.tb_u['pendek'], self.score['gizi_buruk'])
        r3 = ctrl.Rule(self.bb_u['sangat_kurang'] & self.tb_u['normal'], self.score['gizi_buruk'])
        r4 = ctrl.Rule(self.bb_u['sangat_kurang'] & self.tb_u['tinggi'], self.score['gizi_kurang']) # Agak jarang terjadi, tapi berat rendah + tinggi banget itu tanda kurang gizi

        # 2. Logika Kurang (Underweight)
        r5 = ctrl.Rule(self.bb_u['kurang'] & self.tb_u['sangat_pendek'], self.score['gizi_buruk'])
        r6 = ctrl.Rule(self.bb_u['kurang'] & self.tb_u['pendek'], self.score['gizi_kurang'])
        r7 = ctrl.Rule(self.bb_u['kurang'] & self.tb_u['normal'], self.score['gizi_kurang'])
        r8 = ctrl.Rule(self.bb_u['kurang'] & self.tb_u['tinggi'], self.score['gizi_kurang'])

        # 3. Logika Berat Normal
        r9 = ctrl.Rule(self.bb_u['normal'] & self.tb_u['sangat_pendek'], self.score['gizi_kurang']) # Pendek (Stunted) tapi berat normal? Berarti agak gemuk untuk ukuran tingginya
        r10 = ctrl.Rule(self.bb_u['normal'] & self.tb_u['pendek'], self.score['gizi_baik'])
        r11 = ctrl.Rule(self.bb_u['normal'] & self.tb_u['normal'], self.score['gizi_baik'])
        r12 = ctrl.Rule(self.bb_u['normal'] & self.tb_u['tinggi'], self.score['gizi_baik'])

        # 4. Logika Gendut/Risiko Lebih (Overweight)
        r13 = ctrl.Rule(self.bb_u['risiko_lebih'] & self.tb_u['sangat_pendek'], self.score['gizi_lebih'])
        r14 = ctrl.Rule(self.bb_u['risiko_lebih'] & self.tb_u['pendek'], self.score['gizi_lebih'])
        r15 = ctrl.Rule(self.bb_u['risiko_lebih'] & self.tb_u['normal'], self.score['gizi_lebih'])
        r16 = ctrl.Rule(self.bb_u['risiko_lebih'] & self.tb_u['tinggi'], self.score['gizi_baik']) # Tinggi + Berat = Proporsional (Normal)

        self.system = ctrl.ControlSystem([r1, r2, r3, r4, r5, r6, r7, r8, r9, r10, r11, r12, r13, r14, r15, r16])
        self.simulation = ctrl.ControlSystemSimulation(self.system)

    def predict(self, bb_u_val, tb_u_val):
        """
        Jalankan inferensi fuzzy.
        Mengembalikan skor crisp (angka) dan label linguistik (kata-kata).
        """
        # Batasi input biar gak keluar dari range universe
        bb_u_val = max(min(bb_u_val, 5), -5)
        tb_u_val = max(min(tb_u_val, 5), -5)

        self.simulation.input['bb_u'] = bb_u_val
        self.simulation.input['tb_u'] = tb_u_val
        
        self.simulation.compute()
        
        score = self.simulation.output['score']
        
        # Tentukan label dari skor crisp
        label = "Tidak Diketahui"
        if score <= 20: 
            label = "Gizi Buruk"
        elif score <= 50: 
            label = "Gizi Kurang"
        elif score <= 80: 
            label = "Gizi Baik"
        else: 
            label = "Gizi Lebih"
        
        return round(score, 2), label

fuzzy_system = MalnutritionFuzzySystem()
