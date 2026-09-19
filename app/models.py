from pydantic import BaseModel
from typing import List

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatHistory(BaseModel):
    messages: List[ChatMessage] = []