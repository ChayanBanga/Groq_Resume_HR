from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer('all-MiniLM-L6-v2')

SIMILARITY_THRESHOLD = 0.45  # lower threshold for short skill words

def extract_skill_phrases(resume_text: str) -> list[str]:
    """Break resume into short phrases likely to contain skills"""
    import re
    # Split by newlines, bullets, commas, semicolons
    chunks = re.split(r'[\n,;•·|]', resume_text)
    # Keep only short chunks that look like skills (under 60 chars)
    skills = [c.strip() for c in chunks if 2 < len(c.strip()) < 60]
    return skills

def match_skills(required_skills: list[str], resume_text: str) -> tuple[list[str], list[str]]:
    if not required_skills:
        return [], []

    resume_phrases = extract_skill_phrases(resume_text)
    if not resume_phrases:
        return [], required_skills

    # Embed skill-to-skill (short phrases vs short phrases)
    required_embeddings = model.encode(required_skills, convert_to_tensor=True)
    resume_embeddings = model.encode(resume_phrases, convert_to_tensor=True)

    matched = []
    missing = []

    for i, skill in enumerate(required_skills):
        similarities = util.cos_sim(required_embeddings[i], resume_embeddings)[0]
        best_score = float(similarities.max())

        if best_score >= SIMILARITY_THRESHOLD:
            matched.append(skill)
        else:
            missing.append(skill)

    return matched, missing