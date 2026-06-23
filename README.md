# AI Resume Screener

A backend-focused resume screening API built with FastAPI and Groq LLaMA 70B.
Upload multiple resumes, provide a job description, and get AI-powered candidate ranking with match scores, semantic skill matching, CSV export, and automated email notifications.

## Features

- PDF and DOCX resume parsing
- AI-powered candidate scoring and ranking using Groq LLaMA 3.3 70B
- Semantic skill matching using Sentence Transformers (all-MiniLM-L6-v2)
- Automatic email extraction from resumes
- CSV export with all candidate data
- Automated shortlist and rejection emails via Gmail SMTP
- Clean frontend UI served directly from FastAPI

## Tech Stack

- FastAPI - REST API framework
- Groq LLaMA 3.3 70B - AI scoring and analysis
- Sentence Transformers - semantic skill matching
- PyMuPDF - PDF text extraction
- python-docx - DOCX text extraction
- Pydantic - request/response validation
- Gmail SMTP - automated email notifications

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
│   ├── groq_service.py
│   ├── embeddings.py
│   └── email_service.py
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

4. Add your credentials to .env

```
GROQ_API_KEY=your_groq_api_key
SENDER_EMAIL=your_gmail@gmail.com
SENDER_APP_PASSWORD=your_gmail_app_password
```

To get a Gmail App Password:
- Go to myaccount.google.com
- Enable 2-Step Verification
- Search for App Passwords and generate one for Mail

5. Run the server

```
uvicorn main:app --reload
```

## API Endpoints

POST /api/resume/screen - Upload resumes and job description, returns ranked candidates

POST /api/resume/notify - Send shortlist or rejection emails to all candidates

GET /api/resume/export - Download screening results as CSV

GET /api/resume/health - Health check

GET / - Frontend UI

## Usage

Open the browser at http://localhost:8000

Fill in the job title, description, required skills, and upload PDF or DOCX resumes.
The AI will score and rank each candidate with matched skills, missing skills, and a summary.
After screening, download the results as CSV or click Send Emails to automatically notify all candidates.

## How Skill Matching Works

Skills are matched using semantic similarity via Sentence Transformers rather than exact keyword matching.
This means MySQL is correctly matched against SQL, XGBoost is inferred from Scikit-learn experience,
and domain-specific variations are handled intelligently without hardcoded rules.
