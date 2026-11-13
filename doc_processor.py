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