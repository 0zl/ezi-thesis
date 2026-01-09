import pandas as pd
from datetime import date
from dateutil.relativedelta import relativedelta
import os

# --- Konstanta ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "dataset")
STD_AGE_FILE = os.path.join(DATA_DIR, "std_age.csv")
STD_HEIGHT_FILE = os.path.join(DATA_DIR, "std_height.csv")


# --- Load Data ---
def load_data():
    try:
        df_age = pd.read_csv(STD_AGE_FILE)
        df_height = pd.read_csv(STD_HEIGHT_FILE)
        return df_age, df_height
    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Dataset files not found in {DATA_DIR}. Ensure std_age.csv and std_height.csv exist."
        ) from e


# Load data sekali aja di level modul biar gak bolak-balik baca file (I/O)
try:
    DF_AGE, DF_HEIGHT = load_data()
except FileNotFoundError:
    # Boleh import tanpa data buat testing kalo perlu, tapi kasih warning
    print(
        f"Warning: Data files not found in {DATA_DIR}. Functions depending on data will fail."
    )
    DF_AGE, DF_HEIGHT = None, None

# --- Logika Utama ---


def calculate_age_months(dob: date, visit_date: date = date.today()) -> int:
    """
    Hitung usia dalam bulan penuh.
    """
    delta = relativedelta(visit_date, dob)
    age_months = delta.years * 12 + delta.months
    return age_months


def correct_height(age_months: int, height: float, measure_mode: str) -> float:
    """
    Koreksi tinggi badan berdasarkan cara ukur dan usia (sesuai PMK No. 2 2020).
    measure_mode: 'recumbent' (terlentang) or 'standing' (berdiri)
    """
    corrected_height = height

    if measure_mode == "standing" and age_months < 24:
        # Usia < 24 bulan harusnya diukur terlentang. Kalo berdiri, tambah 0.7cm
        corrected_height += 0.7
    elif measure_mode == "recumbent" and age_months >= 24:
        # Usia >= 24 bulan harusnya diukur berdiri. Kalo terlentang, kurangi 0.7cm
        corrected_height -= 0.7

    return corrected_height


def _calculate_z(value: float, median: float, sd_neg1: float, sd_pos1: float) -> float:
    """
    Fungsi bantuan buat hitung Z-score individu pake rumus.
    """
    if value == median:
        return 0.0
    elif value < median:
        # Z = (Value - Median) / (Median - SD-1)
        divisor = median - sd_neg1
        if divisor == 0:
            return 0.0  # Amit-amit error pembagian nol
        return (value - median) / divisor
    else:  # value > median
        # Z = (Value - Median) / (SD+1 - Median)
        divisor = sd_pos1 - median
        if divisor == 0:
            return 0.0  # Amit-amit
        return (value - median) / divisor


def get_z_scores(
    gender: str,
    dob: date,
    weight: float,
    height: float,
    measure_mode: str,
    visit_date: date = date.today(),
) -> dict:
    """
    Hitung Z-score buat BB/U, TB/U (atau PB/U), dan BB/TB (atau BB/PB).

    Args:
        gender: 'L' atau 'P'
        dob: Tanggal lahir
        weight: Berat dalam kg
        height: Tinggi dalam cm
        measure_mode: 'recumbent' atau 'standing'
        visit_date: Tanggal kunjungan (default hari ini)

    Returns:
        Dictionary berisi Z-scores dan metadata:
        {
            'age_months': int,
            'corrected_height': float,
            'z_bb_u': float,
            'z_tb_u': float,
            'z_bb_tb': float
        }
    """
    if DF_AGE is None or DF_HEIGHT is None:
        raise RuntimeError("Reference data not loaded.")

    age_months = calculate_age_months(dob, visit_date)
    corrected_height = correct_height(age_months, height, measure_mode)

    # --- 1. BB/U (Berat-per-Umur) ---
    # Filter by gender, index_type='BB_U', dan umur
    # Catatan: umur di std_age.csv biasanya sampe 60 bulan buat balita, tapi di dataset cuman sampe 18-19 tahun.

    row_bb_u = DF_AGE[
        (DF_AGE["gender"] == gender)
        & (DF_AGE["index_type"] == "BB_U")
        & (DF_AGE["age_months"] == age_months)
    ]

    z_bb_u = None
    if not row_bb_u.empty:
        median = row_bb_u.iloc[0]["median"]
        sd_n1 = row_bb_u.iloc[0]["sd_n1"]
        sd_p1 = row_bb_u.iloc[0]["sd_p1"]
        z_bb_u = _calculate_z(weight, median, sd_n1, sd_p1)

    # --- 2. TB/U atau PB/U (Tinggi-per-Umur) ---
    # PB_U buat 0-24 bulan, TB_U buat 24+ bulan biasanya di standar.
    # Standarnya ganti nama index pas 24 bulan.
    # Cek struktur CSV dari `view_file` sebelumnya.
    # std_age.csv punya 'PB_U' (0-24) dan 'TB_U' (24-60+).

    index_type_len = "PB_U" if age_months < 24 else "TB_U"

    row_tb_u = DF_AGE[
        (DF_AGE["gender"] == gender)
        & (DF_AGE["index_type"] == index_type_len)
        & (DF_AGE["age_months"] == age_months)
    ]

    z_tb_u = None
    if not row_tb_u.empty:
        median = row_tb_u.iloc[0]["median"]
        sd_n1 = row_tb_u.iloc[0]["sd_n1"]
        sd_p1 = row_tb_u.iloc[0]["sd_p1"]
        # Kita pake tinggi yang udah dikoreksi buat asesmen umur
        # Sebenernya biasanya PB diukur buat <24, TB buat >=24.
        # Koreksinya itu buat standardisasi "panjang terukur" jadi "panjang" atau "tinggi terukur" jadi "tinggi".
        # Kalo kita punya corrected_height, kita pake itu aja biar engga ribet
        z_tb_u = _calculate_z(corrected_height, median, sd_n1, sd_p1)

    # --- 3. BB/TB atau BB/PB (Berat-per-Tinggi) ---
    # Ini pake std_height.csv
    # Kolomnya 'height_cm'. Kita mungkin perlu cari tinggi terdekat atau interpolasi.
    # Buat MVP/Simpelnya, kita buletin aja tinggi ke 0.5 atau 0.1 terdekat sesuai CSV.
    # Sampel std_height.csv: 45.0, 45.5, 46.0 ... (step 0.5)

    index_type_wfh = "BB_PB" if age_months < 24 else "BB_TB"

    # Dibulatkan ke 0.5 terdekat biar gampang lookup-nya
    # (Software medis beneran mungkin interpolasi, tapi 0.5 ok lah buat tool dasar) meong
    lookup_height = round(corrected_height * 2) / 2

    row_bb_tb = DF_HEIGHT[
        (DF_HEIGHT["gender"] == gender)
        & (DF_HEIGHT["index_type"] == index_type_wfh)
        & (DF_HEIGHT["height_cm"] == lookup_height)
    ]

    z_bb_tb = None
    if not row_bb_tb.empty:
        median = row_bb_tb.iloc[0]["median"]
        sd_n1 = row_bb_tb.iloc[0]["sd_n1"]
        sd_p1 = row_bb_tb.iloc[0]["sd_p1"]
        z_bb_tb = _calculate_z(weight, median, sd_n1, sd_p1)

    return {
        "age_months": age_months,
        "corrected_height": corrected_height,
        "z_bb_u": round(z_bb_u, 2) if z_bb_u is not None else None,
        "z_tb_u": round(z_tb_u, 2) if z_tb_u is not None else None,
        "z_bb_tb": round(z_bb_tb, 2) if z_bb_tb is not None else None,
    }


def get_growth_chart_data(gender: str):
    """
    Ambil data kurva pertumbuhan TB/U (Height-for-Age) standar WHO.
    Menggunakan PB_U untuk 0-24 bulan dan TB_U untuk 24-60 bulan.
    """
    if DF_AGE is None:
        return None

    # Filter data berdasarkan gender
    # Kita ambil range 0-60 bulan standard

    # 0-24 bulan pake PB_U
    df_0_24 = DF_AGE[
        (DF_AGE["gender"] == gender)
        & (DF_AGE["index_type"] == "PB_U")
        & (DF_AGE["age_months"] >= 0)
        & (DF_AGE["age_months"] < 24)
    ].sort_values("age_months")

    # 24-60 bulan pake TB_U
    df_24_60 = DF_AGE[
        (DF_AGE["gender"] == gender)
        & (DF_AGE["index_type"] == "TB_U")
        & (DF_AGE["age_months"] >= 24)
        & (DF_AGE["age_months"] <= 60)
    ].sort_values("age_months")

    # Gabung
    df_final = pd.concat([df_0_24, df_24_60])

    return {
        "age": df_final["age_months"].tolist(),
        "sd_n3": df_final["sd_n3"].tolist(),
        "sd_n2": df_final["sd_n2"].tolist(),
        "sd_n1": df_final["sd_n1"].tolist(),  # Optional
        "median": df_final["median"].tolist(),
        "sd_p1": df_final["sd_p1"].tolist(),  # Optional
        "sd_p2": df_final["sd_p2"].tolist(),
        "sd_p3": df_final["sd_p3"].tolist(),
    }


def get_weight_chart_data(gender: str):
    """
    Ambil data kurva pertumbuhan BB/U (Weight-for-Age) standar WHO.
    """
    if DF_AGE is None:
        return None

    # Filter data berdasarkan gender dan index BB_U
    # Range 0-60 bulan standard

    df_bb_u = DF_AGE[
        (DF_AGE["gender"] == gender)
        & (DF_AGE["index_type"] == "BB_U")
        & (DF_AGE["age_months"] >= 0)
        & (DF_AGE["age_months"] <= 60)
    ].sort_values("age_months")

    return {
        "age": df_bb_u["age_months"].tolist(),
        "sd_n3": df_bb_u["sd_n3"].tolist(),
        "sd_n2": df_bb_u["sd_n2"].tolist(),
        "median": df_bb_u["median"].tolist(),
        "sd_p2": df_bb_u["sd_p2"].tolist(),
        "sd_p3": df_bb_u["sd_p3"].tolist(),
    }


def get_wfh_chart_data(gender: str, mode: str):
    """
    Ambil data kurva pertumbuhan BB/PB atau BB/TB (Weight-for-Height/Length) standar WHO.
    mode: 'recumbent' (Terlentang) atau 'standing' (Berdiri)
    """
    if DF_HEIGHT is None:
        return None

    # Tentukan Index Type berdasarkan mode
    # Terlentang -> BB_PB (Weight for Length)
    # Berdiri -> BB_TB (Weight for Height)
    index_type = "BB_PB" if mode == "recumbent" else "BB_TB"

    df_wfh = DF_HEIGHT[
        (DF_HEIGHT["gender"] == gender) & (DF_HEIGHT["index_type"] == index_type)
    ].sort_values("height_cm")

    return {
        "height": df_wfh["height_cm"].tolist(),
        "sd_n3": df_wfh["sd_n3"].tolist(),
        "sd_n2": df_wfh["sd_n2"].tolist(),
        "median": df_wfh["median"].tolist(),
        "sd_p2": df_wfh["sd_p2"].tolist(),
        "sd_p3": df_wfh["sd_p3"].tolist(),
    }
