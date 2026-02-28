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
        prompt = f"""Generate exactly ONE technical interview question for a {req.job_role} position.\nYou MUST write the question in {req.language}.\nOutput ONLY the question sentence. No numbering, no explanation, no extra text."""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a senior technical interviewer. You MUST respond ONLY in {req.language}. Do not use any other language."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        question = response.choices[0].message.content
        supabase.table("interview_results").insert({
            "user_id": req.user_id,
            "question": question
        }).execute()
        return {"question": question}
    except Exception as e:
        return {"error": str(e)}


# =========================
# Evaluate Answer
# =========================

@app.post("/evaluate-answer")
def evaluate_answer(req: EvaluationRequest):


Answer: {req.answer}

Evaluate the answer above. You MUST respond ONLY in {req.language}.
Provide:





    try:
        prompt = f"""Question: {req.question}\n\nAnswer: {req.answer}\n\nEvaluate the answer above. You MUST respond ONLY in {req.language}.\nProvide:\n- Score (0-100)\n- Strengths\n- Weaknesses\n- Improvement advice"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"You are a senior technical interviewer. You MUST respond ONLY in {req.language}. Do not use any other language under any circumstances."},
                {"role": "user", "content": prompt}
            ]
        )
        evaluation = response.choices[0].message.content
        supabase.table("interview_results").insert({
            "user_id": req.user_id,
            "question": req.question,
            "answer": req.answer,
            "evaluation": evaluation
        }).execute()
        return {"evaluation": evaluation}
    except Exception as e:
        return {"error": str(e)}


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
            return {"error": "PDF에서 텍스트를 추출할 수 없습니다."}
        # OpenAI 프롬프트 (이력서 리뷰 + 개선점 + 맞춤형 질문 3~5개)
        prompt = f"""
        아래는 한 지원자의 이력서 전문입니다. 이 내용을 바탕으로 아래 두 가지를 출력하세요.\n\n1. 이력서의 문제점, 개선점, 빠진 내용 등 리뷰를 3~5줄로 요약\n2. 지원자의 경력, 기술, 프로젝트, 역할에 맞는 맞춤형 기술 면접 질문 3~5개를 리스트로 생성\n\n아래 형식의 JSON으로만 출력하세요:\n{{\n  \"review\": \"이력서 리뷰 및 개선점\",\n  \"questions\": [\"질문1\", \"질문2\", ...]\n}}\n\n이력서:\n{text}
        """
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert technical interviewer. Analyze the resume below and output a JSON with review and a list of personalized interview questions."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600
        )
        # 응답에서 JSON 파싱
        import json
        content = response.choices[0].message.content
        try:
            result = json.loads(content)
        except Exception:
            result = {"review": "AI 응답 파싱 오류", "questions": [content]}
        return result
    except Exception as e:
        return {"error": str(e)}
