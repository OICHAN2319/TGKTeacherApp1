
import streamlit as st
import sqlite3
import random
import os
from dotenv import load_dotenv
from openai import OpenAI

# --- 設定 ---
# データベースパスの統一
DB_PATH = os.path.join(os.path.dirname(__file__), "quiz_ver2.db")

# OpenAI APIキーの読み込み
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 選択式クイズのデータをSQLiteから取得する関数
def get_quiz_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT question, option1, option2, option3, answerIndex FROM quiz")
    data = cursor.fetchall()
    conn.close()
    return [
        {"question": row[0], "options": [row[1], row[2], row[3]], "answerIndex": row[4]} for row in data
    ]

# 自由記述式クイズのデータをSQLiteから取得する関数
def fetch_openai_question():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT question_text, model_answer FROM questions")
    rows = cursor.fetchall()
    conn.close()
    if rows:
        row = random.choice(rows)
        return {"question_text": row[0], "model_answer": row[1]}
    return None

# OpenAI APIに自由記述の採点を依頼する関数
def get_score_and_feedback(question, model_answer, user_answer):
    prompt = f"""
    あなたは世界で有数のリフォームの専門家であり、先生です。
    「{question}」という質問に対する模範解答は、「{model_answer}」ですが、
    あなたの生徒が「{user_answer}」と回答しました。
    この回答に点数（100点満点）とアドバイスをください。
    出力形式: 
    点数: xx点
    アドバイス: xxx
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content

# --- セッションステートの初期化（状態管理） ---
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'score_quiz' not in st.session_state:
    st.session_state.score_quiz = 0
if 'quiz_order' not in st.session_state:
    quiz_data = get_quiz_data()
    st.session_state.quiz_order = random.sample(quiz_data, min(8, len(quiz_data)))
if 'answered' not in st.session_state:
    st.session_state.answered = False
if 'openai_done' not in st.session_state:
    st.session_state.openai_done = False
if 'openai_score' not in st.session_state:
    st.session_state.openai_score = 0
if 'show_result' not in st.session_state:
    st.session_state.show_result = False
if 'feedback' not in st.session_state:
    st.session_state.feedback = None
if 'question_data' not in st.session_state:
    st.session_state.question_data = fetch_openai_question()

# --- ユーザーインターフェースの表示開始 ---

# カスタムCSSでスタイル設定（背景色、フォント、タイトルデザイン）
st.markdown("""
     <style>
    .stApp {
        background-color: #EFF0FF;
        font-family: 'Noto Sans JP', sans-serif;
        color: black;
    }
    .big-title {
        font-size: 3.5em;
        font-weight: bold;
        color: #004098;
        text-align: center;
        margin-top: 2rem;
    }
    div.stButton {
        display: flex;
        justify-content: center;
        margin-top: 3rem;
    }
    div.stButton > button {
        background-color: #004098;
        color: white;
        padding: 0.8em 2em;
        font-size: 1.1em;
        border: none;
        border-radius: 8px;
        cursor: pointer;
    }
    /* ホバー時のスタイル */
    div.stButton > button:hover {
        background-color: #4974CE; /* 明るめの青 */
        color: #ffffff;
    }
    /* ラジオボタンそのものの色を青にする */
    input[type="radio"] {
        accent-color: #004098 !important;
        transform: scale(1.2);  /* オプション：少し大きくする */
        margin-right: 0.5em;
    }
    textarea {
        background-color: white !important;
        border-color: black;
        color: black;
    }
    .st-ao {
    background-color: rgb(188 195 207);
    }
    </style>

""", unsafe_allow_html=True)

# ロゴを表示
col1, col2 = st.columns([8, 1])

with col1:
    st.markdown('<div class="big-title">TGK<br>Teacherアプリ</div>', unsafe_allow_html=True)

with col2:
    st.image("logo.png",  use_container_width=True)

# 初期化
if "started" not in st.session_state:
    st.session_state.started = False

# コールバック関数：ボタンが押されたときに呼ばれる
def start_training():
    st.session_state.started = True

# 「トレーニングを始める」ボタンを表示し、押すとクイズ開始
if not st.session_state.started:
    st.markdown('<div class="start-button-wrapper">', unsafe_allow_html=True)
    st.button("トレーニングを始める", key="start_button", on_click=start_training)
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()



# --- 選択式クイズ（前半4問） ---
if st.session_state.current_question <len(st.session_state.quiz_order):
    q = st.session_state.quiz_order[st.session_state.current_question]
    st.subheader(f"選択問題 {st.session_state.current_question + 1}/{len(st.session_state.quiz_order)}")
    
    # 進捗バーと進捗状況表示
    progress = (st.session_state.current_question + 1) / len(st.session_state.quiz_order)
    st.progress(progress)  # 進捗バーを表示 
    remaining_questions = len(st.session_state.quiz_order) - st.session_state.current_question
    st.write(f"残り {remaining_questions} 問！")
    
    st.write(q["question"])
    selected = st.radio("選択肢を選んでください", q["options"], key=f"q{st.session_state.current_question}")
    
    if st.button("回答", key=f"submit{st.session_state.current_question}") and not st.session_state.answered:
        correct = q["options"][q["answerIndex"]]
        if selected == correct:
            st.success("正解！ +10点")
            st.session_state.score_quiz += 10
        else:
            st.error(f"不正解！ 正解は: {correct}")
        st.session_state.answered = True

    if st.session_state.answered:
        st.button("次の問題", on_click=lambda: st.session_state.update({
            "current_question": st.session_state.current_question + 1,
            "answered": False
        }))

# --- 自由記述式クイズ ---
elif not st.session_state.openai_done:
    st.subheader("自由記述問題")
    question_data = st.session_state.question_data
    st.write("以下の質問に答えてください：")
    st.markdown(f"**{question_data['question_text']}**")
    user_input = st.text_area("あなたの回答を記入してください")

    if st.button("採点"):
        with st.spinner("OpenAIで採点中..."):
            feedback = get_score_and_feedback(
                question_data["question_text"],
                question_data["model_answer"],
                user_input
            )
            import re
            score_match = re.search(r"点数[:：]?\s*(\d+)", feedback)
            if score_match:
                score = min(int(score_match.group(1)), 100)
                converted_score = round(score * 0.2)
                st.session_state.openai_score = converted_score
            else:
                st.session_state.openai_score = 0
            st.session_state.feedback = feedback
            st.session_state.openai_done = True

import streamlit as st
import plotly.graph_objects as go

# --- 採点結果 & 総合評価ボタン ---
if st.session_state.openai_done:
    st.markdown("### 採点結果")
    st.write(st.session_state.feedback)
    total_score = st.session_state.score_quiz + st.session_state.openai_score
    st.header("🎉 結果発表 🎉")
    st.write(f"選択式クイズ: {st.session_state.score_quiz} / 80点")
    st.write(f"自由記述クイズ: {st.session_state.openai_score} / 20点")
    st.subheader(f"総合得点: {total_score} / 100点")

    # --- メーター（ゲージ）表示 ---
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = total_score,  # 合計得点
        number = {"suffix": "点", "font": {"size": 60}},  # メーター下に「点」付きで表示
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'axis': {'range': [0, 100]},  # 軸の範囲（0から100）
            'bar': {'color': "#EF4123"},  # バーの色
            'bgcolor': "white",  # 背景色
            'borderwidth': 2,  # 枠の幅
            'bordercolor': "#FFB6C1",
            'steps': [
                {'range': [0, 60], 'color': "white"},   # 60点未満は白
                {'range': [60, 80], 'color': "white"},  # 60〜80点は白
                {'range': [80, 100], 'color': "#FFB6C1"}  # 80点以上は薄い赤
            ]
        }
    ))

    # メーターをStreamlitに表示
    st.plotly_chart(fig)

    # 合格点80点のラインを強調
    st.markdown("### 合格点ライン: 80点")
    st.markdown("合格点ラインを超えると、合格となります。")

    # 結果に応じたメッセージを表示
    if total_score >= 80:
        st.success("✅ 合格！おめでとうございます！")
    elif total_score >= 60:
        st.warning("⚠️ 惜しい！もう少し！")
    else:
        st.error("📚 もっと勉強しよう！")

    # 得点に応じたコメント
    if total_score >= 80:
        st.markdown('<div style="color: green; font-size: 1.5em; text-align: center;">🎉 合格！おめでとうございます！</div>', unsafe_allow_html=True)
    elif total_score >= 60:
        st.markdown('<div style="color: orange; font-size: 1.5em; text-align: center;">⚠️ 惜しい！もう少し！</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color: red; font-size: 1.5em; text-align: center;">📚 もっと勉強しよう！</div>', unsafe_allow_html=True)

    # 「TOPページに戻る」ボタン
    if st.button("TOPページに戻る"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()
