from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from supabase import create_client
from dotenv import load_dotenv
import os
import PyPDF2

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
        prompt = f"""Generate exactly ONE technical interview question for a {req.job_role} position.
You MUST write the question in {req.language}.
Output ONLY the question sentence. No numbering, no explanation, no extra text."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a senior technical interviewer. You MUST respond ONLY in {req.language}. Do not use any other language."},
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
        prompt = f"""Question: {req.question}

Answer: {req.answer}

Evaluate the answer above. You MUST respond ONLY in {req.language}.
Provide:
- Score (0-100)
- Strengths
- Weaknesses
- Improvement advice"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a senior technical interviewer. You MUST respond ONLY in {req.language}. Do not use any other language under any circumstances."},
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


# =========================
# Analyze Resume
# =========================

@app.post("/analyze-resume")
def analyze_resume(file: UploadFile = File(...)):
    try:
        # PDF 텍스트 추출
        pdf_reader = PyPDF2.PdfReader(file.file)
        text = "\n".join(page.extract_text() or "" for page in pdf_reader.pages)
        if not text.strip():
            raise HTTPException(status_code=400, detail="PDF에서 텍스트를 추출할 수 없습니다.")
        # OpenAI 프롬프트
        prompt = f"""
        아래는 한 지원자의 이력서 전문입니다. 이 내용을 바탕으로 맞춤형 기술 면접 질문 1개를 생성하세요.
        질문은 지원자의 경력, 기술, 프로젝트, 역할에 맞게 구체적으로 작성하고, 질문만 출력하세요.
        이력서:
        {text}
        """
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert technical interviewer. Generate a personalized interview question based on the resume below. Output ONLY the question."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        question = response.choices[0].message.content
        return question
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
