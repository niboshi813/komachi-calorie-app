import streamlit as st
import csv
import os
from datetime import date
import pandas as pd

st.set_page_config(
    page_title="小町のカロリー計算アプリ",
    page_icon="🐶",
    layout="centered"
)

st.title("🐶 小町のカロリー計算アプリ")
st.write("体重・食事・運動を入力すると、カロリーバランスを確認できます。")

# 保存ファイル名
file_name = "dog_log.csv"

# -------------------------
# 基本情報
# -------------------------
st.header("基本情報")
log_date = st.date_input("日付", value=date.today())
weight = st.number_input("体重 (kg)", min_value=0.0, step=0.1)

# -------------------------
# 食事
# -------------------------
st.header("食事")
food_kcal = st.number_input("ご飯カロリー (kcal)", min_value=0, step=10)
snack_kcal = st.number_input("おやつカロリー (kcal)", min_value=0, step=10)

# -------------------------
# 運動
# -------------------------
st.header("運動")

exercise_types = {
    "なし": 0.0,
    "ゆっくり散歩": 0.08,
    "普通の散歩": 0.12,
    "速歩": 0.16,
    "ラン": 0.22,
    "ドッグラン": 0.18,
    "室内遊び": 0.10
}

exercise_type1 = st.selectbox("運動タイプ①", list(exercise_types.keys()))
exercise_time1 = st.number_input("運動時間① (分)", min_value=0, step=5)

exercise_type2 = st.selectbox("運動タイプ②", list(exercise_types.keys()))
exercise_time2 = st.number_input("運動時間② (分)", min_value=0, step=5)

# -------------------------
# 備考
# -------------------------
st.header("備考")
memo = st.text_area(
    "メモ・備考",
    placeholder="例：朝うんち良好、おやつ少なめ、散歩でよく走った など"
)

# 計算結果を保存する箱
calculated_data = None

# -------------------------
# 計算ボタン
# -------------------------
if st.button("計算する"):
    if weight <= 0:
        st.error("体重を入力してください。")
    else:
        # RER計算
        rer = 70 * (weight ** 0.75)

        # DER（今回は係数1.6で固定）
        der = rer * 1.6

        # 摂取カロリー
        intake = food_kcal + snack_kcal

        # 運動消費カロリー
        burn1 = weight * exercise_types[exercise_type1] * exercise_time1
        burn2 = weight * exercise_types[exercise_type2] * exercise_time2
        exercise_burn = burn1 + burn2

        # 総消費カロリー
        total_burn = rer + exercise_burn

        # カロリーバランス
        balance = intake - total_burn

        # 判定とコメント
        if balance < -100:
            result = "不足"
            comment = "ごはん量が少ないかもしれません。体重の変化も確認してみましょう。"
        elif -100 <= balance < -30:
            result = "やや不足"
            comment = "少し少なめです。体調や便の様子を見ながら調整しましょう。"
        elif -30 <= balance <= 30:
            result = "適正"
            comment = "いいバランスです。今の食事と運動を続けやすい状態です。"
        elif 30 < balance <= 100:
            result = "やや多め"
            comment = "少し多めです。おやつ量やごはん量を少し見直してもよさそうです。"
        else:
            result = "多め"
            comment = "食べすぎ気味かもしれません。食事量やおやつ量を調整してみましょう。"

        # 保存用データ
        calculated_data = {
            "日付": str(log_date),
            "体重(kg)": round(weight, 1),
            "目安摂取カロリー(DER)": round(der, 1),
            "摂取カロリー合計": round(intake, 1),
            "運動消費カロリー": round(exercise_burn, 1),
            "総消費カロリー": round(total_burn, 1),
            "カロリーバランス": round(balance, 1),
            "判定": result,
            "コメント": comment,
            "備考": memo
        }

        st.session_state["calculated_data"] = calculated_data

# 計算済みデータを取り出す
if "calculated_data" in st.session_state:
    calculated_data = st.session_state["calculated_data"]

# -------------------------
# 結果表示
# -------------------------
if calculated_data is not None:
    st.header("結果")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("目安摂取カロリー（DER）", f'{calculated_data["目安摂取カロリー(DER)"]:.1f} kcal')
        st.metric("摂取カロリー合計", f'{calculated_data["摂取カロリー合計"]:.1f} kcal')
        st.metric("運動消費カロリー", f'{calculated_data["運動消費カロリー"]:.1f} kcal')

    with col2:
        st.metric("総消費カロリー", f'{calculated_data["総消費カロリー"]:.1f} kcal')
        st.metric("カロリーバランス", f'{calculated_data["カロリーバランス"]:.1f} kcal')
        st.metric("判定", calculated_data["判定"])

    st.subheader("コメント")
    st.write(calculated_data["コメント"])

    if calculated_data["備考"]:
        st.subheader("備考")
        st.write(calculated_data["備考"])

    # 保存ボタン
    if st.button("この結果を保存する"):
        file_exists = os.path.exists(file_name)

        with open(file_name, mode="a", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)

            if not file_exists:
                writer.writerow([
                    "日付",
                    "体重(kg)",
                    "目安摂取カロリー(DER)",
                    "摂取カロリー合計",
                    "運動消費カロリー",
                    "総消費カロリー",
                    "カロリーバランス",
                    "判定",
                    "コメント",
                    "備考"
                ])

            writer.writerow([
                calculated_data["日付"],
                calculated_data["体重(kg)"],
                calculated_data["目安摂取カロリー(DER)"],
                calculated_data["摂取カロリー合計"],
                calculated_data["運動消費カロリー"],
                calculated_data["総消費カロリー"],
                calculated_data["カロリーバランス"],
                calculated_data["判定"],
                calculated_data["コメント"],
                calculated_data["備考"]
            ])

        st.success("記録を保存しました。")

# -------------------------
# 履歴表示
# -------------------------
st.header("保存履歴")
st.caption("※新しい記録が上に表示されます")

if os.path.exists(file_name):
    df = pd.read_csv(file_name, encoding="utf-8-sig")

    if not df.empty:
        # 日付を datetime に変換して新しい順に並べ替え
        df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
        df = df.sort_values("日付", ascending=False).reset_index(drop=True)

        # 表示用に日付を文字列へ戻す
        df_display = df.copy()
        df_display["日付"] = df_display["日付"].dt.strftime("%Y-%m-%d")

        # 行番号を1から始める
        df_display.index = df_display.index + 1

        st.dataframe(df_display, use_container_width=True)

        # -------------------------
        # 削除機能
        # -------------------------
        st.subheader("保存履歴を削除")

        delete_index = st.number_input(
            "削除したい行番号を入力してください",
            min_value=1,
            max_value=len(df_display),
            step=1
        )

        st.warning(
            f"{delete_index}行目を削除しようとしています。"
            "本当に削除する場合は、下のチェックを入れてください。"
        )

        confirm_delete = st.checkbox("削除を実行してもよい")

        if st.button("選んだ行を削除する"):
            if confirm_delete:
                df = df.drop(index=delete_index - 1).reset_index(drop=True)
                df["日付"] = df["日付"].dt.strftime("%Y-%m-%d")
                df.to_csv(file_name, index=False, encoding="utf-8-sig")
                st.success(f"{delete_index}行目を削除しました。ページを再読み込みすると反映が見やすいです。")
            else:
                st.error("削除前の確認チェックが入っていません。")

    else:
        st.info("保存された記録はありますが、中身は空です。")
else:
    st.info("まだ保存された記録はありません。")

# -------------------------
# グラフ表示
# -------------------------
st.header("グラフ")

if os.path.exists(file_name):
    df_graph = pd.read_csv(file_name, encoding="utf-8-sig")

    if not df_graph.empty:
        # 日付を日付型に変換
        df_graph["日付"] = pd.to_datetime(df_graph["日付"], errors="coerce")

        # グラフ用は古い順に並べる
        df_graph = df_graph.sort_values("日付", ascending=True).copy()

        # 体重の推移
        st.subheader("体重の推移")
        weight_chart = df_graph.set_index("日付")[["体重(kg)"]]
        st.line_chart(weight_chart)

        # カロリーバランスの推移
        st.subheader("カロリーバランスの推移")
        balance_chart = df_graph.set_index("日付")[["カロリーバランス"]]
        st.line_chart(balance_chart)

    else:
        st.info("グラフ表示できる記録がまだありません。")
else:
    st.info("保存ファイルがまだありません。")