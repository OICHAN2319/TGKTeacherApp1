
import streamlit as st
import sqlite3
import random
import os
from dotenv import load_dotenv
from openai import OpenAI

# --- 設定 ---
# データベースパスの統一
DB_PATH = os.path.join(os.path.dirname(__file__), "quiz.db")

# OpenAI APIキーの読み込み
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- ヘルパー関数 ---

# 選択式クイズの取得
def get_quiz_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT question, option1, option2, option3, answerIndex FROM quiz")
    data = cursor.fetchall()
    conn.close()
    return [
        {"question": row[0], "options": [row[1], row[2], row[3]], "answerIndex": row[4]} for row in data
    ]

# 自由回答クイズの取得
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

# OpenAI による採点
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

# --- セッション初期化 ---
if 'current_question' not in st.session_state:
    st.session_state.current_question = 0
if 'score_quiz' not in st.session_state:
    st.session_state.score_quiz = 0
if 'quiz_order' not in st.session_state:
    quiz_data = get_quiz_data()
    st.session_state.quiz_order = random.sample(quiz_data, min(4, len(quiz_data)))
if 'answered' not in st.session_state:
    st.session_state.answered = False
if 'openai_done' not in st.session_state:
    st.session_state.openai_done = False
if 'openai_score' not in st.session_state:
    st.session_state.openai_score = 0

# --- UI 表示 ---

st.title("TGKスキルアップ統合クイズ")

# 選択式クイズパート（4問）
if st.session_state.current_question < 4:
    q = st.session_state.quiz_order[st.session_state.current_question]
    st.subheader(f"選択式クイズ {st.session_state.current_question + 1}/4")
    st.write(q["question"])
    selected = st.radio("選択肢を選んでください", q["options"], key=f"q{st.session_state.current_question}")
    
    if st.button("回答", key=f"submit{st.session_state.current_question}") and not st.session_state.answered:
        correct = q["options"][q["answerIndex"]]
        if selected == correct:
            st.success("正解！ +20点")
            st.session_state.score_quiz += 20
        else:
            st.error(f"不正解！ 正解は: {correct}")
        st.session_state.answered = True

    if st.session_state.answered:
        st.button("次の問題", on_click=lambda: [st.session_state.update({"current_question": st.session_state.current_question + 1, "answered": False})])

# 自由回答パート（OpenAI評価）
elif not st.session_state.openai_done:
    st.subheader("自由記述式クイズ")
    question_data = fetch_openai_question()
    if question_data:
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
                st.session_state.openai_done = True

                # 点数の抽出
                import re
                score_match = re.search(r"点数[:：]?\s*(\d+)", feedback)
                if score_match:
                    score = min(int(score_match.group(1)), 100)
                    converted_score = round(score * 0.2)  # 20点満点換算
                    st.session_state.openai_score = converted_score
                else:
                    converted_score = 0

                st.markdown("### 採点結果")
                st.write(feedback)
    else:
        st.error("自由回答の質問が見つかりません。")

# 総合評価表示
elif st.session_state.openai_done:
    total_score = st.session_state.score_quiz + st.session_state.openai_score
    st.header("🎉 結果発表 🎉")
    st.write(f"選択式クイズ: {st.session_state.score_quiz} / 80点")
    st.write(f"自由記述クイズ: {st.session_state.openai_score} / 20点")
    st.subheader(f"総合得点: {total_score} / 100点")
