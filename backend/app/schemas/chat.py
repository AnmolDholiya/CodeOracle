from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class SourceReference(BaseModel):
    file: str
    symbol: Optional[str] = None
    lines: Optional[str] = None
    details: Optional[str] = None

class ChatRequest(BaseModel):
    project_id: Optional[str] = None
    message: str
    conversation_id: Optional[str] = None
    selected_file: Optional[str] = None
    selected_function: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    sources: List[SourceReference] = []
    verified_facts: List[str] = []
    recommendations: List[str] = []
    model_used: Optional[str] = None
