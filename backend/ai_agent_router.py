"""
TaxSphere — AI Agent Router
Simple Q&A endpoint using Claude
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import os, httpx

from auth import CurrentUser, get_current_user

router = APIRouter(prefix="/ai-agent", tags=["AI Agent"])


class QueryRequest(BaseModel):
    query: str
    context: Optional[str] = None


async def call_claude(query: str, context: str = "") -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise HTTPException(500, "ANTHROPIC_API_KEY not configured")

    system = """You are TaxSphere AI — an expert GST and Income Tax assistant for Indian CA firms.

You help with:
- GST reconciliation, notices, returns (GSTR-1, GSTR-3B, GSTR-9)
- Income Tax — ITR filing, Form 26AS, TDS, tax audit
- Notice replies (ASMT-10, DRC-01, REG-03)
- Compliance deadlines and due dates
- ITC rules and disallowances
- Tax saving tips under old and new regime

Always give practical, actionable answers. Cite relevant sections of GST Act or Income Tax Act.
Keep responses concise and professional. Use ₹ for amounts."""

    messages = []
    if context:
        messages.append({"role": "user", "content": f"Context: {context}"})
        messages.append({"role": "assistant", "content": "Understood. How can I help?"})
    messages.append({"role": "user", "content": query})

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-5",
                "max_tokens": 1500,
                "system": system,
                "messages": messages
            }
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"]


@router.post("/query")
async def query_ai(
    req: QueryRequest,
    current_user: CurrentUser = Depends(get_current_user)
):
    try:
        answer = await call_claude(req.query, req.context or "")
        return {
            "query": req.query,
            "response": answer,
            "model": "claude-sonnet-4-5",
            "firm_id": current_user.firm_id
        }
    except httpx.HTTPStatusError as e:
        raise HTTPException(500, f"AI error: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(500, f"AI error: {str(e)}")


@router.get("/status")
async def ai_status(current_user: CurrentUser = Depends(get_current_user)):
    return {
        "status": "ok",
        "module": "taxsphere_ai_agent",
        "model": "claude-sonnet-4-5",
        "capabilities": [
            "GST reconciliation help",
            "Notice reply drafting",
            "ITR filing guidance",
            "Tax saving tips",
            "Compliance deadline reminders",
            "ITC rules explanation"
        ]
    }
