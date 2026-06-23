import os
import json
from groq import Groq
from models.schemas import ResumeScore, JobDescription
from services.embeddings import match_skills
from dotenv import load_dotenv
from services.parser import extract_email
load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def score_resume(
    resume_text: str,
    file_name: str,
    job: JobDescription
) -> ResumeScore:

    # Use embeddings for skill matching instead of LLM guessing
    matched, missing = match_skills(job.required_skills, resume_text)

    prompt = f"""
You are an expert HR recruiter with experience hiring across technical, managerial, sales, finance, and operations roles.

Analyze this resume against the job description and return a JSON response ONLY.
No explanation, no markdown, just raw JSON.

JOB DETAILS:
- Title: {job.title}
- Description: {job.description}
- Required Skills: {", ".join(job.required_skills)}
- Required Experience: {job.experience_years} years

ALREADY MATCHED SKILLS (detected via semantic analysis): {", ".join(matched)}
MISSING SKILLS (not found in resume): {", ".join(missing)}

RESUME TEXT:
{resume_text[:4000]}

Important rules:
- Use the already matched and missing skills provided above, do not re-evaluate skills yourself.
- For managerial roles: look for leadership experience, team size managed, budget ownership, stakeholder communication.
- For sales or marketing roles: look for revenue targets hit, campaign results, client handling, and growth metrics.
- For finance roles: look for tools like Excel, Tally, SAP, and experience with reporting, auditing, or forecasting.
- Consider internships and projects as partial experience, not zero experience.
- Calculate match_score based on: skill match percentage (60%), experience match (25%), overall profile fit (15%).

Return this exact JSON structure:
{{
    "candidate_name": "full name from resume or Unknown",
    "match_score": <float 0-100>,
    "skill_match": {json.dumps(matched)},
    "missing_skills": {json.dumps(missing)},
    "experience_match": <true or false>,
    "summary": "3-4 lines: mention candidate strengths, relevant projects, and why they fit or dont fit this role",
    "recommendation": "STRONG FIT (score>=80) or GOOD FIT (score 50-79) or WEAK FIT (score<50)"
}}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are an expert HR AI assistant. Always respond with valid JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.3,
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    data = json.loads(raw)

    return ResumeScore(
        candidate_name=data.get("candidate_name", "Unknown"),
        file_name=file_name,
        email=extract_email(resume_text),
        match_score=data.get("match_score", 0),
        skill_match=matched,        # use embedding results, not LLM results
        missing_skills=missing,     # use embedding results, not LLM results
        experience_match=data.get("experience_match", False),
        summary=data.get("summary", ""),
        recommendation=data.get("recommendation", "WEAK FIT")
    )


def rank_candidates(results: list[ResumeScore]) -> list[ResumeScore]:
    return sorted(results, key=lambda x: x.match_score, reverse=True)