from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

# OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Supabase
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# =========================
# Request Models
# =========================

class QuestionRequest(BaseModel):
    job_role: str
    user_id: str

class EvaluationRequest(BaseModel):
    user_id: str
    question: str
    answer: str

# =========================
# Generate Question
# =========================

@app.post("/generate-question")
def generate_question(req: QuestionRequest):
    prompt = f"""
    Generate one technical interview question for a {req.job_role} position.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert technical interviewer."},
            {"role": "user", "content": prompt}
        ]
    )

    question = response.choices[0].message.content

    # Supabase 저장
    supabase.table("interview_results").insert({
        "user_id": req.user_id,
        "question": question
    }).execute()

    return {"question": question}


# =========================
# Evaluate Answer
# =========================

@app.post("/evaluate-answer")
def evaluate_answer(req: EvaluationRequest):

    prompt = f"""
    Question: {req.question}
    Answer: {req.answer}

    Evaluate the answer.
    Give:
    - Score (0-100)
    - Strengths
    - Weaknesses
    - Improvement advice
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a senior technical interviewer."},
            {"role": "user", "content": prompt}
        ]
    )

    evaluation = response.choices[0].message.content

    # Supabase 업데이트
    supabase.table("interview_results").insert({
        "user_id": req.user_id,
        "question": req.question,
        "answer": req.answer,
        "evaluation": evaluation
    }).execute()

    return {"evaluation": evaluation}