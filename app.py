import io
from datetime import date

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from PIL import Image
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(
    page_title="小町の健康管理アプリ",
    page_icon="🐶",
    layout="centered"
)

st.title("🐶 小町の健康管理アプリ")
st.caption("必要カロリー計算・記録・写真アルバムをひとつにまとめた小町専用アプリ")


# -------------------------
# Google接続
# -------------------------
@st.cache_resource
def get_google_clients():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )

    gc = gspread.authorize(creds)
    drive_service = build("drive", "v3", credentials=creds)

    spreadsheet = gc.open(st.secrets["app"]["spreadsheet_name"])
    worksheet = spreadsheet.worksheet(st.secrets["app"]["worksheet_name"])

    return worksheet, drive_service


def load_data():
    worksheet, _ = get_google_clients()
    records = worksheet.get_all_records()

    columns = [
        "日付", "体重(kg)", "年齢", "去勢避妊", "体型", "活動量",
        "RER", "推定MER", "1日目安カロリー", "メモ",
        "写真URL", "写真ファイルID"
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
    worksheet, _ = get_google_clients()
    existing_values = worksheet.get_all_values()

    if not existing_values:
        worksheet.append_row(list(row_dict.keys()))

    worksheet.append_row(list(row_dict.values()))


def overwrite_data(df):
    worksheet, _ = get_google_clients()
    worksheet.clear()

    if not df.empty:
        rows = [df.columns.tolist()] + df.astype(str).values.tolist()
        worksheet.update(rows)


def upload_photo_to_drive(uploaded_file, file_name):
    def compress_image(uploaded_file):

    img = Image.open(uploaded_file)

    img.thumbnail((1280,1280))

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)

    buffer.seek(0)

    return buffer
    _, drive_service = get_google_clients()

    file_metadata = {
        "name": file_name,
        "parents": [st.secrets["app"]["drive_folder_id"]]
    }

    file_stream = compress_image(photo)
    media = MediaIoBaseUpload(file_stream, mimetype=uploaded_file.type)

    created_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webViewLink"
    ).execute()

    file_id = created_file["id"]

    # リンクを知っている人が閲覧できるようにする
    drive_service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"}
    ).execute()

    photo_url = f"https://drive.google.com/uc?id={file_id}"
    return photo_url, file_id


def delete_drive_file(file_id):
    if not file_id:
        return
    try:
        _, drive_service = get_google_clients()
        drive_service.files().delete(fileId=file_id).execute()
    except Exception:
        pass


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
tab1, tab2, tab3 = st.tabs(["計算", "履歴", "アルバム"])


# =========================================================
# 計算タブ
# =========================================================
with tab1:
    st.subheader("必要カロリー計算")

    log_date = st.date_input("日付", value=date.today(), key="log_date")
    weight = st.number_input("体重 (kg)", min_value=0.0, step=0.1, key="weight")

    age_group = st.selectbox("年齢", ["子犬", "成犬", "シニア"], key="age_group")
    neutered = st.selectbox("去勢・避妊の有無", ["あり", "なし"], key="neutered")
    body_type = st.selectbox("体型", ["やせ", "標準", "ぽっちゃり"], key="body_type")
    activity_level = st.selectbox("活動量", ["少ない", "普通", "多い"], key="activity_level")

    memo = st.text_area(
        "メモ・備考",
        placeholder="例：食欲あり、便の状態よし、元気に散歩できた",
        key="memo"
    )

    photo = st.file_uploader(
        "写真を追加",
        type=["jpg", "jpeg", "png"],
        key="photo"
    )

    if st.button("計算する", use_container_width=True):
        if weight <= 0:
            st.error("体重を入力してください。")
        else:
            rer = 70 * (weight ** 0.75)
            mer_factor = get_mer_factor(age_group, neutered, body_type, activity_level)
            mer = rer * mer_factor
            daily_kcal = mer

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
                "メモ": memo
            }

    if "calculated_result" in st.session_state:
        result = st.session_state["calculated_result"]

        st.divider()
        st.subheader("結果")
        st.metric("RER", f'{result["RER"]:.1f} kcal')
        st.metric("推定MER", f'{result["推定MER"]:.1f} kcal')
        st.metric("1日目安カロリー", f'{result["1日目安カロリー"]:.1f} kcal')

        st.info("これは推定値です。2〜4週間の体重変化を見ながら食事量を調整してください。")

        if result["メモ"]:
            st.write(f'**メモ**: {result["メモ"]}')

        if photo is not None:
            st.write("**選択中の写真**")
            st.image(photo, use_container_width=True)

        if st.button("この結果を保存する", use_container_width=True):
            try:
                photo_url = ""
                photo_file_id = ""

                if photo is not None:
                    safe_date = result["日付"]
                    safe_weight = result["体重(kg)"]
                    ext = photo.name.split(".")[-1].lower()
                    drive_file_name = f"komachi_{safe_date}_{safe_weight}kg.{ext}"
                    photo_url, photo_file_id = upload_photo_to_drive(photo, drive_file_name)

                save_row = {
                    "日付": result["日付"],
                    "体重(kg)": result["体重(kg)"],
                    "年齢": result["年齢"],
                    "去勢避妊": result["去勢避妊"],
                    "体型": result["体型"],
                    "活動量": result["活動量"],
                    "RER": result["RER"],
                    "推定MER": result["推定MER"],
                    "1日目安カロリー": result["1日目安カロリー"],
                    "メモ": result["メモ"],
                    "写真URL": photo_url,
                    "写真ファイルID": photo_file_id
                }

                append_data(save_row)
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

            st.dataframe(
                df_display[["日付", "体重(kg)", "年齢", "体型", "活動量", "1日目安カロリー"]],
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
                    if isinstance(row["メモ"], str) and row["メモ"] != "":
                        st.write(f"**メモ**: {row['メモ']}")
                    if isinstance(row["写真URL"], str) and row["写真URL"] != "":
                        st.image(row["写真URL"], use_container_width=True)

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
                    target_row = df.iloc[delete_index - 1]
                    file_id = target_row.get("写真ファイルID", "")
                    delete_drive_file(file_id)

                    df = df.drop(index=delete_index - 1).reset_index(drop=True)
                    df["日付"] = pd.to_datetime(df["日付"], errors="coerce").dt.strftime("%Y-%m-%d")
                    overwrite_data(df)
                    st.success(f"{delete_index}行目を削除しました。")
                    st.cache_resource.clear()

    except Exception as e:
        st.error(f"履歴の読み込みに失敗しました: {e}")


# =========================================================
# アルバムタブ
# =========================================================
with tab3:
    st.subheader("小町の成長アルバム")

    try:
        df = load_data()

        if df.empty:
            st.info("写真付き記録はまだありません。")
        else:
            has_photo = False

            for _, row in df.iterrows():
                if isinstance(row["写真URL"], str) and row["写真URL"] != "":
                    has_photo = True
                    st.write(f"### {row['日付'].strftime('%Y-%m-%d')}")
                    st.image(row["写真URL"], use_container_width=True)
                    st.write(f"**体重**: {row['体重(kg)']} kg")
                    st.write(f"**体型**: {row['体型']}")
                    st.write(f"**1日目安カロリー**: {row['1日目安カロリー']} kcal")
                    if isinstance(row["メモ"], str) and row["メモ"] != "":
                        st.write(f"**メモ**: {row['メモ']}")
                    st.divider()

            if not has_photo:
                st.info("写真付き記録はまだありません。")

    except Exception as e:
        st.error(f"アルバムの読み込みに失敗しました: {e}")


# =========================================================
# グラフ
# =========================================================
st.divider()
st.subheader("グラフ")

try:
    df_graph = load_data()

    if not df_graph.empty:
        df_graph = df_graph.sort_values("日付", ascending=True).copy()

        st.write("**体重の推移**")
        weight_chart = df_graph.set_index("日付")[["体重(kg)"]]
        st.line_chart(weight_chart)

        st.write("**1日目安カロリーの推移**")
        kcal_chart = df_graph.set_index("日付")[["1日目安カロリー"]]
        st.line_chart(kcal_chart)
    else:
        st.info("グラフ表示できる記録がまだありません。")

except Exception as e:
    st.error(f"グラフの読み込みに失敗しました: {e}")

