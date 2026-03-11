import streamlit as st
import pandas as pd
from datetime import date
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(
    page_title="小町の健康管理アプリ",
    page_icon="🐶",
    layout="centered"
)

st.title("🐶 小町の健康管理アプリ")
st.caption("必要カロリー計算＋健康記録")

# -------------------------
# Googleスプレッドシート接続
# -------------------------

scope = [
"https://spreadsheets.google.com/feeds",
"https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
"service_account.json", scope)

client = gspread.authorize(creds)

sheet = client.open("komachi_log").sheet1


# -------------------------
# MER係数
# -------------------------

def get_mer_factor(age_group, neutered, body_type, activity_level):

    if age_group == "子犬":
        base = 2.5
    elif age_group == "成犬":
        base = 1.6 if neutered == "あり" else 1.8
    else:
        base = 1.2 if neutered == "あり" else 1.4

    body_factor = {
        "やせ":1.1,
        "標準":1.0,
        "ぽっちゃり":0.9
    }[body_type]

    activity_factor = {
        "少ない":0.9,
        "普通":1.0,
        "多い":1.2
    }[activity_level]

    return base * body_factor * activity_factor


# -------------------------
# タブ
# -------------------------

tab1, tab2 = st.tabs(["計算","履歴"])


# =================================================
# 計算
# =================================================

with tab1:

    st.subheader("必要カロリー計算")

    log_date = st.date_input("日付", value=date.today())

    weight = st.number_input("体重 kg",min_value=0.0,step=0.1)

    age_group = st.selectbox(
        "年齢",
        ["子犬","成犬","シニア"]
    )

    neutered = st.selectbox(
        "去勢避妊",
        ["あり","なし"]
    )

    body_type = st.selectbox(
        "体型",
        ["やせ","標準","ぽっちゃり"]
    )

    activity_level = st.selectbox(
        "活動量",
        ["少ない","普通","多い"]
    )

    memo = st.text_area("メモ")


    if st.button("計算する"):

        rer = 70*(weight**0.75)

        mer_factor = get_mer_factor(
            age_group,
            neutered,
            body_type,
            activity_level
        )

        mer = rer*mer_factor

        kcal = mer

        st.metric("RER",f"{rer:.0f} kcal")
        st.metric("推定MER",f"{mer:.0f} kcal")
        st.metric("1日目安カロリー",f"{kcal:.0f} kcal")

        st.info("これは推定値。2〜4週間の体重変化で調整")

        if st.button("保存"):

            sheet.append_row([
                str(log_date),
                weight,
                age_group,
                neutered,
                body_type,
                activity_level,
                round(rer,1),
                round(mer,1),
                round(kcal,1),
                memo
            ])

            st.success("保存しました")


# =================================================
# 履歴
# =================================================

with tab2:

    st.subheader("記録履歴")

    data = sheet.get_all_records()

    if len(data) == 0:

        st.info("記録はまだありません")

    else:

        df = pd.DataFrame(data)

        st.dataframe(df,use_container_width=True)
