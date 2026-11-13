# app.py
import json
import streamlit as st
from doc_processor import extract_text_from_files
from ai_engine import (
    get_ai_client,
    extract_topics,
    generate_questions,
    evaluate_user_answers,
    DIFFICULTY_DESCRIPTIONS
)
from database import (
    init_db,
    save_questions,
    get_all_questions,
    update_question,
    delete_question
)

# Дерекқорды іске қосу
init_db()

# Беттің негізгі баптаулары
st.set_page_config(page_title="AI Сұрақ Генераторы", page_icon="📚", layout="wide")

st.title("📚 Оқу материалдары бойынша AI сұрақ генераторы")
st.markdown("Оқулықтарды (**PDF** немесе **TXT**) жүктеңіз, AI негізгі тақырыптарды анықтап, **5 қиындық деңгейі** бойынша сұрақтар құрастырады.")

# --- Бүйірлік панель (Sidebar): API баптаулары ---
with st.sidebar:
    st.header("⚙️ AI Модель баптаулары")
    api_key = st.text_input("API Кілт (API Key)", type="password", placeholder="AIza...")
    model_name = st.text_input("Модель атауы", value="gemini-3.5-flash-lite")
    
    st.divider()
    st.info("Кеңес: Google Gemini API кілтін енгізіңіз.")

# Негізгі жұмыс аймағын екі қойындыға (Tab) бөлу
tab1, tab2 = st.tabs(["📝 1. Сұрақтар құрастыру және Тест тапсыру", "🗄️ 2. Сақталған сұрақтар қоры"])

# ==========================================
# 1-ҚОЙЫНДЫ: Құжат жүктеу, сұрақ құрастыру және жауап беру
# ==========================================
with tab1:
    st.subheader("1-қадам. Оқу материалдарын жүктеу")
    uploaded_files = st.file_uploader(
        "Файлдарды таңдаңыз (PDF, TXT)",
        type=["pdf", "txt"],
        accept_multiple_files=True
    )

    if uploaded_files:
        current_names = [f.name for f in uploaded_files]
        if "doc_data" not in st.session_state or st.session_state["doc_data"]["filenames"] != current_names:
            with st.spinner("Құжаттардан мәтін алынуда..."):
                st.session_state["doc_data"] = extract_text_from_files(uploaded_files)
                st.session_state["topics"] = []
                st.session_state["latest_questions"] = []
                st.session_state["checked_answers"] = {}
                st.session_state["user_eval_report"] = ""

        doc_data = st.session_state["doc_data"]

        if doc_data["empty_files"]:
            st.warning(
                f"⚠️ Мына файлдардан мәтін табылмады (сканерленген PDF болуы мүмкін): "
                f"**{', '.join(doc_data['empty_files'])}**."
            )

        if doc_data["pages"]:
            st.success(f"Құжаттар жүктелді: **{doc_data['display_name']}** (Барлығы {len(doc_data['pages'])} мәтіндік бет/бөлім)")

            with st.expander("Құжат мәтінін алдын ала қарау"):
                st.text(doc_data["full_text"][:1500] + "...")

            st.divider()
            st.subheader("2-қадам. Негізгі тақырыптарды анықтау")
            
            if st.button("🔍 AI арқылы тақырыптарды анықтау"):
                if not api_key:
                    st.error("Алдымен сол жақ панельде API кілтін енгізіңіз!")
                else:
                    try:
                        with st.spinner("AI мәтінді талдап, тақырыптарды іздеуде..."):
                            client = get_ai_client(api_key.strip())
                            topics = extract_topics(client, doc_data["full_text"], model_name.strip())
                            st.session_state["topics"] = topics
                    except Exception as e:
                        st.error(f"Қате орын алды: {e}")

            # 3-қадам: Сұрақ параметрлерін таңдау
            if st.session_state.get("topics"):
                st.divider()
                st.subheader("3-қадам. Сұрақ параметрлерін таңдау")
                
                col1, col2 = st.columns(2)
                with col1:
                    selected_topic = st.selectbox("Тақырыпты таңдаңыз:", st.session_state["topics"])
                    difficulty = st.selectbox(
                        "Қиындық деңгейін таңдаңыз (1–5):",
                        options=[1, 2, 3, 4, 5],
                        format_func=lambda x: f"{x}-деңгей: {DIFFICULTY_DESCRIPTIONS[x]}"
                    )
                with col2:
                    num_questions = st.number_input("Сұрақтар саны:", min_value=1, max_value=10, value=5)
                    question_type = st.radio(
                        "Сұрақ түрін таңдаңыз:",
                        ["Тест сұрақтары", "Ашық сұрақтар"]
                    )

                if st.button("✨ Сұрақтарды құрастыру", type="primary"):
                    if not api_key:
                        st.error("API кілтін енгізіңіз!")
                    else:
                        try:
                            client = get_ai_client(api_key.strip())
                            with st.spinner("AI сұрақтар құрастыруда..."):
                                questions = generate_questions(
                                    client=client,
                                    pages=doc_data["pages"],
                                    topic=selected_topic,
                                    num_questions=num_questions,
                                    difficulty=difficulty,
                                    question_type=question_type,
                                    model=model_name.strip()
                                )
                            
                            save_questions(doc_data["display_name"], questions)
                            st.session_state["latest_questions"] = questions
                            # Жаңа сұрақтар үшін алдыңғы жауаптар күйін тазалау
                            st.session_state["checked_answers"] = {}
                            st.session_state["user_eval_report"] = ""
                            st.success(f"Сәтті аяқталды! {len(questions)} жаңа сұрақ құрастырылды. Төменде жауап беріп көріңіз:")
                        except Exception as e:
                            st.error(f"Сұрақ құрастыру кезінде қате шықты: {e}")

            # 4-қадам: Интерактивті түрде сұрақтарға жауап беру
            if st.session_state.get("latest_questions"):
                st.divider()
                st.subheader("4-қадам. Сұрақтарға жауап беріңіз")
                
                questions_list = st.session_state["latest_questions"]
                checked_map = st.session_state.get("checked_answers", {})

                for idx, q in enumerate(questions_list):
                    with st.container(border=True):
                        st.markdown(f"**{idx + 1}. [{q['difficulty']}-деңгей | {q['question_type']}] {q['question_text']}**")
                        
                        # Тест сұрағы болса — батырмалы (radio) таңдау шығару
                        if q.get("options"):
                            user_choice = st.radio(
                                "Жауап нұсқасын таңдаңыз:",
                                options=q["options"],
                                index=None,
                                key=f"radio_q_{idx}"
                            )
                        else:
                            # Ашық сұрақ болса — мәтін енгізу өрісі
                            user_choice = st.text_area(
                                "Жауабыңызды жазыңыз:",
                                key=f"text_q_{idx}",
                                placeholder="Осында өз жауабыңызды енгізіңіз..."
                            )

                        # Пайдаланушы жауабын тексеру батырмасы
                        if st.button("✅ Жауапты тексеру", key=f"btn_check_{idx}"):
                            if not user_choice or not str(user_choice).strip():
                                st.warning("Алдымен жауапты таңдаңыз немесе жазыңыз!")
                            else:
                                checked_map[idx] = str(user_choice).strip()
                                st.session_state["checked_answers"] = checked_map

                        # Егер осы сұрақ тексерілген болса — нәтижесі мен түсіндірмесін көрсету
                        if idx in checked_map:
                            submitted_ans = checked_map[idx]
                            correct_ans = str(q["correct_answer"]).strip()

                            if q.get("options"):
                                # Тест сұрағын дәл немесе әріп бойынша (A, B, C, D) салыстыру
                                is_correct = (
                                    submitted_ans == correct_ans
                                    or submitted_ans[:2].upper() == correct_ans[:2].upper()
                                )
                                if is_correct:
                                    st.success(f"🎉 Дұрыс! Сіздің жауабыңыз: **{submitted_ans}**")
                                else:
                                    st.error(f"❌ Қате! Сіздің жауабыңыз: **{submitted_ans}** | Дұрыс жауап: **{correct_ans}**")
                            else:
                                st.info(f"📝 Сіздің жауабыңыз қабылданды. **Үлгілі дұрыс жауап:** {correct_ans}")

                            st.markdown(f"**Түсіндірме:** {q['explanation']}")
                            st.caption(f"Дереккөз: {q.get('source_section', '-')}")

                # Барлық сұрақтар аяқталған соң — пайдаланушы жауаптарының сапасын AI арқылы тексеру
                st.divider()
                st.subheader("5-қадам. Барлық жауаптардың сапасын AI арқылы бағалау")
                st.write(f"Орындалған сұрақтар саны: **{len(checked_map)} / {len(questions_list)}**")

                if st.button("🛡️ Жауаптар сапасын AI арқылы тексеру", type="primary"):
                    if not api_key:
                        st.error("Тексеру үшін сол жақ панельде API кілтін енгізіңіз!")
                    elif len(checked_map) < len(questions_list):
                        st.warning(f"Алдымен барлық {len(questions_list)} сұраққа жауап беріп, әрқайсысын тексеріңіз!")
                    else:
                        try:
                            # Пайдаланушының барлық жауаптарын жинақтау
                            qa_records = []
                            for idx, q in enumerate(questions_list):
                                qa_records.append({
                                    "question": q["question_text"],
                                    "type": q["question_type"],
                                    "correct_answer": q["correct_answer"],
                                    "user_answer": checked_map.get(idx, "")
                                })

                            client = get_ai_client(api_key.strip())
                            with st.spinner("AI сіздің барлық жауаптарыңыздың сапасын талдауда..."):
                                report = evaluate_user_answers(client, qa_records, model_name.strip())
                                st.session_state["user_eval_report"] = report
                        except Exception as e:
                            st.error(f"Бағалау кезінде қате шықты: {e}")

                if st.session_state.get("user_eval_report"):
                    with st.container(border=True):
                        st.markdown("### 📊 AI Сапа Тексерісінің Қорытындысы")
                        st.markdown(st.session_state["user_eval_report"])

# ==========================================
# 2-ҚОЙЫНДЫ: Сақталған сұрақтарды көру және өңдеу
# ==========================================
with tab2:
    st.subheader("Сақталған сұрақтар тізімі (Көру, Өңдеу, Өшіру)")
    all_questions = get_all_questions()

    if not all_questions:
        st.info("Дерекқорда әзірге сұрақтар жоқ. Алдымен құжат жүктеп, сұрақтар құрастырыңыз.")
    else:
        st.write(f"Барлық сақталған сұрақтар саны: **{len(all_questions)}**")
        
        json_export = json.dumps(all_questions, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 Барлық сұрақтарды JSON ретінде жүктеп алу",
            data=json_export,
            file_name="generated_questions.json",
            mime="application/json"
        )

        st.divider()

        for q in all_questions:
            with st.expander(f"#{q['id']} | {q['topic']} | {q['difficulty']}-деңгей | {q['question_text'][:60]}..."):
                st.caption(f"Құжат: {q['doc_name']} | Түрі: {q['question_type']} | Дереккөз: {q['source_section']}")
                
                if q["options"]:
                    st.write("**Нұсқалар:**")
                    for opt in q["options"]:
                        st.write(f"- {opt}")

                with st.form(key=f"edit_form_{q['id']}"):
                    edited_text = st.text_area("Сұрақ мәтіні:", value=q["question_text"])
                    edited_answer = st.text_input("Дұрыс жауап:", value=q["correct_answer"])
                    edited_exp = st.text_area("Түсіндірме:", value=q["explanation"])

                    col_save, col_del = st.columns([1, 1])
                    with col_save:
                        if st.form_submit_button("💾 Өзгерістерді сақтау"):
                            update_question(q["id"], edited_text, edited_answer, edited_exp)
                            st.success("Сұрақ жаңартылды!")
                            st.rerun()
                    with col_del:
                        if st.form_submit_button("🗑️ Сұрақты өшіру"):
                            delete_question(q["id"])
                            st.warning("Сұрақ өшірілді!")
                            st.rerun()

#————————————————————————————————————————————————————————————————————by Aynar