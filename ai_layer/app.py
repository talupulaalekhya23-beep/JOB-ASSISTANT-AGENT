# ai_layer/app.py

import os
import pandas as pd
import requests
from fastapi import FastAPI, UploadFile, File
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel
from bs4 import BeautifulSoup

from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain.agents import create_agent

from ai_layer.rag.build_index import main
from ai_layer.rag.retriever import get_retriever


# ----------------------------
# LOAD ENV
# ----------------------------
ENV_PATH = Path(__file__).resolve().parent / ".env"
print("Loading ENV from:", ENV_PATH)
load_dotenv(dotenv_path=ENV_PATH)

MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "claude-3-haiku-20240307"
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("❌ ANTHROPIC_API_KEY not found in ai_layer/.env")


# ----------------------------
# FASTAPI APP
# ----------------------------
app = FastAPI(title="Job Assistant Agent")


# ----------------------------
# LLM
# ----------------------------
llm_model = ChatAnthropic(
    model=MODEL_NAME,
    api_key=ANTHROPIC_API_KEY,
    temperature=0
)


# ----------------------------
# REQUEST MODEL
# ----------------------------
class ChatRequest(BaseModel):
    message: str


# ----------------------------
# TOOLS
# ----------------------------
@tool
def retrieve_context(query: str) -> str:
    """Retrieve relevant context from uploaded resumes"""
    retriever = get_retriever()
    docs = retriever.invoke(query)
    return "\n".join([d.page_content for d in docs])


@tool
def search_jobs(skills: str) -> str:
    """
    Use this tool whenever a user asks for jobs.
    Returns real job titles and ziprecruiter links.
    """

    import requests
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9"
    }

    response = None  # ✅ prevent UnboundLocalError

    try:
        query = skills.replace(" ", "+") + "+fresher+entry+level"
        url = f"https://www.ziprecruiter.com/"

        response = requests.get(url, headers=headers, timeout=10)

        # ✅ DEBUG safely
        print("STATUS:", response.status_code)
        print("HTML SIZE:", len(response.text))

        soup = BeautifulSoup(response.text, "html.parser")

        jobs = []

        for a in soup.select("a.jcs-JobTitle")[:5]:
            title = a.get_text(strip=True)
            link = "https://www.ziprecruiter.com/" + a.get("href")

            jobs.append(f"{title}\n{link}")

        if not jobs:
            return "NO_RESULTS_FROM_INDEED"

        return "INDEED JOB RESULTS:\n\n" + "\n\n".join(jobs)

    except Exception as e:
        return f"SCRAPER ERROR: {str(e)}"
    
@tool
def save_excel(data: str) -> str:
    """Save job results into Excel"""
    df = pd.DataFrame([{"jobs": data}])
    file = "jobs.xlsx"
    df.to_excel(file, index=False)
    return f"Saved to {file}"


# ----------------------------
# AGENT
# ----------------------------
agent = create_agent(
    model=llm_model,
    tools=[retrieve_context, search_jobs, save_excel],
    system_prompt="""
You are a Job Assistant Agent.

CRITICAL RULES:

1. If the user asks about jobs, hiring, openings, fresher jobs,
   internships, or opportunities → ALWAYS call search_jobs tool.

2. NEVER answer job queries from your own knowledge.

3. ONLY return results coming from tools.

4. Do NOT give career advice unless user explicitly asks.

5. If job search tool returns links, display them clearly.

You MUST use tools instead of guessing.
"""
)


# ----------------------------
# UPLOAD ENDPOINT
# ----------------------------
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

        # rebuild RAG index
        main()

        result = agent.invoke({
            "messages": [
                {
                    "role": "user",
                    "content": "Analyze uploaded resume and suggest suitable jobs"
                }
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


# ----------------------------
# CHAT ENDPOINT (FIXED ✅)
# ----------------------------
@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        user_message = req.message

        result = agent.invoke({
            "messages": [
                {"role": "user", "content": user_message}
            ]
        })
        print(result)
        reply = result["messages"][-1].content

        return {"response": reply}

    except Exception as e:
        print("CHAT ERROR:", str(e))
        return {"response": "Agent failed to respond"}


# ----------------------------
# HEALTH CHECK
# ----------------------------
@app.get("/")
def health():
    return {"status": "Job Assistant Agent Running"}