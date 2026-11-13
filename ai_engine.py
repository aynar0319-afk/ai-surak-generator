import json
import time
from google import genai
from google.genai import types

# Әртүрлі қиындық деңгейлерінің сипаттамасы
DIFFICULTY_DESCRIPTIONS = {
    1: "Өте жеңіл (Қарапайым анықтамалар мен фактілер)",
    2: "Жеңіл (Материалды түсіну деңгейі)",
    3: "Орташа (Білімді тәжірибеде қолдану)",
    4: "Қиын (Жағдайлар мен қателерді талдау)",
    5: "Өте қиын (Стандартты емес есептерді шешу)"
}

def get_ai_client(api_key: str, base_url: str = "") -> genai.Client:
    """
    Google Gemini AI моделімен байланысу үшін клиентті инициализациялайды.
    """
    return genai.Client(api_key=api_key)

def _call_gemini_with_retry(client: genai.Client, model: str, prompt: str, system_inst: str, temp: float, is_json: bool = True) -> str:
    """
    Сервер бос болмаған жағдайда (503 қатесі) автоматты түрде қайталап сұраныс жібереді.
    """
    models_to_try = list(dict.fromkeys([model, "gemini-3.5-flash-lite"]))
    config_args = {
        "system_instruction": system_inst,
        "temperature": temp
    }
    if is_json:
        config_args["response_mime_type"] = "application/json"

    last_error = None
    for current_model in models_to_try:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=current_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_args)
                )
                return response.text
            except Exception as e:
                last_error = e
                if "503" in str(e) or "429" in str(e) or "UNAVAILABLE" in str(e):
                    time.sleep(2)
                    continue
                else:
                    break
    raise last_error

def extract_topics(client: genai.Client, text: str, model: str = "gemini-3.5-flash-lite") -> list:
    """
    Мәтіннен негізгі оқу тақырыптарын анықтайды (2-тапсырма).
    """
    sample_text = text[:15000]
    prompt = f"""
    Сен тәжірибелі оқытушысың. Төмендегі оқу материалының мәтінін талдап, 5-тен 8-ге дейін негізгі тақырыптарды қазақ тілінде анықта.
    Жауапты тек қана JSON форматында қайтар. Формат үлгісі:
    {{"topics": ["1-тақырып", "2-тақырып", "3-тақырып"]}}

    Оқу материалы:
    {sample_text}
    """
    raw_text = _call_gemini_with_retry(
        client=client,
        model=model,
        prompt=prompt,
        system_inst="Сен оқу материалдарын талдайтын көмекшісің. Тек JSON форматында жауап бер.",
        temp=0.3
    )
    result = json.loads(raw_text)
    return result.get("topics", [])

def generate_questions(
    client: genai.Client,
    pages: list,
    topic: str,
    num_questions: int,
    difficulty: int,
    question_type: str,
    model: str = "gemini-3.5-flash-lite"
) -> list:
    """
    Таңдалған тақырып пен қиындық деңгейі бойынша сұрақтар құрастырады (3, 4, 5, 6-тапсырмалар).
    """
    relevant_pages = [p for p in pages if topic.lower() in p["text"].lower()]
    if not relevant_pages:
        relevant_pages = pages[:6]
        
    context_text = ""
    for p in relevant_pages[:6]:
        context_text += f"\n--- Дереккөз: {p['section']} ---\n{p['text'][:2500]}\n"

    diff_desc = DIFFICULTY_DESCRIPTIONS.get(difficulty, "")
    
    if question_type == "Тест сұрақтары":
        type_instruction = """
        Әр сұрақтың 4 жауап нұсқасы (A, B, C, D) болуы керек, оның ішінде тек біреуі ғана дұрыс.
        "options" өрісінде 4 нұсқаны ["A) ...", "B) ...", "C) ...", "D) ..."] түрінде көрсет.
        Ал "correct_answer" өрісіне сол дұрыс нұсқаның МӘТІНІН дәлме-дәл көшіріп жаз (мысалы: "B) ...").
        """
    else:
        type_instruction = """
        Бұл ашық сұрақтар. Жауап нұсқалары қажет емес ("options": []).
        "correct_answer" өрісіне үлгілі дұрыс жауапты жаз.
        """

    prompt = f"""
    Төмендегі оқу материалына сүйене отырып, қазақ тілінде {num_questions} сұрақ құрастыр.
    
    Тақырып: {topic}
    Қиындық деңгейі: {difficulty} - {diff_desc}
    Сұрақ түрі: {question_type}
    {type_instruction}

    Маңызды талаптар:
    1. Сұрақтар тек берілген мәтінге негізделуі тиіс.
    2. Қайталанатын сұрақтар болмауы керек.
    3. Жауапты тек мына JSON құрылымында қайтар:
    {{
        "questions": [
            {{
                "question_text": "Сұрақтың мәтіні",
                "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
                "correct_answer": "B) ...",
                "explanation": "Қысқаша түсіндірме",
                "difficulty": {difficulty},
                "topic": "{topic}",
                "question_type": "{question_type}",
                "source_section": "Мысалы: 2-бет"
            }}
        ]
    }}

    Оқу материалы:
    {context_text}
    """

    raw_text = _call_gemini_with_retry(
        client=client,
        model=model,
        prompt=prompt,
        system_inst="Сен қазақ тілінде білім тексеру сұрақтарын құрастыратын AI-жүйесің. Тек JSON форматында жауап бер.",
        temp=0.5
    )

    result = json.loads(raw_text)
    return result.get("questions", [])

def evaluate_user_answers(client: genai.Client, qa_records: list, model: str = "gemini-3.5-flash-lite") -> str:
    """
    Пайдаланушының барлық сұрақтарға берген жауаптарының сапасын AI арқылы кешенді тексереді.
    """
    prompt = f"""
    Сен тәжірибелі оқытушысың. Студент төмендегі сұрақтарға жауап берді.
    Оның жауаптарының сапасын талдап, қазақ тілінде толық қорытынды бер:
    1. Жалпы нәтиже және білім деңгейіне баға (мысалы: 100 баллдық жүйемен).
    2. Ашық сұрақтар мен тест сұрақтары бойынша жіберілген қателіктерге талдау.
    3. Қай тақырыптарды қайталау керектігі туралы нақты кеңестер.

    Студенттің жауаптары мен дұрыс жауаптар тізімі:
    {json.dumps(qa_records, ensure_ascii=False, indent=2)}
    """

    return _call_gemini_with_retry(
        client=client,
        model=model,
        prompt=prompt,
        system_inst="Сен студенттердің жауаптарын әділ әрі түсінікті бағалайтын AI-оқытушысың.",
        temp=0.4,
        is_json=False
    )

def verify_questions(client: genai.Client, questions: list, model: str = "gemini-3.5-flash-lite") -> list:
    """
    Құрастырылған сұрақтардың сапасын тексереді (8-тапсырма).
    """
    prompt = f"""
    Төмендегі сұрақтар тізімін тексер:
    1. Сұрақ тақырыпқа сәйкес пе?
    2. Дұрыс жауабы қатесіз бе?
    3. Қиындық деңгейі дұрыс таңдалған ба?

    Әр сұраққа қысқаша сапа бағасын ("quality_note") қосып, сол JSON құрылымында қайтар:
    {{"verified_questions": [...]}}

    Сұрақтар:
    {json.dumps(questions, ensure_ascii=False)}
    """
    
    raw_text = _call_gemini_with_retry(
        client=client,
        model=model,
        prompt=prompt,
        system_inst="Сен сұрақтардың сапасын тексеретін сарапшысың. Тек JSON форматында жауап бер.",
        temp=0.2
    )
    
    result = json.loads(raw_text)
    return result.get("verified_questions", questions)

#————————————————————————————————————————————————————————————————————by Aynar