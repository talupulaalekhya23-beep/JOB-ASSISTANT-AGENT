# ai_layer/app.py

import os
import pandas as pd
import requests
from fastapi import FastAPI, UploadFile, File
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Dict
from bs4 import BeautifulSoup
from fastapi.responses import FileResponse

from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain.agents import create_agent

from ai_layer.rag.build_index import main
from ai_layer.rag.retriever import get_retriever

# =====================================================
# LOAD ENV
# =====================================================
ENV_PATH = Path(__file__).resolve().parent / ".env"
print("Loading ENV from:", ENV_PATH)
load_dotenv(dotenv_path=ENV_PATH)

MODEL_NAME = os.getenv("MODEL_NAME", "claude-3-haiku-20240307")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("❌ ANTHROPIC_API_KEY not found")

# =====================================================
# FASTAPI APP
# =====================================================
app = FastAPI(title="Job Assistant Agent")

# =====================================================
# LLM
# =====================================================
llm_model = ChatAnthropic(
    model=MODEL_NAME,
    api_key=ANTHROPIC_API_KEY,
    temperature=0
)

# =====================================================
# REQUEST MODEL
# =====================================================
class ChatRequest(BaseModel):
    message: str

# =====================================================
# TOOL INPUT MODELS
# =====================================================
class JobList(BaseModel):
    jobs: List[Dict]

# =====================================================
# TOOLS
# =====================================================

@tool
def retrieve_context(query: str) -> str:
    """Retrieve context from uploaded resumes using the RAG retriever."""
    retriever = get_retriever()
    docs = retriever.invoke(query)
    return "\n".join([d.page_content for d in docs])

@tool
def search_jobs(query: str) -> List[Dict]:
    """Search jobs using JSearch API (RapidAPI) for Franklin, TN."""
    url = "https://jsearch.p.rapidapi.com/search"
    params = {"query": query, "location": "Franklin, TN", "page": "1"}
    headers = {
        "X-RapidAPI-Key": os.getenv("JSEARCH_API_KEY"),
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code != 200:
            return "JOB_SOURCE_ERROR"

        data = response.json()
        jobs_list = []

        for job in data.get("data", [])[:5]:
            jobs_list.append({
                "Job Title": job.get("job_title"),
                "Company": job.get("employer_name"),
                "Location": job.get("job_city"),
                "Apply Link": job.get("job_apply_link")
            })

        if not jobs_list:
            return "NO_JOBS_FOUND"

        return jobs_list

    except Exception as e:
        print("API ERROR:", str(e))
        return "JOB_SOURCE_ERROR"

@tool
def save_excel(jobs: dict) -> str:
    """
    Save job search results into an Excel file.
    Input format: {"jobs": [list of job dicts]}
    """
    if not jobs or "jobs" not in jobs or not jobs["jobs"]:
        return "No jobs to save."

    file_path = Path(__file__).resolve().parent / "jobs.xlsx"
    df = pd.DataFrame(jobs["jobs"])
    df.to_excel(file_path, index=False)
    return f"Saved to {file_path}"

# =====================================================
# JOB QUERY DETECTOR
# =====================================================
def is_job_query(text: str) -> bool:
    keywords = [
        "job", "jobs", "hiring", "opening",
        "vacancy", "role", "position",
        "sales associate", "retail",
        "internship", "career"
    ]
    text = text.lower()
    return any(k in text for k in keywords)

# =====================================================
# AGENT
# =====================================================
agent = create_agent(
    model=llm_model,
    tools=[retrieve_context, search_jobs, save_excel],
    system_prompt="""
You are a Job Assistant Agent.

RULES:

1. ALWAYS use search_jobs for job queries.
2. NEVER invent job listings.
3. Interpret tool outputs:

- JOB RESULTS → show clearly.
- NO_JOBS_FOUND → say no listings found.
- JOB_SOURCE_ERROR → say provider temporarily unavailable.

Never guess jobs yourself.
"""
)

# =====================================================
# UPLOAD ENDPOINT
# =====================================================
@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    try:
        upload_dir = Path(__file__).resolve().parent / "rag" / "docs"
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / file.filename
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        print("Saved:", file_path)

        # rebuild vector DB
        main()

        result = agent.invoke({
            "messages": [
                {"role": "user",
                 "content": "Analyze uploaded resume and suggest suitable jobs"}
            ]
        })
        reply = result["messages"][-1].content

        return {
            "message": "File uploaded successfully",
            "file": file.filename,
            "response": reply
        }

    except Exception as e:
        print("UPLOAD ERROR:", str(e))
        return {"error": str(e)}

# =====================================================
# CHAT ENDPOINT
# =====================================================


@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        user_message = req.message

        if is_job_query(user_message):
            jobs = search_jobs.invoke(user_message)

            if jobs == "JOB_SOURCE_ERROR":
                return {"response": "⚠️ Job provider temporarily unavailable."}
            if jobs == "NO_JOBS_FOUND":
                return {"response": "No job listings found."}

            # Wrap the job list in a dictionary
            save_excel.invoke({"jobs": jobs})
            file_path = Path(__file__).resolve().parent / "jobs.xlsx"

            return FileResponse(
                path=file_path,
                filename="job_results.xlsx",
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

        # Non-job queries use agent
        result = agent.invoke({"messages":[{"role":"user","content":user_message}]})
        reply = result["messages"][-1].content
        return {"response": reply}

    except Exception as e:
        print("CHAT ERROR:", str(e))
        return {"response": "Agent failed to respond"}
# =====================================================
# HEALTH CHECK
# =====================================================
@app.get("/")
def health():
    return {"status": "Job Assistant Agent Running"}