from pydantic import BaseModel
from typing import List, Optional

class JobDescription(BaseModel):
    title: str
    description: str
    required_skills: List[str]
    experience_years: Optional[int] = 0

class ResumeScore(BaseModel):
    candidate_name: str
    file_name: str
    match_score: float          # 0-100
    skill_match: List[str]      # matched skills
    missing_skills: List[str]   # skills not found
    experience_match: bool
    flagged: bool = False       # True if integrity checks found something suspicious
    flag_reasons: List[str] = [] 
    summary: str                # AI generated summary
    recommendation: str         # STRONG FIT / GOOD FIT / WEAK FIT

class ScreeningResult(BaseModel):
    job_title: str
    total_resumes: int
    results: List[ResumeScore]  # ranked list, best first
