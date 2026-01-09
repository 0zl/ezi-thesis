import gradio as gr
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import plotly.graph_objects as go
import utils
from fuzzy_logic import fuzzy_system


def analyze_gizi(nama, dob_str, gender, weight, height, measure_mode):
    try:
        if dob_str is None:
            return "Mohon masukkan tanggal lahir.", "Error", "", None

        dob = dob_str.date() if isinstance(dob_str, datetime) else dob_str

        gender_code = "L" if gender == "Laki-laki" else "P"
        mode_code = "standing" if measure_mode == "Berdiri" else "recumbent"

        if height > 200 or height < 10:
            return (
                None,
                None,
                None,
                "Tinggi badan tidak valid (Range: 10cm - 200cm).",
                "Input Error",
                None,
            )

        if weight > 100 or weight < 1:
            return (
                None,
                None,
                None,
                "Berat badan tidak valid (Range: 1kg - 100kg).",
                "Input Error",
                None,
            )

        # 1. Hitung-hitungan Backend atau apalah itu, keong
        z_results = utils.get_z_scores(gender_code, dob, weight, height, mode_code)

        age_months = z_results["age_months"]
        z_bb_u = z_results["z_bb_u"]
        z_tb_u = z_results["z_tb_u"]
        z_bb_tb = z_results["z_bb_tb"]
        corrected_height = z_results["corrected_height"]

        # 2. Inferensi Fuzzy
        if z_bb_u is None or z_tb_u is None:
            return (
                age_months,
                corrected_height,
                None,
                "Data diluar jangkauan standar.",
                "Tidak Dapat Dianalisa",
                None,
            )

        fuzzy_score, fuzzy_label = fuzzy_system.predict(z_bb_u, z_tb_u)

        # 3. Logika Rekomendasi
        rekomendasi = ""
        if fuzzy_label == "Gizi Buruk":
            rekomendasi = "SEGERA RUJUK KE PUSKESMAS/RS. Perlu penanganan medis segera."
        elif fuzzy_label == "Gizi Kurang":
            rekomendasi = "Perlu Pemberian Makanan Tambahan (PMT) pemulihan dan konseling gizi rutin."
        elif fuzzy_label == "Gizi Baik":
            rekomendasi = "Pertahankan pola asuh dan pola makan yang baik. Pantau pertumbuhan diposyandu setiap bulan."
        elif fuzzy_label == "Gizi Lebih":
            rekomendasi = "Konsultasikan diet seimbang. Kurangi makanan manis/berlemak, tingkatkan aktivitas fisik."

        z_score_data = [
            ["BB/U (Berat/Umur)", z_bb_u, "Indikator Berat Badan"],
            ["TB/U (Tinggi/Umur)", z_tb_u, "Indikator Stunting"],
            ["BB/TB (Berat/Tinggi)", z_bb_tb, "Indikator Wasting"],
        ]

        status_output = f"{fuzzy_label} ({fuzzy_score}/100)"

        # 5. Visualisasi (Pake Plotly)
        # 5. Visualisasi Growth Chart (Height-for-Age) standard WHO
        chart_data_tb = utils.get_growth_chart_data(gender_code)

        fig = go.Figure()

        if chart_data_tb:
            # Plot Kurva Standar
            # SD -3 (Merah)
            fig.add_trace(
                go.Scatter(
                    x=chart_data_tb["age"],
                    y=chart_data_tb["sd_n3"],
                    mode="lines",
                    line=dict(color="red", width=1),
                    name="-3 SD",
                )
            )
            # SD -2 (Orange)
            fig.add_trace(
                go.Scatter(
                    x=chart_data_tb["age"],
                    y=chart_data_tb["sd_n2"],
                    mode="lines",
                    line=dict(color="orange", width=1),
                    name="-2 SD",
                )
            )
            # SD 0 (Hijau / Median)
            fig.add_trace(
                go.Scatter(
                    x=chart_data_tb["age"],
                    y=chart_data_tb["median"],
                    mode="lines",
                    line=dict(color="green", width=2),
                    name="0 SD (Median)",
                )
            )
            # SD +2 (Orange)
            fig.add_trace(
                go.Scatter(
                    x=chart_data_tb["age"],
                    y=chart_data_tb["sd_p2"],
                    mode="lines",
                    line=dict(color="orange", width=1),
                    name="+2 SD",
                )
            )
            # SD +3 (Merah)
            fig.add_trace(
                go.Scatter(
                    x=chart_data_tb["age"],
                    y=chart_data_tb["sd_p3"],
                    mode="lines",
                    line=dict(color="red", width=1),
                    name="+3 SD",
                )
            )

        # Plot Posisi Anak Saat Ini (TB)
        fig.add_trace(
            go.Scatter(
                x=[age_months],
                y=[corrected_height],
                mode="markers+text",
                text=[nama],
                textposition="top center",
                marker=dict(
                    size=12,
                    color="blue",
                    symbol="circle",
                    line=dict(width=2, color="white"),
                ),
                name="Posisi Anak",
            )
        )

        fig.update_layout(
            # title=f"Grafik Pertumbuhan TB/U (Standard WHO) - {gender}",
            xaxis_title="Umur (Bulan)",
            yaxis_title="Tinggi Badan (cm)",
            xaxis=dict(range=[0, 60], zeroline=False),  # Balita 0-5 tahun
            yaxis=dict(zeroline=False),
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            height=500,
            margin=dict(l=40, r=20, t=60, b=40),
        )

        # 6. Visualisasi Weight Chart (Weight-for-Age) standard WHO
        chart_data_bb = utils.get_weight_chart_data(gender_code)
        fig2 = go.Figure()

        if chart_data_bb:
            fig2.add_trace(
                go.Scatter(
                    x=chart_data_bb["age"],
                    y=chart_data_bb["sd_n3"],
                    mode="lines",
                    line=dict(color="red", width=1),
                    name="-3 SD",
                )
            )
            fig2.add_trace(
                go.Scatter(
                    x=chart_data_bb["age"],
                    y=chart_data_bb["sd_n2"],
                    mode="lines",
                    line=dict(color="orange", width=1),
                    name="-2 SD",
                )
            )
            fig2.add_trace(
                go.Scatter(
                    x=chart_data_bb["age"],
                    y=chart_data_bb["median"],
                    mode="lines",
                    line=dict(color="green", width=2),
                    name="0 SD (Median)",
                )
            )
            fig2.add_trace(
                go.Scatter(
                    x=chart_data_bb["age"],
                    y=chart_data_bb["sd_p2"],
                    mode="lines",
                    line=dict(color="orange", width=1),
                    name="+2 SD",
                )
            )
            fig2.add_trace(
                go.Scatter(
                    x=chart_data_bb["age"],
                    y=chart_data_bb["sd_p3"],
                    mode="lines",
                    line=dict(color="red", width=1),
                    name="+3 SD",
                )
            )

        # Plot Posisi Anak Saat Ini (BB)
        fig2.add_trace(
            go.Scatter(
                x=[age_months],
                y=[weight],
                mode="markers+text",
                text=[nama],
                textposition="top center",
                marker=dict(
                    size=12,
                    color="purple",
                    symbol="diamond",
                    line=dict(width=2, color="white"),
                ),
                name="Posisi Anak",
            )
        )

        fig2.update_layout(
            # title=f"Grafik Pertumbuhan BB/U (Standard WHO) - {gender}",
            xaxis_title="Umur (Bulan)",
            yaxis_title="Berat Badan (kg)",
            xaxis=dict(range=[0, 60], zeroline=False),
            yaxis=dict(zeroline=False),
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            height=500,
            margin=dict(l=40, r=20, t=60, b=40),
        )

        # 7. Visualisasi Weight-for-Length/Height (BB/TB atau BB/PB)
        chart_data_wfh = utils.get_wfh_chart_data(gender_code, mode_code)
        fig3 = go.Figure()

        wfh_title = "BB/TB" if mode_code == "standing" else "BB/PB"
        x_label = (
            "Tinggi Badan (cm)" if mode_code == "standing" else "Panjang Badan (cm)"
        )

        if chart_data_wfh:
            fig3.add_trace(
                go.Scatter(
                    x=chart_data_wfh["height"],
                    y=chart_data_wfh["sd_n3"],
                    mode="lines",
                    line=dict(color="red", width=1),
                    name="-3 SD",
                )
            )
            fig3.add_trace(
                go.Scatter(
                    x=chart_data_wfh["height"],
                    y=chart_data_wfh["sd_n2"],
                    mode="lines",
                    line=dict(color="orange", width=1),
                    name="-2 SD",
                )
            )
            fig3.add_trace(
                go.Scatter(
                    x=chart_data_wfh["height"],
                    y=chart_data_wfh["median"],
                    mode="lines",
                    line=dict(color="green", width=2),
                    name="0 SD (Median)",
                )
            )
            fig3.add_trace(
                go.Scatter(
                    x=chart_data_wfh["height"],
                    y=chart_data_wfh["sd_p2"],
                    mode="lines",
                    line=dict(color="orange", width=1),
                    name="+2 SD",
                )
            )
            fig3.add_trace(
                go.Scatter(
                    x=chart_data_wfh["height"],
                    y=chart_data_wfh["sd_p3"],
                    mode="lines",
                    line=dict(color="red", width=1),
                    name="+3 SD",
                )
            )

        # Plot Posisi Anak Saat Ini (BB vs TB)
        fig3.add_trace(
            go.Scatter(
                x=[corrected_height],
                y=[weight],
                mode="markers+text",
                text=[nama],
                textposition="top center",
                marker=dict(
                    size=12,
                    color="magenta",
                    symbol="star",
                    line=dict(width=2, color="white"),
                ),
                name="Posisi Anak",
            )
        )

        fig3.update_layout(
            # title=f"Grafik Pertumbuhan {wfh_title} (Standard WHO) - {gender}",
            xaxis_title=x_label,
            yaxis_title="Berat Badan (kg)",
            # Range X axis menyesuaikan data tapi kita bisa set auto dulu atau range spesifik
            # BB/PB ~45-110, BB/TB ~65-120
            yaxis=dict(zeroline=False),
            showlegend=True,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            height=500,
            margin=dict(l=40, r=20, t=60, b=40),
        )

        return (
            age_months,
            corrected_height,
            z_score_data,
            status_output,
            rekomendasi,
            fig,
            fig2,
            fig3,
        )

    except Exception as e:
        return None, None, None, f"Error: {str(e)}", "Error", None


def simpan_data(nama, dob, gender, weight, height, status, recommendation):
    # Placeholder buat simpen ke database
    if not nama:
        return "Data kosong, tidak dapat disimpan."
    return f"Data balita '{nama}' berhasil disimpan! (Placeholder)"


# --- Layout UI ---

with gr.Blocks(title="Sistem Pakar Gizi Posyandu") as demo:
    gr.Markdown("## Dashboard Posyandu - Sistem Pakar Gizi Posyandu")

    with gr.Tabs():
        with gr.TabItem("📋 Pemeriksaan Gizi"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📝 Input Data")
                    with gr.Group():
                        inp_nama = gr.Textbox(
                            label="Nama Balita", placeholder="Masukkan nama lengkap"
                        )
                        inp_dob = gr.DateTime(
                            label="Tanggal Lahir", type="datetime", include_time=False
                        )
                        inp_gender = gr.Radio(
                            ["Laki-laki", "Perempuan"],
                            label="Jenis Kelamin",
                            value="Laki-laki",
                        )

                        with gr.Row():
                            inp_weight = gr.Number(
                                label="Berat Badan (kg)", precision=2
                            )
                            inp_height = gr.Number(
                                label="Tinggi Badan (cm)", precision=1
                            )

                        inp_mode = gr.Radio(
                            ["Terlentang", "Berdiri"],
                            label="Posisi Pengukuran",
                            value="Terlentang",
                        )

                    btn_analyze = gr.Button(
                        "🔍 Analisa Status Gizi", variant="primary", size="lg"
                    )

                    today_date = date.today()
                    # Bikin contoh buat balita umur 24 bulan (2 tahun)
                    dob_2yo = (today_date - relativedelta(years=2)).strftime("%Y-%m-%d")

                    gr.Examples(
                        examples=[
                            [
                                "Budi (Sehat)",
                                dob_2yo,
                                "Laki-laki",
                                12.2,
                                87.1,
                                "Berdiri",
                            ],
                            [
                                "Asep (Gizi Buruk)",
                                dob_2yo,
                                "Laki-laki",
                                8.0,
                                75.0,
                                "Berdiri",
                            ],
                            [
                                "Putri (Gizi Lebih)",
                                dob_2yo,
                                "Perempuan",
                                18.0,
                                87.1,
                                "Berdiri",
                            ],
                        ],
                        inputs=[
                            inp_nama,
                            inp_dob,
                            inp_gender,
                            inp_weight,
                            inp_height,
                            inp_mode,
                        ],
                        label="Contoh Kasus (Klik untuk isi otomatis)",
                    )

                with gr.Column(scale=2):
                    gr.Markdown("### 📊 Hasil Analisa Ekspert")

                    with gr.Row():
                        out_age = gr.Number(label="Usia (Bulan)", interactive=False)
                        out_corr_height = gr.Number(
                            label="Tinggi Terkoreksi (cm)", interactive=False
                        )

                    with gr.Row():
                        out_status = gr.Label(
                            label="Keputusan Sistem (Fuzzy Score)", num_top_classes=1
                        )

                    with gr.Row():
                        out_z_table = gr.Dataframe(
                            headers=["Indeks", "Nilai (SD)", "Keterangan"],
                            datatype=["str", "number", "str"],
                            label="Rincian Z-Score (Standar WHO/Kemenkes)",
                            interactive=False,
                        )

                    out_rekomendasi = gr.Textbox(
                        label="Rekomendasi Penanganan", lines=2, interactive=False
                    )

                    with gr.Tabs():
                        with gr.TabItem("📏 Tinggi/Umur (TB/U)"):
                            out_plot_tb = gr.Plot(label="Kurva Pertumbuhan TB/U")
                        with gr.TabItem("⚖️ Berat/Umur (BB/U)"):
                            out_plot_bb = gr.Plot(label="Kurva Pertumbuhan BB/U")
                        with gr.TabItem("📐 Berat/Tinggi (BB/TB)"):
                            out_plot_wfh = gr.Plot(label="Kurva Pertumbuhan BB/TB")

                    with gr.Row():
                        btn_save = gr.Button(
                            "💾 Simpan Data Ke Database", variant="secondary"
                        )
                        out_save_msg = gr.Textbox(
                            label="Status Penyimpanan", visible=False
                        )

        with gr.TabItem("📂 Riwayat Data"):
            gr.Markdown("### 📂 Database Balita (Placeholder)")
            gr.Markdown("_WEWLEWLE Data bakal dari MySQL/SQLite._")
            gr.Dataframe(
                headers=["ID", "Nama", "Tanggal Periksa", "Status Gizi"],
                value=[["1", "Contoh Balita", "2024-01-05", "Gizi Baik"]],
                interactive=False,
            )

    btn_analyze.click(
        fn=analyze_gizi,
        inputs=[inp_nama, inp_dob, inp_gender, inp_weight, inp_height, inp_mode],
        outputs=[
            out_age,
            out_corr_height,
            out_z_table,
            out_status,
            out_rekomendasi,
            out_plot_tb,
            out_plot_bb,
            out_plot_wfh,
        ],
    )

    btn_save.click(
        fn=simpan_data,
        inputs=[
            inp_nama,
            inp_dob,
            inp_gender,
            inp_weight,
            inp_height,
            out_status,
            out_rekomendasi,
        ],
        outputs=[out_save_msg],
    ).then(
        fn=lambda x: gr.update(visible=True, value=x),
        inputs=[out_save_msg],
        outputs=[out_save_msg],
    )

if __name__ == "__main__":
    import os
    import argparse

    share_link = False
    server_port = int(os.getenv("PORT", 7860))

    parser = argparse.ArgumentParser()
    parser.add_argument("--share", action="store_true", help="Meong")
    args = parser.parse_args()
    if args.share:
        share_link = True

    demo.launch(
        server_name="127.0.0.1",
        server_port=server_port,
        theme=gr.themes.Default(),
        share=share_link,
    )
