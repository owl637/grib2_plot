# streamlit run streamlit_app.py
import streamlit as st
import pygrib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import cartopy.crs as ccrs
import tempfile

plt.rcParams["font.family"] = "IPAexGothic"  # Streamlit Cloud にもともと入っているフォント名

st.set_page_config(layout="wide")
st.title("GPVモデルデータの可視化")

WEATHER_KEYWORD = "192:192"

uploaded_file_col, controls_col = st.columns([1, 1])

with uploaded_file_col:
    uploaded_file = st.file_uploader("GRIB2ファイルを選択", type=["grib2", "bin"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    grbs = pygrib.open(tmp_path)
    grb_list = list(grbs)
    grbs.close()

    def is_weather_code(grb):
        return grb.name == "unknown" and WEATHER_KEYWORD in str(grb)

    def extract_label(grb):
        if grb.name != "unknown":
            return grb.name
        desc = str(grb)
        if WEATHER_KEYWORD in desc:
            return "天気コード"
        parts = desc.split(":")
        return parts[1].strip() if len(parts) > 1 else "unknown"

    all_labels = [extract_label(grb) for grb in grb_list]
    valid_dates = [getattr(grb, 'validDate', '?') for grb in grb_list]

    unique_labels = sorted(set(all_labels))
    unique_valids = sorted(set(valid_dates))

    # セッション初期化
    if "time_index" not in st.session_state:
        st.session_state.time_index = 0
    if "selected_labels" not in st.session_state:
        st.session_state.selected_labels = [unique_labels[0]]

    # 有効なインデックス範囲チェック
    if st.session_state.time_index >= len(unique_valids):
        st.session_state.time_index = 0

    with controls_col:
        # ドロップダウン：予報時刻
        selected_valid = st.selectbox(
            "予報時刻", unique_valids, index=st.session_state.time_index, key="valid_select"
        )
        # 選択に応じて time_index 更新
        st.session_state.time_index = unique_valids.index(selected_valid)

        # マルチセレクト：変数
        st.session_state.selected_labels = st.multiselect(
            "表示変数", unique_labels, default=st.session_state.selected_labels
        )

        # スライダー：予報時間
        time_index = st.slider(
            "← 予報時間 →", 0, len(unique_valids) - 1, st.session_state.time_index, key="slider"
        )
        st.session_state.time_index = time_index
        selected_valid = unique_valids[st.session_state.time_index]

        # 前・次ボタンをスライダー下に配置
        col_prev, col_next = st.columns([1, 1])
        with col_prev:
            if st.button("◀ 前"):
                st.session_state.time_index = max(0, st.session_state.time_index - 1)
                selected_valid = unique_valids[st.session_state.time_index]
                st.rerun()
        with col_next:
            if st.button("次 ▶"):
                st.session_state.time_index = min(len(unique_valids) - 1, st.session_state.time_index + 1)
                selected_valid = unique_valids[st.session_state.time_index]
                st.rerun()

    # フィルタして描画
    filtered_grbs = [
        grb for grb in grb_list
        if extract_label(grb) in st.session_state.selected_labels and getattr(grb, 'validDate', '?') == selected_valid
    ]

    # 2列で横並び表示し、余ったら次の行
    for i in range(0, len(filtered_grbs), 2):
        cols = st.columns(2)
        for j, grb in enumerate(filtered_grbs[i:i+2]):
            with cols[j]:
                data, lats, lons = grb.data()
                fig = plt.figure(figsize=(8, 6))
                ax = plt.axes(projection=ccrs.PlateCarree())
                ax.coastlines()
                title = extract_label(grb)
                ax.set_title(f"{title} ({grb.validDate})", fontsize=15)
                plt.tight_layout()

                if is_weather_code(grb):
                    code_labels = ['晴れ', '曇り', '雨', '雨または雪', '雪']
                    code_colors = ['gold', 'lightgray', 'blue', 'mediumpurple', 'cyan']
                    cmap = mcolors.ListedColormap(code_colors)
                    bounds = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
                    norm = mcolors.BoundaryNorm(bounds, cmap.N)
                    im = ax.pcolormesh(lons, lats, data, cmap=cmap, norm=norm, shading='auto')
                    cbar = plt.colorbar(im, ticks=[1, 2, 3, 4, 5])
                    cbar.ax.set_yticklabels(code_labels)
                    cbar.set_label("天気コード")
                else:
                    cont = ax.contourf(lons, lats, data, cmap='coolwarm')
                    plt.colorbar(cont, label=grb.units)

                st.pyplot(fig)
