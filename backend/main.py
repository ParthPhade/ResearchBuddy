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
            persona_prompt = "You are an AI Research Intelligence Assistant. Provide a detailed, pedagogical 'Notebook' analysis of the research, focusing on providing a comprehensive understanding of the author's intent and findings."
        else:
            persona_prompt = "You are an Advanced Research Strategist. Deconstruct this paper into a highly professional, pedagogical guide. Use clear, formal English and sophisticated analogies to ensure deep conceptual mastery."

        prompt = f"""{persona_prompt}

        ---
        STRICT OPERATIONAL RULES:
        1. NO INFORMAL OR CHILDISH LANGUAGE. Maintain a high professional standard.
        2. NO LONG PARAGRAPHS. Utilize structured, nested bullet points for clarity and depth.
        3. FLOWCHART IS MANDATORY. Map the SPECIFIC methodology of this paper using a 'mermaid graph TD' block.
        4. USE PROFESSIONAL TABLES for comparative data or definitions.

        ---
        REQUIRED REPORT STRUCTURE:

        # 📄 RESEARCH INTELLIGENCE GUIDE: [Title]

        > ### 🏛️ EXECUTIVE BRIEFING
        > [Provide a sophisticated, high-level summary of the core thesis and its strategic importance to the field.]

        ## 📊 I. PROCEDURAL ARCHITECTURE (Methodology Roadmap)
        ```mermaid
        graph TD
          [CRITICAL: Map the SPECIFIC methodological steps of this paper. Use 6-10 detailed nodes with professional labels and relevant icons/emojis.]
        ```

        ## 🔍 II. CRITICAL RESEARCH GAP
        *   **Context:** What were the limitations of the existing state-of-the-art?
        *   **The Resolution:** How does this research systematically address that specific gap?

        ## 🌍 III. STRATEGIC REAL-WORLD IMPLICATIONS
        * [Explain the long-term impact on industry, technology, or society.]
        * [Provide a concrete example of the practical application of these findings.]

        ## 💡 IV. CONCEPTUAL FRAMEWORK & TERMINOLOGY
        | Technical Term | Comprehensive Definition | Contextual Significance |
        | :--- | :--- | :--- |
        [Identify 6-10 core concepts. Provide deep, professional explanations.]

        ## ⚙️ V. CORE METHODOLOGICAL FRAMEWORK
        * **1. Design & Configuration:** [Detail the research setup]
        * **2. Execution & Data Synthesis:** [Detail the process]
        * **3. Validation & Statistical Rigor:** [How accuracy was established]

        ## 📈 VI. KEY FINDINGS & ANALYTICAL INSIGHTS
        * 🔷 [Major Insight 1: Deep explanation]
        * 🔷 [Major Insight 2: Deep explanation]

        ---
        PAPER TEXT FOR ANALYSIS:
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
