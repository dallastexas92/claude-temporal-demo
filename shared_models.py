from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class ClaudePromptInput:
    prompt: str
    model: str = "claude-3-7-sonnet-20250219"
    max_tokens: int = 1024
    conversation_history: Optional[List[Dict]] = None


@dataclass
class ClaudeResponse:
    text: str
    request_id: str = ""


@dataclass
class ChatMessage:
    role: str  # "user" or "assistant"
    content: str
    timestamp: float