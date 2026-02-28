from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from supabase import create_client
from dotenv import load_dotenv
import os

# =========================
# Load Environment Variables
# =========================

load_dotenv()

app = FastAPI()

# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# OpenAI Setup
# =========================

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# =========================
# Supabase Setup
# =========================

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
    language: str = '한국어'

class EvaluationRequest(BaseModel):
    user_id: str
    question: str
    answer: str
    language: str = '한국어'

# =========================
# Generate Question
# =========================

@app.post("/generate-question")
def generate_question(req: QuestionRequest):

    try:
        prompt = f"""
        {req.job_role} 포지션 기술 면접 질문 1개를 {req.language}로 생성해주세요.
        질문만 출력하고, 번호나 부가 설명 없이 질문 문장만 반환하세요.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"당신은 시니어 기술 면접관입니다. 모든 응답은 {req.language}로 작성하세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )

        question = response.choices[0].message.content

        # Supabase 저장
        supabase.table("interview_results").insert({
            "user_id": req.user_id,
            "question": question
        }).execute()

        return {"question": question}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# Evaluate Answer
# =========================

@app.post("/evaluate-answer")
def evaluate_answer(req: EvaluationRequest):

    try:
        prompt = f"""
        Question: {req.question}

        Answer: {req.answer}

        Evaluate the answer in {req.language} and provide:
        - Score (0-100)
        - Strengths
        - Weaknesses
        - Improvement advice
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a senior technical interviewer. Respond entirely in {req.language}."},
                {"role": "user", "content": prompt}
            ]
        )

        evaluation = response.choices[0].message.content

        # Supabase 저장 f
        supabase.table("interview_results").insert({
            "user_id": req.user_id,
            "question": req.question,
            "answer": req.answer,
            "evaluation": evaluation
        }).execute()

        return {"evaluation": evaluation}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    