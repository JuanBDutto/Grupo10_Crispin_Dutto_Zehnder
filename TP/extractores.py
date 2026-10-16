import pymupdf as fitz
import docx

def extraer_pdf(ruta):
    texto = ""
    try:
        with fitz.open(ruta) as doc:
            for pagina in doc: 
                texto += pagina.get_text() + " \n"
    except: pass
    return texto

def extraer_docx(ruta):
    try:
        doc = docx.Document(ruta)
        return '\n'.join([p.text for p in doc.paragraphs])
    except: return ""

def extraer_texto_plano(ruta):
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            return f.read()
    except: return ""