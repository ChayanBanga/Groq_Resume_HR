import fitz  # PyMuPDF
from docx import Document
import os

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using PyMuPDF"""
    text = ""
    doc = fitz.open(file_path)
    for page in doc:
        text += page.get_text()
    doc.close()
    return text.strip()

def extract_text_from_docx(file_path: str) -> str:
    """Extract text from DOCX using python-docx"""
    doc = Document(file_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text.strip()

def parse_resume(file_path: str) -> str:
    """Auto-detect file type and extract text"""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Only PDF and DOCX allowed.")

def get_candidate_name(file_name: str) -> str:
    """Extract candidate name from filename as fallback"""
    name = os.path.splitext(file_name)[0]  # remove extension
    return name.replace("_", " ").replace("-", " ").title()