import os
from fastapi import APIRouter, HTTPException, status
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import generate_chat_response

router = APIRouter(prefix="/api", tags=["CodeOracle AI Chat"])

@router.post("/chat", response_model=ChatResponse)
async def chat_with_codeoracle(request: ChatRequest):
    """
    On-Demand CodeOracle AI Chatbot powered by Google Gemini.
    Strictly answers queries using targeted context retrieved from analyzed workspace data.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message cannot be empty."
        )

    try:
        return await generate_chat_response(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat message: {str(exc)}"
        )
