from datetime import date

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="小町の健康管理アプリ",
    page_icon="🐶",
    layout="centered"
)

st.title("🐶 小町の健康管理アプリ")
st.caption("必要カロリー計算 + フード量計算 + Googleスプレッドシート保存")


# -------------------------
# Googleスプレッドシート接続
# -------------------------
@st.cache_resource
def get_worksheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )

    gc = gspread.authorize(creds)
    spreadsheet = gc.open(st.secrets["app"]["spreadsheet_name"])
    worksheet = spreadsheet.worksheet(st.secrets["app"]["worksheet_name"])
    return worksheet


def load_data():
    worksheet = get_worksheet()
    records = worksheet.get_all_records()

    columns = [
        "日付",
        "体重(kg)",
        "年齢",
        "去勢避妊",
        "体型",
        "活動量",
        "RER",
        "推定MER",
        "1日目安カロリー",
        "フード商品名",
        "100gカロリー",
        "必要フード量(g)",
        "メモ"
    ]

    if records:
        df = pd.DataFrame(records)

        for col in columns:
            if col not in df.columns:
                df[col] = ""

        df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
        df = df.sort_values("日付", ascending=False).reset_index(drop=True)
        return df

    return pd.DataFrame(columns=columns)


def append_data(row_dict):
    worksheet = get_worksheet()
    existing_values = worksheet.get_all_values()

    # シートが完全に空なら見出しを先に追加
    if not existing_values:
        worksheet.append_row(list(row_dict.keys()))

    worksheet.append_row(list(row_dict.values()))


def overwrite_data(df):
    worksheet = get_worksheet()
    worksheet.clear()

    if not df.empty:
        rows = [df.columns.tolist()] + df.astype(str).values.tolist()
        worksheet.update(rows)


# -------------------------
# MER係数
# -------------------------
def get_mer_factor(age_group, neutered, body_type, activity_level):
    if age_group == "子犬":
        base = 2.5
    elif age_group == "成犬":
        base = 1.6 if neutered == "あり" else 1.8
    else:  # シニア
        base = 1.2 if neutered == "あり" else 1.4

    body_factor = {
        "やせ": 1.1,
        "標準": 1.0,
        "ぽっちゃり": 0.9
    }[body_type]

    activity_factor = {
        "少ない": 0.9,
        "普通": 1.0,
        "多い": 1.2
    }[activity_level]

    return base * body_factor * activity_factor


# -------------------------
# タブ
# -------------------------
tab1, tab2 = st.tabs(["計算", "履歴"])


# =========================================================
# 計算タブ
# =========================================================
with tab1:
    st.subheader("必要カロリー計算")

    log_date = st.date_input("日付", value=date.today(), key="log_date")
    weight = st.number_input("体重 (kg)", min_value=0.0, step=0.1, key="weight")

    age_group = st.selectbox(
        "年齢",
        ["子犬", "成犬", "シニア"],
        key="age_group"
    )

    neutered = st.selectbox(
        "去勢・避妊の有無",
        ["あり", "なし"],
        key="neutered"
    )

    body_type = st.selectbox(
        "体型",
        ["やせ", "標準", "ぽっちゃり"],
        key="body_type"
    )

    activity_level = st.selectbox(
        "活動量",
        ["少ない", "普通", "多い"],
        key="activity_level"
    )

    st.divider()
    st.subheader("フード情報")

    food_name = st.text_input(
        "フード商品名",
        placeholder="例：ロイヤルカナン ミニ インドア アダルト",
        key="food_name"
    )

    food_kcal = st.number_input(
        "100gあたりカロリー (kcal)",
        min_value=0.0,
        step=1.0,
        key="food_kcal"
    )

    memo = st.text_area(
        "メモ・備考",
        placeholder="例：食欲あり、便の状態よし、元気に散歩できた",
        key="memo"
    )

    if st.button("計算する", use_container_width=True):
        if weight <= 0:
            st.error("体重を入力してください。")
        else:
            rer = 70 * (weight ** 0.75)
            mer_factor = get_mer_factor(age_group, neutered, body_type, activity_level)
            mer = rer * mer_factor
            daily_kcal = mer

            food_amount = ""
            if food_kcal > 0:
                food_amount = round(daily_kcal / (food_kcal / 100), 1)

            st.session_state["calculated_result"] = {
                "日付": str(log_date),
                "体重(kg)": round(weight, 1),
                "年齢": age_group,
                "去勢避妊": neutered,
                "体型": body_type,
                "活動量": activity_level,
                "RER": round(rer, 1),
                "推定MER": round(mer, 1),
                "1日目安カロリー": round(daily_kcal, 1),
                "フード商品名": food_name,
                "100gカロリー": round(food_kcal, 1) if food_kcal > 0 else "",
                "必要フード量(g)": food_amount,
                "メモ": memo
            }

    if "calculated_result" in st.session_state:
        result = st.session_state["calculated_result"]

        st.divider()
        st.subheader("結果")

        st.metric("RER", f'{result["RER"]:.1f} kcal')
        st.metric("推定MER", f'{result["推定MER"]:.1f} kcal')
        st.metric("1日目安カロリー", f'{result["1日目安カロリー"]:.1f} kcal')

        if result["必要フード量(g)"] != "":
            st.metric("1日必要フード量", f'{result["必要フード量(g)"]:.1f} g')

        st.info("これは推定値です。2〜4週間の体重変化を見ながら食事量を調整してください。")

        if result["フード商品名"]:
            st.write(f'**フード商品名**: {result["フード商品名"]}')

        if result["100gカロリー"] != "":
            st.write(f'**100gあたりカロリー**: {result["100gカロリー"]:.1f} kcal')

        if result["メモ"]:
            st.write(f'**メモ**: {result["メモ"]}')

        if st.button("この結果を保存する", use_container_width=True):
            try:
                append_data(result)
                st.success("Googleスプレッドシートに保存しました。")
                st.cache_resource.clear()
            except Exception as e:
                st.error(f"保存に失敗しました: {e}")


# =========================================================
# 履歴タブ
# =========================================================
with tab2:
    st.subheader("記録履歴")

    try:
        df = load_data()

        if df.empty:
            st.info("記録はまだありません。")
        else:
            df_display = df.copy()
            df_display["日付"] = df_display["日付"].dt.strftime("%Y-%m-%d")
            df_display.index = df_display.index + 1

            # スマホ向けに主要項目だけ表示
            st.dataframe(
                df_display[[
                    "日付",
                    "体重(kg)",
                    "年齢",
                    "体型",
                    "活動量",
                    "1日目安カロリー",
                    "必要フード量(g)"
                ]],
                use_container_width=True
            )

            st.divider()
            st.write("### 記録の詳細")

            for _, row in df.iterrows():
                title = f"{row['日付'].strftime('%Y-%m-%d')} / {row['体重(kg)']}kg / {row['体型']}"
                with st.expander(title):
                    st.write(f"**年齢**: {row['年齢']}")
                    st.write(f"**去勢避妊**: {row['去勢避妊']}")
                    st.write(f"**活動量**: {row['活動量']}")
                    st.write(f"**RER**: {row['RER']} kcal")
                    st.write(f"**推定MER**: {row['推定MER']} kcal")
                    st.write(f"**1日目安カロリー**: {row['1日目安カロリー']} kcal")

                    if "フード商品名" in row and isinstance(row["フード商品名"], str) and row["フード商品名"] != "":
                        st.write(f"**フード商品名**: {row['フード商品名']}")

                    if "100gカロリー" in row and str(row["100gカロリー"]) != "":
                        st.write(f"**100gあたりカロリー**: {row['100gカロリー']} kcal")

                    if "必要フード量(g)" in row and str(row["必要フード量(g)"]) != "":
                        st.write(f"**必要フード量**: {row['必要フード量(g)']} g")

                    if isinstance(row["メモ"], str) and row["メモ"] != "":
                        st.write(f"**メモ**: {row['メモ']}")

            st.divider()
            st.write("### 履歴を削除")

            delete_index = st.number_input(
                "削除したい行番号",
                min_value=1,
                max_value=len(df_display),
                step=1,
                key="delete_index"
            )

            st.warning(f"{delete_index}行目を削除しようとしています。削除してよければチェックを入れてください。")
            confirm_delete = st.checkbox("削除を実行してもよい", key="confirm_delete")

            if st.button("選んだ行を削除する", use_container_width=True):
                if not confirm_delete:
                    st.error("削除前の確認チェックが入っていません。")
                else:
                    df = df.drop(index=delete_index - 1).reset_index(drop=True)
                    df["日付"] = pd.to_datetime(df["日付"], errors="coerce").dt.strftime("%Y-%m-%d")
                    overwrite_data(df)
                    st.success(f"{delete_index}行目を削除しました。")
                    st.cache_resource.clear()

            st.divider()
            st.subheader("グラフ")

            df_graph = df.sort_values("日付", ascending=True).copy()

            st.write("**体重の推移**")
            weight_chart = df_graph.set_index("日付")[["体重(kg)"]]
            st.line_chart(weight_chart)

            st.write("**1日目安カロリーの推移**")
            kcal_chart = df_graph.set_index("日付")[["1日目安カロリー"]]
            st.line_chart(kcal_chart)

            if "必要フード量(g)" in df_graph.columns:
                # 空文字をNaNに寄せてグラフ化しやすくする
                food_chart_df = df_graph.copy()
                food_chart_df["必要フード量(g)"] = pd.to_numeric(
                    food_chart_df["必要フード量(g)"], errors="coerce"
                )
                if food_chart_df["必要フード量(g)"].notna().any():
                    st.write("**必要フード量の推移**")
                    food_chart = food_chart_df.set_index("日付")[["必要フード量(g)"]]
                    st.line_chart(food_chart)

    except Exception as e:
        st.error(f"履歴の読み込みに失敗しました: {e}")
