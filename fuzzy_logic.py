import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


class MalnutritionFuzzySystem:
    def __init__(self):
        # --- Antecedents (Input) ---
        # 1. Status Berat Badan (Z-Score BB/U)
        self.bb_u = ctrl.Antecedent(np.arange(-5, 5.1, 0.1), "bb_u")

        # 2. Status Tinggi Badan (Z-Score TB/U)
        self.tb_u = ctrl.Antecedent(np.arange(-5, 5.1, 0.1), "tb_u")

        # 3. Status Berat-per-Tinggi (Z-Score BB/TB) [BARU]
        self.bb_tb = ctrl.Antecedent(np.arange(-5, 5.1, 0.1), "bb_tb")

        # --- Consequent (Output) ---
        # Skor Kesehatan Gizi (0-100)
        self.score = ctrl.Consequent(np.arange(0, 101, 1), "score")

        # --- Membership Functions ---

        # 1. BB/U (Indikator Umum)
        # Extend sangat_kurang to -2.9 to catch -3.0 boundary cases better
        self.bb_u["sangat_kurang"] = fuzz.trapmf(
            self.bb_u.universe, [-5, -5, -3.0, -2.8]
        )
        self.bb_u["kurang"] = fuzz.trimf(self.bb_u.universe, [-3.5, -2.5, -1.5])
        self.bb_u["normal"] = fuzz.trapmf(self.bb_u.universe, [-2.5, -1, 1, 2.5])
        self.bb_u["risiko_lebih"] = fuzz.trapmf(self.bb_u.universe, [1.5, 3, 5, 5])

        # 2. TB/U (Stunting - Kronis)
        self.tb_u["sangat_pendek"] = fuzz.trapmf(self.tb_u.universe, [-5, -5, -3.5, -3])
        self.tb_u["pendek"] = fuzz.trimf(self.tb_u.universe, [-3.5, -2.5, -1.5])
        self.tb_u["normal"] = fuzz.trapmf(self.tb_u.universe, [-2.5, -1, 2, 3.5])
        self.tb_u["tinggi"] = fuzz.trapmf(self.tb_u.universe, [2.5, 4, 5, 5])

        # 3. BB/TB (Wasting/Obesity - Akut)
        # Sangat Kurus (<-3), Kurus (-3 s.d -2), Normal (-2 s.d +2), Gemuk (>+2)
        # Kita simplifikasi jadi: Sangat Kurus, Kurus, Normal, Gemuk
        self.bb_tb["sangat_kurus"] = fuzz.trapmf(
            self.bb_tb.universe, [-5, -5, -3.5, -3]
        )
        self.bb_tb["kurus"] = fuzz.trimf(self.bb_tb.universe, [-3.5, -2.5, -1.5])
        self.bb_tb["normal"] = fuzz.trapmf(self.bb_tb.universe, [-2.5, -1, 1, 2.5])
        self.bb_tb["gemuk"] = fuzz.trapmf(self.bb_tb.universe, [1.5, 3, 5, 5])

        # Skor Output
        self.score["gizi_buruk"] = fuzz.trapmf(self.score.universe, [0, 0, 15, 25])
        self.score["gizi_kurang"] = fuzz.trimf(self.score.universe, [20, 35, 55])
        self.score["gizi_baik"] = fuzz.trimf(self.score.universe, [50, 65, 85])
        self.score["gizi_lebih"] = fuzz.trapmf(self.score.universe, [80, 90, 100, 100])

        # --- Rules ---
        # Prioritas:
        # 1. BB/TB Sangat Kurus / Kurus -> Gizi Buruk / Kurang (Acute is dangerous)
        # 2. BB/TB Gemuk -> Gizi Lebih
        # 3. BB/TB Normal tapi TB/U Pendek -> Gizi Kurang (Stunting)

        rules = []

        # -- Gizi Buruk / Kurang (Malnutrisi Akut/Wasting) --
        # Kalau BB/TB Sangat Kurus, pasti Gizi Buruk, apapun TB-nya
        rules.append(ctrl.Rule(self.bb_tb["sangat_kurus"], self.score["gizi_buruk"]))

        # Kalau BB/TB Kurus (-3 sd -2), cek BB/U
        # Jika BB/U Sangat Kurang (<-3 SD), ini double burden (Kurus + Sangat Ringan) -> Gizi Buruk
        rules.append(
            ctrl.Rule(
                self.bb_tb["kurus"] & self.bb_u["sangat_kurang"],
                self.score["gizi_buruk"],
            )
        )

        # Jika BB/TB Kurus DAN BB/U juga Kurang/Normal -> Gizi Kurang
        rules.append(
            ctrl.Rule(
                self.bb_tb["kurus"] & self.bb_u["kurang"], self.score["gizi_kurang"]
            )
        )
        rules.append(
            ctrl.Rule(
                self.bb_tb["kurus"] & self.bb_u["normal"], self.score["gizi_kurang"]
            )
        )

        # -- Gizi Lebih (Overweight) --
        # Kalau BB/TB Gemuk, pasti Gizi Lebih
        rules.append(ctrl.Rule(self.bb_tb["gemuk"], self.score["gizi_lebih"]))
        # Juga backup kalau BB/U berlebih
        rules.append(
            ctrl.Rule(
                self.bb_u["risiko_lebih"] & self.bb_tb["normal"],
                self.score["gizi_lebih"],
            )
        )

        # -- Kondisi Normal / Stunted (Kronis) --
        # BB/TB Normal... cek TB/U

        # 1. BB/TB Normal + TB/U Sangat Pendek (Stunting Parah) -> Masuk risiko tinggi -> Gizi Kurang/Buruk
        rules.append(
            ctrl.Rule(
                self.bb_tb["normal"] & self.tb_u["sangat_pendek"],
                self.score["gizi_buruk"],
            )
        )

        # 2. BB/TB Normal + TB/U Pendek (Stunted) -> Gizi Kurang
        rules.append(
            ctrl.Rule(
                self.bb_tb["normal"] & self.tb_u["pendek"], self.score["gizi_kurang"]
            )
        )

        # 3. BB/TB Normal + TB/U Normal -> Gizi Baik (Ideal)
        rules.append(
            ctrl.Rule(
                self.bb_tb["normal"] & self.tb_u["normal"] & self.bb_u["normal"],
                self.score["gizi_baik"],
            )
        )

        # 4. BB/TB Normal + TB/U Tinggi -> Gizi Baik (Tinggi)
        rules.append(
            ctrl.Rule(
                self.bb_tb["normal"] & self.tb_u["tinggi"], self.score["gizi_baik"]
            )
        )

        # Fallback aturan untuk kasus tepi (kombinasi tidak umum)
        # Misal BB/U Kurang tapi BB/TB Normal (berarti dia pendek juga/proporsional kecil)
        rules.append(
            ctrl.Rule(
                self.bb_u["kurang"] & self.bb_tb["normal"] & self.tb_u["normal"],
                self.score["gizi_kurang"],
            )
        )

        self.system = ctrl.ControlSystem(rules)
        self.simulation = ctrl.ControlSystemSimulation(self.system)

    def predict(self, bb_u_val, tb_u_val, bb_tb_val):
        """
        Jalankan inferensi fuzzy dengan 3 input.
        """
        # Batasi input
        bb_u_val = max(min(bb_u_val, 5), -5)
        tb_u_val = max(min(tb_u_val, 5), -5)
        bb_tb_val = max(min(bb_tb_val, 5), -5)

        self.simulation.input["bb_u"] = bb_u_val
        self.simulation.input["tb_u"] = tb_u_val
        self.simulation.input["bb_tb"] = bb_tb_val

        try:
            self.simulation.compute()
            score = self.simulation.output["score"]
        except:  # noqa: E722
            # Fallback kalo rule ga cover (harusnya cover semua sih)
            score = 50

        # Tentukan label dari skor crisp
        label = "Tidak Diketahui"
        if score <= 25:
            label = "Gizi Buruk"
        elif score <= 50:
            label = "Gizi Kurang"
        elif score <= 80:
            label = "Gizi Baik"
        else:
            label = "Gizi Lebih"

        # Override label manual buat kasus ekstrem biar ga aneh
        # Kalo BB/TB <-3 (Sangat Kurus), paksa Gizi Buruk
        if bb_tb_val <= -3:
            label = "Gizi Buruk (Sangat Kurus)"
        # Kalo BB/TB > 2 (Gemuk), paksa Gizi Lebih
        if bb_tb_val >= 2:
            label = "Gizi Lebih (Gemuk)"

        return round(score, 2), label


fuzzy_system = MalnutritionFuzzySystem()
