import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_APP_PASSWORD = os.getenv("SENDER_APP_PASSWORD")


def send_shortlist_email(candidate_name: str, candidate_email: str, job_title: str):
    """Send shortlist email to strong fit candidates"""

    subject = f"You've been shortlisted for {job_title}"

    body = f"""
Dear {candidate_name},

We have reviewed your resume and are pleased to inform you that you have been shortlisted for the position of {job_title}.

Your profile stood out among our applicants and we would love to move forward with you in our hiring process. Our team will be in touch shortly to schedule an interview.

In the meantime, if you have any questions feel free to reply to this email.

Best regards,
HR Team
    """

    _send_email(candidate_email, subject, body)


def send_rejection_email(candidate_name: str, candidate_email: str, job_title: str):
    """Send polite rejection email to weak fit candidates"""

    subject = f"Your application for {job_title}"

    body = f"""
Dear {candidate_name},

Thank you for taking the time to apply for the position of {job_title} and for your interest in joining our team.

After carefully reviewing your profile, we have decided to move forward with other candidates whose experience more closely matches our current requirements.

We truly appreciate your effort and encourage you to apply for future openings that match your skills. We will keep your profile on record.

Wishing you all the best in your job search.

Best regards,
HR Team
    """

    _send_email(candidate_email, subject, body)


def _send_email(to_email: str, subject: str, body: str):
    """Core SMTP sending function"""

    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        print(f"Email sent to {to_email}")