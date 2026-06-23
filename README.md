# AI Resume Screener

A backend-focused resume screening API built with FastAPI and Groq LLaMA 70B.
Upload multiple resumes, provide a job description, and get AI-powered candidate ranking with match scores.

## Tech Stack

- FastAPI - REST API framework
- Groq LLaMA 3.3 70B - AI scoring and analysis
- PyMuPDF - PDF text extraction
- python-docx - DOCX text extraction
- Pydantic - request/response validation

## Project Structure

```
resume-screener/
├── main.py
├── .env
├── requirements.txt
├── routers/
│   └── resume.py
├── services/
│   ├── parser.py
│   └── groq_service.py
├── models/
│   └── schemas.py
└── static/
    └── index.html
```

## Setup

1. Clone the repo and navigate to the project folder

2. Create and activate virtual environment

```
python -m venv venv
source venv/bin/activate
```

3. Install dependencies

```
pip install -r requirements.txt
```

4. Add your Groq API key to .env

```
GROQ_API_KEY=your_key_here
```

5. Run the server

```
uvicorn main:app --reload
```

## API Endpoints

POST /api/resume/screen - Upload resumes and job description, returns ranked candidates

GET /api/resume/health - Health check

GET / - Frontend UI

## Usage

Open the browser at http://localhost:8000

Fill in the job title, description, required skills, and upload PDF or DOCX resumes.
The AI will score and rank each candidate with matched skills, missing skills, and a summary.
