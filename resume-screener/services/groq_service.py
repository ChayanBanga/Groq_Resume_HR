import os
from groq import Groq
from models.schemas import ResumeScore, JobDescription
import json
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def score_resume(
    resume_text: str,
    file_name: str,
    job: JobDescription
) -> ResumeScore:
    """Send resume + job description to Groq LLaMA 70B and get structured score"""

    prompt = f"""
You are an expert HR recruiter and technical interviewer.

Analyze this resume against the job description and return a JSON response ONLY.
No explanation, no markdown, just raw JSON.

JOB DETAILS:
- Title: {job.title}
- Description: {job.description}
- Required Skills: {", ".join(job.required_skills)}
- Required Experience: {job.experience_years} years

RESUME TEXT:
{resume_text[:4000]}  # limit to avoid token overflow

Return this exact JSON structure:
{{
    "candidate_name": "full name from resume or Unknown",
    "match_score": <float 0-100>,
    "skill_match": ["skill1", "skill2"],
    "missing_skills": ["skill3", "skill4"],
    "experience_match": <true or false>,
    "summary": "3-4 lines: mention candidate strengths, relevant projects, and why they fit or dont fit this role",
    "recommendation": "STRONG FIT (score>=80) or GOOD FIT (score 50-79) or WEAK FIT (score<50)"
}}

Be strict but fair. Consider projects and internships as partial experience. 
Penalize only if critical skills are completely missing.
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
        temperature=0.3,  # low temp = consistent structured output
    )

    raw = response.choices[0].message.content.strip()

    # Clean up if model wraps in markdown
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    data = json.loads(raw)

    return ResumeScore(
        candidate_name=data.get("candidate_name", "Unknown"),
        file_name=file_name,
        match_score=data.get("match_score", 0),
        skill_match=data.get("skill_match", []),
        missing_skills=data.get("missing_skills", []),
        experience_match=data.get("experience_match", False),
        summary=data.get("summary", ""),
        recommendation=data.get("recommendation", "WEAK FIT")
    )


def rank_candidates(results: list[ResumeScore]) -> list[ResumeScore]:
    """Sort candidates by match score, highest first"""
    return sorted(results, key=lambda x: x.match_score, reverse=True)