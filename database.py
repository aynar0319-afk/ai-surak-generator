# database.py
import sqlite3
import json

DB_NAME = "questions.db"

def init_db():
    """
    Дерекқорды және сұрақтар кестесін инициализациялайды.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_name TEXT,
            topic TEXT,
            difficulty INTEGER,
            question_type TEXT,
            question_text TEXT,
            options TEXT,
            correct_answer TEXT,
            explanation TEXT,
            source_section TEXT,
            quality_note TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_questions(doc_name: str, questions: list):
    """
    Құрастырылған сұрақтар тізімін дерекқорға сақтайды (7-тапсырма).
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for q in questions:
        options_json = json.dumps(q.get("options", []), ensure_ascii=False)
        cursor.execute("""
            INSERT INTO questions (
                doc_name, topic, difficulty, question_type,
                question_text, options, correct_answer, explanation,
                source_section, quality_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_name,
            q.get("topic", ""),
            q.get("difficulty", 1),
            q.get("question_type", ""),
            q.get("question_text", ""),
            options_json,
            q.get("correct_answer", ""),
            q.get("explanation", ""),
            q.get("source_section", ""),
            q.get("quality_note", "Тексерілмеген")
        ))
    conn.commit()
    conn.close()

def get_all_questions() -> list:
    """
    Дерекқорда сақталған барлық сұрақтарды қайтарады.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM questions ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        item = dict(row)
        item["options"] = json.loads(item["options"]) if item["options"] else []
        result.append(item)
    return result

def update_question(q_id: int, new_text: str, new_answer: str, new_explanation: str):
    """
    Таңдалған сұрақтың мәтінін, дұрыс жауабын және түсіндірмесін жаңартады (7-тапсырма).
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE questions
        SET question_text = ?, correct_answer = ?, explanation = ?
        WHERE id = ?
    """, (new_text, new_answer, new_explanation, q_id))
    conn.commit()
    conn.close()

def delete_question(q_id: int):
    """
    Сәтсіз сұрақты дерекқордан өшіреді (7-тапсырма).
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM questions WHERE id = ?", (q_id,))
    conn.commit()
    conn.close()