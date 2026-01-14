#!/usr/bin/env python3
"""
Backend server for Session Calendar Viewer
Handles GraphQL queries and LLM analysis using Claude 4.5 Sonnet
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

try:
    import anthropic
except ImportError:
    print("Installing required packages...")
    os.system("pip install fastapi uvicorn anthropic")
    import anthropic


from config import ANTHROPIC_API_KEY

# Configuration
# ANTHROPIC_API_KEY is imported from config.py

GRAPHQL_ENDPOINT = "https://api-llm-internal.prd.alva.xyz/query"

# Claude 4.5 Sonnet Model
CLAUDE_MODEL = "claude-4-5-sonnet-20250514"  # Latest Sonnet 4.5 model

app = FastAPI(title="Session Calendar API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request models
class GraphQLRequest(BaseModel):
    query: str
    variables: Optional[dict] = None


class SessionData(BaseModel):
    id: str
    dialogs: Optional[dict] = None
    error: Optional[str] = None


class AnalysisRequest(BaseModel):
    session: SessionData


# Initialize Anthropic client
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def format_session_for_analysis(session: SessionData) -> str:
    """Format session data for LLM analysis."""
    dialogs_text = ""

    if session.dialogs and session.dialogs.get("list"):
        for i, dialog in enumerate(session.dialogs["list"], 1):
            question = dialog.get("question", "N/A")
            answer = dialog.get("answer", "N/A")

            # Truncate long answers
            if len(answer) > 2000:
                answer = answer[:2000] + "..."

            dialogs_text += f"""
Dialog {i}:
Question: {question}
Answer: {answer}

---"""

    return f"""Session ID: {session.id}

Dialogs in this session:
{dialogs_text}

Please analyze this session and provide a structured evaluation."""


ANALYSIS_PROMPT = """You are an expert conversation analyst. Analyze the following session and provide a comprehensive evaluation in JSON format.

Focus on:
1. **User Query Evaluation** (part_b_user_query)
   - primary_topic: What is the main subject?
   - sentiment: positive, negative, neutral, or mixed
   - complexity: low, medium, or high
   - intent: What is the user trying to achieve?

2. **Model Response Evaluation** (part_c_model_response)
   - overall_score: 1-5 rating
   - relevance_score: 1-5 rating
   - accuracy_score: 1-5 rating
   - completeness_score: 1-5 rating
   - clarity_score: 1-5 rating
   - helpful_score: 1-5 rating
   - strengths: List of 2-3 key strengths
   - weaknesses: List of any areas for improvement
   - response_quality: brief assessment

3. **Summary** (summary)
   - overall_interaction_quality: One sentence summary
   - user_satisfaction: Estimated satisfaction level
   - action_items: Any follow-up actions suggested

Return ONLY valid JSON without markdown formatting:

```json
{{
  "part_b_user_query": {{
    "user_query_evaluation": {{
      "primary_topic": "...",
      "sentiment": "...",
      "complexity": "...",
      "intent": "..."
    }}
  }},
  "part_c_model_response": {{
    "model_response_evaluation": {{
      "overall_score": 4,
      "relevance_score": 4,
      "accuracy_score": 4,
      "completeness_score": 4,
      "clarity_score": 5,
      "helpful_score": 4,
      "strengths": ["...", "..."],
      "weaknesses": ["..."],
      "response_quality": "..."
    }}
  }},
  "summary": {{
    "overall_interaction_quality": "...",
    "user_satisfaction": "...",
    "action_items": ["..."]
  }}
}}
```"""


async def call_claude_for_analysis(session_text: str) -> dict:
    """Call Claude API to analyze session."""
    try:
        full_prompt = f"{ANALYSIS_PROMPT}\n\n{session_text}"

        response = anthropic_client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            temperature=0,
            messages=[{"role": "user", "content": full_prompt}]
        )

        # Extract response text
        content = response.content[0].text

        # Parse JSON from response (handle markdown code blocks)
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        return json.loads(content)

    except anthropic.APIError as e:
        raise HTTPException(status_code=500, detail=f"Anthropic API error: {str(e)}")
    except json.JSONDecodeError as e:
        # Try to fix common JSON issues
        try:
            # Remove any trailing commas
            content = content.replace(",\n", "\n").replace(",}", "}").replace(",]", "]")
            return json.loads(content)
        except:
            raise HTTPException(status_code=500, detail=f"Failed to parse LLM response: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "Session Calendar API"}


@app.post("/query")
async def graphql_proxy(request: GraphQLRequest):
    """Proxy GraphQL requests to the Alva API."""
    try:
        # Get Authorization header from the request
        auth_header = request.headers.get("Authorization", "")

        headers = {
            "Content-Type": "application/json",
        }

        if auth_header:
            headers["Authorization"] = auth_header

        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GRAPHQL_ENDPOINT,
                json={"query": request.query, "variables": request.variables or {}},
                headers=headers,
                timeout=30.0
            )

            return response.json()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GraphQL proxy error: {str(e)}")


@app.post("/analyze")
async def analyze_session(request: AnalysisRequest):
    """Analyze a session using Claude 4.5 Sonnet."""
    try:
        session_text = format_session_for_analysis(request.session)

        # Call Claude API (this is async but anthropic is sync, so we run in thread pool)
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                executor,
                lambda: call_claude_for_analysis(session_text)
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/analyze/stream")
async def analyze_session_stream(request: AnalysisRequest):
    """Stream analysis results from Claude."""
    try:
        session_text = format_session_for_analysis(request.session)
        full_prompt = f"{ANALYSIS_PROMPT}\n\n{session_text}"

        async def generate():
            try:
                with anthropic_client.messages.stream(
                    model=CLAUDE_MODEL,
                    max_tokens=4096,
                    temperature=0,
                    messages=[{"role": "user", "content": full_prompt}]
                ) as stream:
                    for text in stream.text_stream:
                        yield text

            except Exception as e:
                yield f"\n\n[Error: {str(e)}]"

        return StreamingResponse(generate(), media_type="text/plain")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream analysis failed: {str(e)}")


if __name__ == "__main__":
    print("=" * 60)
    print("Session Calendar Backend Server")
    print("=" * 60)
    print(f"Claude Model: {CLAUDE_MODEL}")
    print(f"GraphQL Endpoint: {GRAPHQL_ENDPOINT}")
    print("\nStarting server on http://localhost:8000")
    print("=" * 60)

    # Check if running in correct environment
    import sys
    print(f"Python: {sys.executable}")

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
