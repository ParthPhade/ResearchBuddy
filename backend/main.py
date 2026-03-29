import os
import io
import base64
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import fitz  # PyMuPDF
from PIL import Image
from dotenv import load_dotenv
from google.oauth2 import id_token
from google.auth.transport import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

load_dotenv()

app = FastAPI()

# Setup static directory for images
STATIC_DIR = "static"
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

async def get_current_user_api_key(x_api_key: Optional[str], authorization: Optional[str], provider: str):
    if x_api_key:
        return x_api_key
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        try:
            id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
            return os.getenv(f"{provider.upper()}_API_KEY")
        except Exception as e:
            err_msg = str(e)
            if "Max retries exceeded" in err_msg or "Failed to resolve" in err_msg:
                raise HTTPException(status_code=503, detail="Google Auth server unreachable. Please use your own API Key in Settings to bypass Google login.")
            raise HTTPException(status_code=401, detail=f"Auth Failed: {err_msg}")
    key = os.getenv(f"{provider.upper()}_API_KEY")
    if key: return key
    raise HTTPException(status_code=401, detail="Auth Required")

@app.post("/analyze")
async def analyze_paper(
    file: UploadFile = File(...),
    provider: str = "gemini",
    style: str = "simple", # New style parameter
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF only")
    
    api_key = await get_current_user_api_key(x_api_key, authorization, provider)
    
    try:
        pdf_content = await file.read()
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        
        # 1. Extract Text
        text = ""
        for page in doc:
            extracted = page.get_text()
            if extracted:
                text += extracted
        
        if not text.strip() or len(text.strip()) < 50:
            raise HTTPException(
                status_code=400, 
                detail="This PDF seems to have no readable text (it might be a scan). Please try a paper with selectable text."
            )
        
        # 2. Extract Key Images
        image_urls = []
        img_count = 0
        for i in range(len(doc)):
            if img_count >= 3: break
            for img in doc.get_page_images(i):
                if img_count >= 3: break
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                img_filename = f"paper_img_{xref}.png"
                img_path = os.path.join(STATIC_DIR, img_filename)
                with open(img_path, "wb") as f: f.write(image_bytes)
                image_urls.append(f"http://localhost:8000/static/{img_filename}")
                img_count += 1

        # 3. AI Analysis
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key) if provider == "gemini" else ChatOpenAI(model="gpt-4o-mini", openai_api_key=api_key)

        if style == "notebook":
            persona_prompt = "You are an AI Notebook Assistant. Create an interactive-style 'Notebook' summary. Use a 'Author's Diary' tone, explaining the 'behind-the-scenes' of the research."
        else:
            persona_prompt = "You are Your Genius Best Friend. Explain this paper so simply that a 10-year-old would get excited about it. Use zero 'professor words' and constantly use analogies (like pizza, video games, or TikTok)."

        prompt = f"""{persona_prompt}

        ---
        STRICT RULES:
        1. NO LONG PARAGRAPHS. Use short, punchy bullet points.
        2. NO ACADEMIC JARGON. If you use a hard word, explain it like a friend would.
        3. FLOWCHART IS MANDATORY. Use simple labels like 'Step 1: The Idea' -> 'Step 2: The Test'.
        4. USE EMOJIS to make it look friendly.

        ---
        STRUCTURE:

        # 📚 THE ULTIMATE CHEAT SHEET: [Title]

        > ### 🎯 THE 10-WORD TAKEAWAY
        > [Summarize the whole paper in exactly 10 words or less]

        > ### 🌟 THE BIG PICTURE
        > [Explain the core discovery using a fun analogy. Why should I care?]

        ## 📊 I. THE ROADMAP (How they did it)
        ```mermaid
        graph TD
          A[The Problem 🛑] --> B[The Plan 📝]
          B --> C[The Test 🧪]
          C --> D[The Big Win 🏆]
        ```
        [Note: Change labels to match the paper but KEEP THEM SIMPLE.]

        ## 🌍 II. WHY THIS MATTERS (Real World Impact)
        * [How this changes your phone/health/future]
        * [One concrete example of this in the real world]

        ## 💡 III. JARGON DECODER (STRICT TABLE)
        | Hard Word | Simple English | "Like a..." (Analogy) |
        | :--- | :--- | :--- |
        [STRICTLY 5-10 terms here. NO PARAGRAPHS.]

        ## 🧮 IV. THE MAGIC BEHIND THE CURTAIN (Math Decoder)
        [Find the hard math/logic. Explain the 'Vibe' of the math without using scary symbols.]

        ## ⚙️ V. THE 1-2-3 METHOD
        * **1. The Setup:** [What they gathered]
        * **2. The Action:** [What they did - simple!]
        * **3. The Proof:** [How they knew it worked]

        ## 📈 VI. THE 'AHA!' MOMENTS
        * 💡 [Coolest finding 1]
        * 💡 [Coolest finding 2]

        ---
        PAPER TEXT:
        {text[:18000]}
        """

        response = await llm.ainvoke([HumanMessage(content=prompt)])
        return {
            "analysis": response.content, 
            "images": image_urls,
            "full_text": text[:20000] # Return context for frontend chat
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat_with_paper(
    question: str,
    context: str,
    provider: str = "gemini",
    x_api_key: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
):
    api_key = await get_current_user_api_key(x_api_key, authorization, provider)
    
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=api_key) if provider == "gemini" else ChatOpenAI(model="gpt-4o-mini", openai_api_key=api_key)
        
        prompt = f"""You are a helpful research assistant. Answer the user's question based ONLY on the provided research paper text. If the answer isn't in the text, say you don't know.
        
        PAPER CONTEXT:
        {context}
        
        USER QUESTION:
        {question}
        
        ANSWER (Keep it helpful and clear):"""
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        return {"answer": response.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
