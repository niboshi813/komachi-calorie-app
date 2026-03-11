import streamlit as st
import pandas as pd
from datetime import date
import gspread

st.set_page_config(
    page_title="小町の健康管理アプリ",
    page_icon="🐶",
    layout="centered"
)

st.title("🐶 小町の健康管理アプリ")
st.caption("必要カロリー計算＋Googleスプレッドシート保存")

# -------------------------
# Googleスプレッドシート接続
# -------------------------
@st.cache_resource
def get_worksheet():
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    spreadsheet = gc.open(st.secrets["app"]["spreadsheet_name"])
    worksheet = spreadsheet.worksheet(st.secrets["app"]["worksheet_name"])
    return worksheet


def load_data():
    ws = get_worksheet()
    records = ws.get_all_records()
    if records:
        df = pd.DataFrame(records)
        if "日付" in df.columns:
            df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
            df = df.sort_values("日付", ascending=False).reset_index(drop=True)
        return df
    return pd.DataFrame(columns=[
        "日付", "体重(kg)", "年齢", "去勢避妊", "体型", "活動量",
        "RER", "推定MER", "1日目安カロリー", "メモ"
    ])


def append_data(row):
    ws = get_worksheet()
    all_values = ws.get_all_values()

    # シートが空なら見出しを先に入れる
    if not all_values:
        ws.append_row(list(row.keys()))

    ws.append_row(list(row.values()))


def overwrite_data(df):
    ws = get_worksheet()
    ws.clear()

    if not df.empty:
        rows = [df.columns.tolist()] + df.astype(str).values.tolist()
        ws.update(rows)


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


# =================================================
# 計算タブ
# =================================================
with tab1:
    st.subheader("必要カロリー計算")

    log_date = st.date_input("日付", value=date.today())
    weight = st.number_input("体重 (kg)", min_value=0.0, step=0.1)

    age_group = st.selectbox("年齢", ["子犬", "成犬", "シニア"])
    neutered = st.selectbox("去勢・避妊の有無", ["あり", "なし"])
    body_type = st.selectbox("体型", ["やせ", "標準", "ぽっちゃり"])
    activity_level = st.selectbox("活動量", ["少ない", "普通", "多い"])

    memo = st.text_area("メモ", placeholder="例：最近少しやせ気味、食欲あり")

    if st.button("計算する", use_container_width=True):
        if weight <= 0:
            st.error("体重を入力してください。")
        else:
            rer = 70 * (weight ** 0.75)
            mer_factor = get_mer_factor(age_group, neutered, body_type, activity_level)
            mer = rer * mer_factor
            kcal = mer

            st.session_state["calc_result"] = {
                "日付": str(log_date),
                "体重(kg)": round(weight, 1),
                "年齢": age_group,
                "去勢避妊": neutered,
                "体型": body_type,
                "活動量": activity_level,
                "RER": round(rer, 1),
                "推定MER": round(mer, 1),
                "1日目安カロリー": round(kcal, 1),
                "メモ": memo
            }

    if "calc_result" in st.session_state:
        result = st.session_state["calc_result"]

        st.divider()
        st.subheader("結果")
        st.metric("RER", f'{result["RER"]:.1f} kcal')
        st.metric("推定MER", f'{result["推定MER"]:.1f} kcal')
        st.metric("1日目安カロリー", f'{result["1日目安カロリー"]:.1f} kcal')

        st.info("これは推定値。2〜4週間の体重変化で調整")

        if result["メモ"]:
            st.write(f'**メモ**: {result["メモ"]}')

        if st.button("この結果を保存する", use_container_width=True):
            try:
                append_data(result)
                st.success("Googleスプレッドシートに保存しました。")
                st.cache_resource.clear()
            except Exception as e:
                st.error(f"保存に失敗しました: {e}")


# =================================================
# 履歴タブ
# =================================================
with tab2:
    st.subheader("記録履歴")

    try:
        df = load_data()

        if df.empty:
            st.info("記録はまだありません")
        else:
            df_display = df.copy()
            if "日付" in df_display.columns:
                df_display["日付"] = df_display["日付"].dt.strftime("%Y-%m-%d")
            df_display.index = df_display.index + 1

            st.dataframe(df_display, use_container_width=True)

            st.divider()
            st.write("### 削除")

            delete_index = st.number_input(
                "削除したい行番号",
                min_value=1,
                max_value=len(df_display),
                step=1
            )

            confirm_delete = st.checkbox("削除を実行してもよい")

            if st.button("選んだ行を削除する", use_container_width=True):
                if not confirm_delete:
                    st.error("削除前の確認チェックが入っていません。")
                else:
                    df = df.drop(index=delete_index - 1).reset_index(drop=True)
                    if "日付" in df.columns:
                        df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
                        df["日付"] = df["日付"].dt.strftime("%Y-%m-%d")
                    overwrite_data(df)
                    st.success(f"{delete_index}行目を削除しました。")
                    st.cache_resource.clear()

    except Exception as e:
        st.error(f"履歴の読み込みに失敗しました: {e}")
