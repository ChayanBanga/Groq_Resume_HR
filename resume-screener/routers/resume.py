import os
import shutil
import json
from typing import Annotated, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from models.schemas import JobDescription, ScreeningResult
from services.parser import parse_resume
from services.groq_service import score_resume, rank_candidates

router = APIRouter(prefix="/api/resume", tags=["Resume Screener"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/screen", response_model=ScreeningResult)
async def screen_resumes(
    files: Annotated[List[UploadFile], File(description="Upload PDF or DOCX resumes")],
    job_data: Annotated[str, Form(description="Job description as JSON string")]
):
    """
    Screen multiple resumes against a job description.
    Returns ranked candidates with AI scores.
    """
    try:
        job_dict = json.loads(job_data)
        job = JobDescription(**job_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid job description: {str(e)}")

    if not files:
        raise HTTPException(status_code=400, detail="No resume files uploaded")

    results = []

    for file in files:
        file_path = os.path.join(UPLOAD_DIR, file.filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            resume_text = parse_resume(file_path)

            if not resume_text:
                raise ValueError("Could not extract text from resume")

            score = score_resume(
                resume_text=resume_text,
                file_name=file.filename,
                job=job
            )
            results.append(score)

        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    ranked = rank_candidates(results)

    return ScreeningResult(
        job_title=job.title,
        total_resumes=len(ranked),
        results=ranked
    )


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "Resume Screener", "model": "llama-3.3-70b-versatile"}