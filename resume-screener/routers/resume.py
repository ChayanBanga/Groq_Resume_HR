import os
import shutil
import json
import csv
import io
from typing import Annotated, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from services.email_service import send_shortlist_email, send_rejection_email
from models.schemas import JobDescription, ScreeningResult
from services.parser import parse_resume
from services.groq_service import score_resume, rank_candidates

router = APIRouter(prefix="/api/resume", tags=["Resume Screener"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Store last screening result in memory for export
last_result = {}


@router.post("/screen", response_model=ScreeningResult)
async def screen_resumes(
    files: Annotated[List[UploadFile], File(description="Upload PDF or DOCX resumes")],
    job_data: Annotated[str, Form(description="Job description as JSON string")]
):
    """
    Screen multiple resumes against a job description.
    Returns ranked candidates with AI scores.
    """
    global last_result

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

    # Save for export
    last_result = {
        "job_title": job.title,
        "results": ranked
    }

    return ScreeningResult(
        job_title=job.title,
        total_resumes=len(ranked),
        results=ranked
    )


@router.get("/export")
async def export_results():
    """Export last screening results as CSV"""

    if not last_result:
        raise HTTPException(status_code=404, detail="No screening results found. Run a screening first.")

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
    "Rank", "Candidate Name", "Email", "File Name", "Match Score (%)",
    "Recommendation", "Experience Match", "Matched Skills",
    "Missing Skills", "Summary"
    ])

    for i, candidate in enumerate(last_result["results"]):
        writer.writerow([
            i + 1,
            candidate.candidate_name,
            candidate.email or "Not found",
            candidate.file_name,
            candidate.match_score,
            candidate.recommendation,
            "Yes" if candidate.experience_match else "No",
            ", ".join(candidate.skill_match),
            ", ".join(candidate.missing_skills),
            candidate.summary
        ])

    output.seek(0)
    job_title = last_result["job_title"].replace(" ", "_")

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=screening_{job_title}.csv"}
    )
@router.post("/notify")
async def notify_candidates():
    """Send shortlist or rejection emails to all candidates"""

    if not last_result:
        raise HTTPException(status_code=404, detail="No screening results found. Run a screening first.")

    job_title = last_result["job_title"]
    results = last_result["results"]

    sent = []
    skipped = []

    for candidate in results:
        if not candidate.email:
            skipped.append(candidate.candidate_name)
            continue

        try:
            if candidate.recommendation.startswith("STRONG") or candidate.recommendation.startswith("GOOD"):
                send_shortlist_email(candidate.candidate_name, candidate.email, job_title)
                sent.append({"name": candidate.candidate_name, "email": candidate.email, "status": "shortlisted"})
            else:
                send_rejection_email(candidate.candidate_name, candidate.email, job_title)
                sent.append({"name": candidate.candidate_name, "email": candidate.email, "status": "rejected"})

        except Exception as e:
            skipped.append(f"{candidate.candidate_name} (error: {str(e)})")

    return {
        "message": "Emails processed",
        "sent": sent,
        "skipped": skipped
    }

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "Resume Screener", "model": "llama-3.3-70b-versatile"}