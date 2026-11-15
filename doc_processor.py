import pymupdf  # PDF файлдарын оқуға арналған кітапхана

def extract_text_from_files(uploaded_files) -> dict:
    """
    Бір немесе бірнеше жүктелген PDF/TXT файлдарынан мәтінді алады.
    Барлық файл атауларын, беттер/бөлімдер тізімін және толық мәтінді қайтарады.
    """
    filenames = []
    pages_content = []
    empty_files = []

    for uploaded_file in uploaded_files:
        filename = uploaded_file.name
        filenames.append(filename)
        file_pages_count = 0

        if filename.lower().endswith(".pdf"):
            # PDF файлын байт ағыны ретінде ашу
            file_bytes = uploaded_file.read()
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
            for page_num in range(len(doc)):
                text = doc[page_num].get_text("text").strip()
                if text:
                    pages_content.append({
                        "section": f"[{filename}] {page_num + 1}-бет",
                        "text": text
                    })
                    file_pages_count += 1
        elif filename.lower().endswith(".txt"):
            # TXT файлын UTF-8 форматында оқу
            text = uploaded_file.read().decode("utf-8", errors="ignore").strip()
            # Мәтінді 2000 таңбадан тұратын бөлімдерге бөлу
            chunk_size = 2000
            for i in range(0, len(text), chunk_size):
                pages_content.append({
                    "section": f"[{filename}] {i // chunk_size + 1}-бөлім",
                    "text": text[i:i + chunk_size]
                })
                file_pages_count += 1

        # Егер файлдан ешқандай мәтін табылмаса (мысалы, сканерленген PDF)
        if file_pages_count == 0:
            empty_files.append(filename)

    return {
        "filenames": filenames,
        "display_name": ", ".join(filenames),
        "pages": pages_content,
        "full_text": "\n\n".join([p["text"] for p in pages_content]),
        "empty_files": empty_files
    }

#————————————————————————————————————————————————————————————————————by Aynar

import re


def clean_text(text: str) -> str:
    """
    Құжаттан алынған мәтінді тазалайды.
    Артық бос орындар мен қажетсіз бос жолдарды жояды.
    """

    # Мәтіндегі бірнеше бос орынды бір бос орынға ауыстыру
    text = re.sub(r"[ \t]+", " ", text)

    # Артық бос жолдарды азайту
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    # Мәтіннің басы мен соңындағы бос орындарды жою
    text = text.strip()

    return text


def process_document_data(document_data: dict) -> dict:
    """
    Алынған құжат мәтіндерін тазалап,
    бөлімдер бойынша қайта өңдейді.
    """

    # Өңделген бөлімдерді сақтау
    cleaned_pages = []

    # Әр бөлімдегі мәтінді тазалау
    for page in document_data["pages"]:
        cleaned_content = clean_text(page["text"])

        # Бос емес бөлімдерді ғана сақтау
        if cleaned_content:
            cleaned_pages.append({
                "section": page["section"],
                "text": cleaned_content
            })

    # Барлық тазаланған мәтінді біріктіру
    full_text = "\n\n".join(
        page["text"] for page in cleaned_pages
    )

    # Нәтижені бастапқы деректер құрылымында қайтару
    return {
        "filenames": document_data["filenames"],
        "display_name": document_data["display_name"],
        "pages": cleaned_pages,
        "full_text": full_text,
        "empty_files": document_data["empty_files"]
    }


#————————————————————————————————————————————————————————————————————by Arayle