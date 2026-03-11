import streamlit as st
import csv
import os
from datetime import date
import pandas as pd

st.set_page_config(
    page_title="小町の健康管理アプリ",
    page_icon="🐶",
    layout="centered"
)

st.title("🐶 小町の健康管理アプリ")
st.caption("スマホで使いやすい、小町専用の必要カロリー＆成長記録アプリ")

file_name = "dog_log.csv"
photo_dir = "photos"

# 写真保存フォルダ
os.makedirs(photo_dir, exist_ok=True)


# -------------------------
# MER係数を決める関数
# -------------------------
def get_mer_factor(age_group, neutered, body_type, activity_level):
    if age_group == "子犬":
        base_factor = 2.5
    elif age_group == "成犬":
        base_factor = 1.6 if neutered == "あり" else 1.8
    else:  # シニア
        base_factor = 1.2 if neutered == "あり" else 1.4

    body_factor_map = {
        "やせ": 1.1,
        "標準": 1.0,
        "ぽっちゃり": 0.9
    }
    body_factor = body_factor_map[body_type]

    activity_factor_map = {
        "少ない": 0.9,
        "普通": 1.0,
        "多い": 1.2
    }
    activity_factor = activity_factor_map[activity_level]

    return base_factor * body_factor * activity_factor


# -------------------------
# データ読み込み関数
# -------------------------
def load_data():
    if os.path.exists(file_name):
        df = pd.read_csv(file_name, encoding="utf-8-sig")
        if not df.empty:
            df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
            df = df.sort_values("日付", ascending=False).reset_index(drop=True)
        return df
    return pd.DataFrame()


# -------------------------
# タブ構成
# -------------------------
tab1, tab2, tab3 = st.tabs(["計算", "履歴", "アルバム"])


# =========================================================
# 計算タブ
# =========================================================
with tab1:
    st.subheader("今日の必要カロリーを計算")

    log_date = st.date_input("日付", value=date.today(), key="calc_date")
    weight = st.number_input("体重 (kg)", min_value=0.0, step=0.1, key="calc_weight")

    age_group = st.selectbox(
        "年齢",
        ["子犬", "成犬", "シニア"],
        key="calc_age"
    )

    neutered = st.selectbox(
        "去勢・避妊の有無",
        ["あり", "なし"],
        key="calc_neutered"
    )

    body_type = st.selectbox(
        "体型",
        ["やせ", "標準", "ぽっちゃり"],
        key="calc_body"
    )

    activity_level = st.selectbox(
        "活動量",
        ["少ない", "普通", "多い"],
        key="calc_activity"
    )

    memo = st.text_area(
        "メモ・備考",
        placeholder="例：最近少しやせ気味、食欲あり、毛並み良好 など",
        key="calc_memo"
    )

    photo = st.file_uploader(
        "写真を追加",
        type=["jpg", "jpeg", "png"],
        key="calc_photo"
    )

    calculated_data = None

    if st.button("計算する", use_container_width=True):
        if weight <= 0:
            st.error("体重を入力してください。")
        else:
            rer = 70 * (weight ** 0.75)
            mer_factor = get_mer_factor(age_group, neutered, body_type, activity_level)
            mer = rer * mer_factor
            daily_kcal = mer

            note_text = "これは推定値です。2〜4週間の体重変化を見ながら食事量を調整してください。"

            photo_name = ""
            if photo is not None:
                ext = photo.name.split(".")[-1]
                photo_name = f"{log_date}_{weight:.1f}kg.{ext}"

            calculated_data = {
                "日付": str(log_date),
                "体重(kg)": round(weight, 1),
                "年齢": age_group,
                "去勢避妊": neutered,
                "体型": body_type,
                "活動量": activity_level,
                "RER": round(rer, 1),
                "推定MER": round(mer, 1),
                "1日目安カロリー": round(daily_kcal, 1),
                "注意文": note_text,
                "備考": memo,
                "写真ファイル名": photo_name
            }

            st.session_state["calculated_data"] = calculated_data
            st.session_state["uploaded_photo"] = photo

    if "calculated_data" in st.session_state:
        calculated_data = st.session_state["calculated_data"]

    if calculated_data is not None:
        st.divider()
        st.subheader("結果")

        st.metric("RER", f'{calculated_data["RER"]:.1f} kcal')
        st.metric("推定MER", f'{calculated_data["推定MER"]:.1f} kcal')
        st.metric("1日目安カロリー", f'{calculated_data["1日目安カロリー"]:.1f} kcal')

        st.info("これは推定値です。2〜4週間の体重変化を見ながら食事量を調整してください。")

        if calculated_data["備考"]:
            st.write(f"**備考**: {calculated_data['備考']}")

        if "uploaded_photo" in st.session_state and st.session_state["uploaded_photo"] is not None:
            st.write("**選択中の写真**")
            st.image(st.session_state["uploaded_photo"], use_container_width=True)

        if st.button("この結果を保存する", use_container_width=True):
            file_exists = os.path.exists(file_name)

            # 写真保存
            if "uploaded_photo" in st.session_state and st.session_state["uploaded_photo"] is not None:
                uploaded_photo = st.session_state["uploaded_photo"]
                photo_path = os.path.join(photo_dir, calculated_data["写真ファイル名"])
                with open(photo_path, "wb") as f:
                    f.write(uploaded_photo.getbuffer())

            # CSV保存
            with open(file_name, mode="a", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)

                if not file_exists:
                    writer.writerow([
                        "日付",
                        "体重(kg)",
                        "年齢",
                        "去勢避妊",
                        "体型",
                        "活動量",
                        "RER",
                        "推定MER",
                        "1日目安カロリー",
                        "注意文",
                        "備考",
                        "写真ファイル名"
                    ])

                writer.writerow([
                    calculated_data["日付"],
                    calculated_data["体重(kg)"],
                    calculated_data["年齢"],
                    calculated_data["去勢避妊"],
                    calculated_data["体型"],
                    calculated_data["活動量"],
                    calculated_data["RER"],
                    calculated_data["推定MER"],
                    calculated_data["1日目安カロリー"],
                    calculated_data["注意文"],
                    calculated_data["備考"],
                    calculated_data["写真ファイル名"]
                ])

            st.success("記録を保存しました。")


# =========================================================
# 履歴タブ
# =========================================================
with tab2:
    st.subheader("保存履歴")
    st.caption("※新しい記録が上に表示されます")

    df = load_data()

    if not df.empty:
        df_display = df.copy()
        df_display["日付"] = df_display["日付"].dt.strftime("%Y-%m-%d")
        df_display.index = df_display.index + 1

        # スマホで全部横に広い表は見づらいので主要項目だけ表示
        st.dataframe(
            df_display[["日付", "体重(kg)", "年齢", "体型", "活動量", "1日目安カロリー"]],
            use_container_width=True
        )

        st.write("### 記録の詳細")
        for i, row in df.iterrows():
            title = f"{row['日付'].strftime('%Y-%m-%d')} / {row['体重(kg)']}kg / {row['体型']}"
            with st.expander(title):
                st.write(f"**年齢**: {row['年齢']}")
                st.write(f"**去勢避妊**: {row['去勢避妊']}")
                st.write(f"**活動量**: {row['活動量']}")
                st.write(f"**RER**: {row['RER']} kcal")
                st.write(f"**推定MER**: {row['推定MER']} kcal")
                st.write(f"**1日目安カロリー**: {row['1日目安カロリー']} kcal")
                if isinstance(row["備考"], str) and row["備考"] != "":
                    st.write(f"**備考**: {row['備考']}")

        st.divider()
        st.write("### 履歴を削除")

        delete_index = st.number_input(
            "削除したい行番号を入力してください",
            min_value=1,
            max_value=len(df_display),
            step=1,
            key="delete_index"
        )

        st.warning(f"{delete_index}行目を削除しようとしています。削除してよければチェックを入れてください。")
        confirm_delete = st.checkbox("削除を実行してもよい", key="confirm_delete")

        if st.button("選んだ行を削除する", use_container_width=True):
            if confirm_delete:
                target_row = df.iloc[delete_index - 1]
                target_photo = target_row["写真ファイル名"]

                if isinstance(target_photo, str) and target_photo != "":
                    target_photo_path = os.path.join(photo_dir, target_photo)
                    if os.path.exists(target_photo_path):
                        os.remove(target_photo_path)

                df = df.drop(index=delete_index - 1).reset_index(drop=True)
                df["日付"] = df["日付"].dt.strftime("%Y-%m-%d")
                df.to_csv(file_name, index=False, encoding="utf-8-sig")
                st.success(f"{delete_index}行目を削除しました。ページを再読み込みすると見やすいです。")
            else:
                st.error("削除前の確認チェックが入っていません。")

    else:
        st.info("まだ保存された記録はありません。")


# =========================================================
# アルバムタブ
# =========================================================
with tab3:
    st.subheader("小町の成長アルバム")

    df = load_data()

    if not df.empty:
        has_photo = False

        for _, row in df.iterrows():
            photo_file = row["写真ファイル名"]

            if isinstance(photo_file, str) and photo_file != "":
                photo_path = os.path.join(photo_dir, photo_file)

                if os.path.exists(photo_path):
                    has_photo = True
                    st.write(f"### {row['日付'].strftime('%Y-%m-%d')}")
                    st.image(photo_path, use_container_width=True)
                    st.write(f"**体重**: {row['体重(kg)']} kg")
                    st.write(f"**体型**: {row['体型']}")
                    st.write(f"**1日目安カロリー**: {row['1日目安カロリー']} kcal")
                    if isinstance(row["備考"], str) and row["備考"] != "":
                        st.write(f"**メモ**: {row['備考']}")
                    st.divider()

        if not has_photo:
            st.info("写真付きの記録はまだありません。")

    else:
        st.info("まだ保存された記録はありません。")
